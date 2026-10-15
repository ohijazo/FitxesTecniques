"""Enviament de correus amb adjunts via Microsoft Graph.

Autenticacio: client credentials (app-only), la mateixa app registration
d'Azure que la distribucio a SharePoint (reutilitza el seu _get_token).

Permis requerit a Azure AD (Application permission, amb admin consent):
  - Mail.Send
Recomanat restringir-lo amb una Application Access Policy al grup d'usuaris
de l'aplicacio, perque no pugui enviar des de qualsevol bustia del tenant.

Flux: es crea el missatge com a esborrany a la bustia del remitent, s'hi
afegeixen els adjunts (simple fins a 3 MB, upload session per sobre) i
s'envia. Aixi no hi ha limit de mida de peticio i el correu queda als
Elements enviats de l'usuari.
"""

import os
import base64
import logging
import requests

from app.services.sharepoint_distributor import _get_token, GRAPH_BASE

LOG = logging.getLogger(__name__)

ADJUNT_SIMPLE_MAX = 3 * 1024 * 1024    # 3 MB (limit d'adjunt simple a Graph)
CHUNK_SIZE = 4 * 1024 * 1024           # multiple de 320 KiB, com demana Graph
TIMEOUT = 60


def _error_graph(resp, accio):
    """Missatge llegible a partir d'una resposta d'error de Graph."""
    try:
        err = resp.json().get('error', {})
        codi = err.get('code', '')
        msg = err.get('message', '')
    except ValueError:
        codi, msg = '', resp.text[:300]
    if resp.status_code == 403 or codi in ('ErrorAccessDenied', 'AccessDenied'):
        return (f"{accio}: accés denegat per Microsoft 365. Cal que l'app registration "
                f"tingui el permís Mail.Send (amb admin consent) i que pugui enviar "
                f"des d'aquesta bústia. Detall: {msg}")
    if resp.status_code == 404 or codi in ('ErrorInvalidUser', 'MailboxNotEnabledForRESTAPI', 'ResourceNotFound'):
        return f"{accio}: no s'ha trobat la bústia del remitent a Microsoft 365. Detall: {msg}"
    return f"{accio}: error {resp.status_code} {codi} {msg}".strip()


def _destinataris(adreces):
    return [{'emailAddress': {'address': a}} for a in adreces]


def _afegir_adjunt(session, url_missatge, path, nom):
    mida = os.path.getsize(path)
    if mida <= ADJUNT_SIMPLE_MAX:
        with open(path, 'rb') as f:
            contingut = base64.b64encode(f.read()).decode('ascii')
        resp = session.post(f'{url_missatge}/attachments', json={
            '@odata.type': '#microsoft.graph.fileAttachment',
            'name': nom,
            'contentType': 'application/pdf',
            'contentBytes': contingut,
        }, timeout=TIMEOUT)
        if resp.status_code not in (200, 201):
            return _error_graph(resp, f"Adjuntant {nom}")
        return None

    # Adjunt gran: upload session
    resp = session.post(f'{url_missatge}/attachments/createUploadSession', json={
        'AttachmentItem': {'attachmentType': 'file', 'name': nom, 'size': mida},
    }, timeout=TIMEOUT)
    if resp.status_code not in (200, 201):
        return _error_graph(resp, f"Adjuntant {nom}")
    upload_url = resp.json().get('uploadUrl')
    with open(path, 'rb') as f:
        inici = 0
        while inici < mida:
            tros = f.read(CHUNK_SIZE)
            fi = inici + len(tros) - 1
            # L'uploadUrl ja porta l'autenticacio: no s'hi envia el token.
            r = requests.put(upload_url, data=tros, headers={
                'Content-Length': str(len(tros)),
                'Content-Range': f'bytes {inici}-{fi}/{mida}',
            }, timeout=TIMEOUT)
            if r.status_code not in (200, 201, 202):
                return _error_graph(r, f"Pujant {nom}")
            inici = fi + 1
    return None


def enviar_correu(config, remitent, per_a, cc, assumpte, cos, adjunts):
    """Envia un correu des de la bustia `remitent`.

    config: dict amb tenant_id, client_id, client_secret.
    adjunts: llista de (path_local, nom_fitxer).
    Retorna (ok, missatge_error). No llança excepcions.
    """
    try:
        if not (config.get('tenant_id') and config.get('client_id') and config.get('client_secret')):
            return False, ("L'enviament per correu no està configurat al servidor "
                           "(falten GRAPH_TENANT_ID / GRAPH_CLIENT_ID / GRAPH_CLIENT_SECRET).")

        token, err = _get_token(config['tenant_id'], config['client_id'], config['client_secret'])
        if err:
            return False, err

        session = requests.Session()
        session.headers.update({'Authorization': f'Bearer {token}'})

        url_bustia = f"{GRAPH_BASE}/users/{requests.utils.quote(remitent)}"
        missatge = {
            'subject': assumpte,
            'body': {'contentType': 'Text', 'content': cos},
            'toRecipients': _destinataris(per_a),
        }
        if cc:
            missatge['ccRecipients'] = _destinataris(cc)

        resp = session.post(f'{url_bustia}/messages', json=missatge, timeout=TIMEOUT)
        if resp.status_code not in (200, 201):
            return False, _error_graph(resp, "Creant el correu")
        msg_id = resp.json()['id']
        url_missatge = f'{url_bustia}/messages/{msg_id}'

        for path, nom in adjunts:
            err = _afegir_adjunt(session, url_missatge, path, nom)
            if err:
                # No deixar l'esborrany a mitges a la bustia de l'usuari
                session.delete(url_missatge, timeout=TIMEOUT)
                return False, err

        resp = session.post(f'{url_missatge}/send', timeout=TIMEOUT)
        if resp.status_code not in (200, 202):
            return False, _error_graph(resp, "Enviant el correu")
        return True, None

    except requests.RequestException as e:
        LOG.exception('[EMAIL] error de xarxa')
        return False, f"Error de connexió amb Microsoft 365: {e}"
    except Exception as e:
        LOG.exception('[EMAIL] error inesperat')
        return False, f"Error inesperat enviant el correu: {e}"
