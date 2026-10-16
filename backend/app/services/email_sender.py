"""Enviament de correus amb adjunts via Microsoft Graph.

Autenticacio: client credentials (app-only), la mateixa app registration
d'Azure que la distribucio a SharePoint (reutilitza el seu _get_token).

Permis requerit a Azure AD (Application permission, amb admin consent):
  - Mail.Send   (NO cal Mail.ReadWrite)
Recomanat restringir-lo amb una Application Access Policy al grup d'usuaris
de l'aplicacio, perque no pugui enviar des de qualsevol bustia del tenant.

Flux: POST /users/{remitent}/sendMail amb el missatge i els adjunts en base64
en una sola peticio (saveToSentItems: el correu queda als Elements enviats).
Crear esborranys (/messages) requeriria Mail.ReadWrite, per aixo no es fa.

Graph limita cada peticio a 4 MB; el base64 hi afegeix un 33%. Si els adjunts
no hi caben, l'enviament es parteix en diversos correus "(1/n)".
"""

import os
import base64
import logging
import requests

from app.services.sharepoint_distributor import _get_token, GRAPH_BASE

LOG = logging.getLogger(__name__)

# Mida maxima dels fitxers originals per correu: 2,8 MB * 4/3 (base64) ~ 3,7 MB,
# amb marge per al cos i les capçaleres dins del limit de 4 MB de Graph.
MAX_BYTES_PER_CORREU = int(2.8 * 1024 * 1024)
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


def _agrupar_adjunts(adjunts):
    """Reparteix (path, nom) en lots que caben en un correu. Conserva l'ordre."""
    lots, actual, mida_actual = [], [], 0
    for path, nom in adjunts:
        mida = os.path.getsize(path)
        if actual and mida_actual + mida > MAX_BYTES_PER_CORREU:
            lots.append(actual)
            actual, mida_actual = [], 0
        actual.append((path, nom))
        mida_actual += mida
    if actual:
        lots.append(actual)
    return lots or [[]]


def _adjunt_graph(path, nom):
    with open(path, 'rb') as f:
        contingut = base64.b64encode(f.read()).decode('ascii')
    return {
        '@odata.type': '#microsoft.graph.fileAttachment',
        'name': nom,
        'contentType': 'application/pdf',
        'contentBytes': contingut,
    }


def enviar_correu(config, remitent, per_a, cc, assumpte, cos, adjunts):
    """Envia un correu (o diversos, si els adjunts no hi caben) des de `remitent`.

    config: dict amb tenant_id, client_id, client_secret.
    adjunts: llista de (path_local, nom_fitxer).
    Retorna (ok, missatge): si ok, missatge es None o informa que s'ha partit.
    No llança excepcions.
    """
    try:
        if not (config.get('tenant_id') and config.get('client_id') and config.get('client_secret')):
            return False, ("L'enviament per correu no està configurat al servidor "
                           "(falten GRAPH_TENANT_ID / GRAPH_CLIENT_ID / GRAPH_CLIENT_SECRET).")

        massa_grans = [nom for path, nom in adjunts if os.path.getsize(path) > MAX_BYTES_PER_CORREU]
        if massa_grans:
            return False, (f"No es pot enviar: {', '.join(massa_grans)} supera la mida màxima "
                           f"per correu ({MAX_BYTES_PER_CORREU / (1024 * 1024):.1f} MB).")

        token, err = _get_token(config['tenant_id'], config['client_id'], config['client_secret'])
        if err:
            return False, err

        url = f"{GRAPH_BASE}/users/{requests.utils.quote(remitent)}/sendMail"
        headers = {'Authorization': f'Bearer {token}'}
        lots = _agrupar_adjunts(adjunts)
        total = len(lots)

        for i, lot in enumerate(lots, start=1):
            missatge = {
                'subject': assumpte if total == 1 else f'{assumpte} ({i}/{total})',
                'body': {'contentType': 'Text', 'content': cos},
                'toRecipients': _destinataris(per_a),
                'attachments': [_adjunt_graph(path, nom) for path, nom in lot],
            }
            if cc:
                missatge['ccRecipients'] = _destinataris(cc)

            resp = requests.post(url, headers=headers, timeout=TIMEOUT,
                                 json={'message': missatge, 'saveToSentItems': True})
            if resp.status_code != 202:
                accio = "Enviant el correu" if total == 1 else f"Enviant el correu {i} de {total}"
                err = _error_graph(resp, accio)
                if i > 1:
                    err = f"S'han enviat {i - 1} de {total} correus. {err}"
                return False, err

        if total > 1:
            return True, f"Enviat en {total} correus per la mida dels adjunts."
        return True, None

    except requests.RequestException as e:
        LOG.exception('[EMAIL] error de xarxa')
        return False, f"Error de connexió amb Microsoft 365: {e}"
    except Exception as e:
        LOG.exception('[EMAIL] error inesperat')
        return False, f"Error inesperat enviant el correu: {e}"
