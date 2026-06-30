"""Servei per distribuir PDFs a SharePoint Online via Microsoft Graph API.

Autenticacio: client credentials flow (App-only) — l'app s'autentica amb
tenant_id + client_id + client_secret registrats a Azure AD.

Permisos minims requerits a Azure AD (Application permissions):
  - Files.ReadWrite.All  (o Sites.Selected si es vol restringir a sites concrets)
"""

import os
import time
import logging
from urllib.parse import quote
import requests

try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False

LOG = logging.getLogger(__name__)


def _quote_path(p):
    """URL-encode un path conservant els separadors '/'.

    Graph API requereix paths percent-encoded quan contenen espais, accents,
    parèntesi, comes, etc. (ex.: 'Documentació Comercial(FT, fotos,...)').
    """
    return quote(p or '', safe='/')


GRAPH_BASE = 'https://graph.microsoft.com/v1.0'
SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024   # 4 MiB (limit upload simple Graph)
CHUNK_SIZE = 5 * 1024 * 1024            # 5 MiB per chunk en upload session

# Cache en memoria de tokens i identificadors resolts (evita peticions repetides)
_token_cache = {}     # key: f"{tenant_id}|{client_id}" -> {'token': str, 'expires': float}
_resource_cache = {}  # key: f"{site_url}|{drive_name}" -> {'site_id': str, 'drive_id': str}


def _get_token(tenant_id, client_id, client_secret):
    """Obte un access token via client credentials flow (cachejat)."""
    if not MSAL_AVAILABLE:
        return None, "Llibreria 'msal' no instal·lada. Cal afegir-la a requirements.txt"

    cache_key = f"{tenant_id}|{client_id}"
    cached = _token_cache.get(cache_key)
    if cached and cached['expires'] > time.time() + 60:
        return cached['token'], None

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    try:
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority,
        )
        result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
    except Exception as e:
        return None, f"Error iniciant MSAL: {e}"

    if 'access_token' not in result:
        err = result.get('error_description') or result.get('error') or 'Token no obtingut'
        return None, f"Error obtenint token: {err}"

    expires_in = int(result.get('expires_in', 3600))
    _token_cache[cache_key] = {
        'token': result['access_token'],
        'expires': time.time() + expires_in,
    }
    return result['access_token'], None


def _parse_site_url(site_url):
    """Separa una URL tipus https://contoso.sharepoint.com/sites/X en hostname + path."""
    url = site_url.strip()
    if url.startswith('https://'):
        url = url[8:]
    elif url.startswith('http://'):
        url = url[7:]
    url = url.rstrip('/')
    parts = url.split('/', 1)
    hostname = parts[0]
    site_path = '/' + parts[1] if len(parts) > 1 else ''
    return hostname, site_path


def _resolve_site_drive(token, config):
    """Resol site_id i drive_id a partir de la configuracio (cachejat)."""
    site_url = (config.get('site_url') or '').strip()
    drive_name = (config.get('drive_name') or '').strip()
    cache_key = f"{site_url}|{drive_name}"

    cached = _resource_cache.get(cache_key)
    if cached:
        return cached, None

    if not site_url:
        return None, "Configuracio SharePoint incompleta (site_url buit)"

    headers = {'Authorization': f'Bearer {token}'}

    # 1) Resoldre site_id (si no s'ha passat directament)
    site_id = (config.get('site_id') or '').strip()
    if not site_id:
        hostname, site_path = _parse_site_url(site_url)
        url = f"{GRAPH_BASE}/sites/{hostname}:{_quote_path(site_path)}"
        try:
            r = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as e:
            return None, f"Error connectant a Graph (site): {e}"
        if r.status_code != 200:
            return None, f"No s'ha pogut resoldre el site ({r.status_code}): {r.text[:200]}"
        site_id = r.json().get('id')
        if not site_id:
            return None, "Resposta de site sense 'id'"

    # 2) Resoldre drive_id
    drive_id = (config.get('drive_id') or '').strip()
    if not drive_id:
        if drive_name:
            url = f"{GRAPH_BASE}/sites/{site_id}/drives"
            try:
                r = requests.get(url, headers=headers, timeout=30)
            except requests.RequestException as e:
                return None, f"Error llistant drives: {e}"
            if r.status_code != 200:
                return None, f"No s'han pogut llistar drives ({r.status_code}): {r.text[:200]}"
            drives = r.json().get('value', [])
            target = next((d for d in drives if d.get('name', '').lower() == drive_name.lower()), None)
            if not target:
                noms = ', '.join(d.get('name', '') for d in drives) or '(cap)'
                return None, f"No s'ha trobat la llibreria '{drive_name}'. Disponibles: {noms}"
            drive_id = target['id']
        else:
            url = f"{GRAPH_BASE}/sites/{site_id}/drive"
            try:
                r = requests.get(url, headers=headers, timeout=30)
            except requests.RequestException as e:
                return None, f"Error obtenint drive per defecte: {e}"
            if r.status_code != 200:
                return None, f"No s'ha pogut obtenir drive per defecte ({r.status_code}): {r.text[:200]}"
            drive_id = r.json().get('id')
            if not drive_id:
                return None, "Resposta de drive sense 'id'"

    result = {'site_id': site_id, 'drive_id': drive_id}
    _resource_cache[cache_key] = result
    return result, None


def _build_item_path(folder_path, filename):
    """Construeix la ruta de l'item dins del drive (ex: /FitxesTecniques/60360.pdf)."""
    folder = (folder_path or '').strip().strip('/')
    if folder:
        return f"/{folder}/{filename}"
    return f"/{filename}"


def _ensure_folder(token, site_id, drive_id, folder_path):
    """Crea la carpeta a SharePoint si no existeix (idempotent, suporta carpetes niuades)."""
    folder = (folder_path or '').strip().strip('/')
    if not folder:
        return True, None

    headers = {'Authorization': f'Bearer {token}'}

    # Comprovar si ja existeix
    url = f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root:/{_quote_path(folder)}"
    try:
        r = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        return False, f"Error comprovant carpeta: {e}"
    if r.status_code == 200:
        return True, None
    if r.status_code != 404:
        LOG.warning('[SharePoint] GET carpeta %s -> %s: %s', folder, r.status_code, r.text[:300])
        return False, f"Error comprovant carpeta ({r.status_code}): {r.text[:200]}"

    # Crear segment a segment
    segments = folder.split('/')
    parent = ''
    for seg in segments:
        if parent:
            create_url = f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root:/{_quote_path(parent)}:/children"
        else:
            create_url = f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root/children"
        body = {
            'name': seg,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'replace',
        }
        try:
            r = requests.post(
                create_url,
                headers={**headers, 'Content-Type': 'application/json'},
                json=body, timeout=30,
            )
        except requests.RequestException as e:
            return False, f"Error creant carpeta '{seg}': {e}"
        if r.status_code not in (200, 201, 409):
            LOG.warning('[SharePoint] CREATE carpeta %s -> %s: %s', seg, r.status_code, r.text[:300])
            return False, f"No s'ha pogut crear '{seg}' ({r.status_code}): {r.text[:200]}"
        parent = f"{parent}/{seg}" if parent else seg

    return True, None


def _simple_upload(token, site_id, drive_id, item_path, pdf_path):
    """Upload simple per fitxers < 4 MB."""
    url = f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root:{_quote_path(item_path)}:/content"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/pdf',
    }
    with open(pdf_path, 'rb') as f:
        data = f.read()
    try:
        r = requests.put(url, headers=headers, data=data, timeout=120)
    except requests.RequestException as e:
        LOG.error('[SharePoint] PUT url=%s falla: %s', url, e)
        return None, f"Error pujant (simple): {e}"
    if r.status_code not in (200, 201):
        LOG.error('[SharePoint] PUT url=%s item_path=%r -> %s: %s',
                  url, item_path, r.status_code, r.text[:500])
        return None, f"Pujada simple fallida ({r.status_code}): {r.text[:300]}"
    return r.json(), None


def _session_upload(token, site_id, drive_id, item_path, pdf_path):
    """Upload session per fitxers >= 4 MB (chunked)."""
    create_url = f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root:{_quote_path(item_path)}:/createUploadSession"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    body = {'item': {'@microsoft.graph.conflictBehavior': 'replace'}}
    try:
        r = requests.post(create_url, headers=headers, json=body, timeout=30)
    except requests.RequestException as e:
        LOG.error('[SharePoint] createUploadSession url=%s falla: %s', create_url, e)
        return None, f"Error creant upload session: {e}"
    if r.status_code not in (200, 201):
        LOG.error('[SharePoint] createUploadSession url=%s item_path=%r -> %s: %s',
                  create_url, item_path, r.status_code, r.text[:500])
        return None, f"Upload session fallida ({r.status_code}): {r.text[:300]}"
    upload_url = r.json().get('uploadUrl')
    if not upload_url:
        return None, "Resposta sense uploadUrl"

    file_size = os.path.getsize(pdf_path)
    last_response = None
    with open(pdf_path, 'rb') as f:
        offset = 0
        while offset < file_size:
            chunk = f.read(CHUNK_SIZE)
            chunk_end = offset + len(chunk) - 1
            chunk_headers = {
                'Content-Length': str(len(chunk)),
                'Content-Range': f'bytes {offset}-{chunk_end}/{file_size}',
            }
            try:
                r = requests.put(upload_url, headers=chunk_headers, data=chunk, timeout=300)
            except requests.RequestException as e:
                return None, f"Error pujant chunk a offset {offset}: {e}"
            if r.status_code not in (200, 201, 202):
                return None, f"Chunk fallit a offset {offset} ({r.status_code}): {r.text[:300]}"
            last_response = r
            offset += len(chunk)

    if last_response is None:
        return None, "No s'ha pujat cap chunk"
    try:
        return last_response.json(), None
    except ValueError:
        return {}, None


def distribuir_sharepoint(pdf_path, art_codi, config, filename=None):
    """Puja un PDF a SharePoint Online via Microsoft Graph.

    Args:
        pdf_path: ruta local del fitxer PDF
        art_codi: codi article (fallback per nom de fitxer)
        config: dict amb tenant_id, client_id, client_secret, site_url,
                drive_name (opcional), folder_path (opcional)
        filename: nom del fitxer a SharePoint (si None, usa {art_codi}.pdf)

    Returns:
        dict amb 'ok' (bool), 'error' (str) i 'url' (str amb webUrl si ok)
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return {'ok': False, 'error': f"PDF no trobat: {pdf_path}"}

    tenant_id = (config.get('tenant_id') or '').strip()
    client_id = (config.get('client_id') or '').strip()
    client_secret = config.get('client_secret') or ''
    site_url = (config.get('site_url') or '').strip()

    if not (tenant_id and client_id and client_secret and site_url):
        return {'ok': False,
                'error': "Configuracio SharePoint incompleta (tenant_id, client_id, client_secret, site_url)"}

    token, err = _get_token(tenant_id, client_id, client_secret)
    if err:
        return {'ok': False, 'error': err}

    res, err = _resolve_site_drive(token, config)
    if err:
        return {'ok': False, 'error': err}
    site_id = res['site_id']
    drive_id = res['drive_id']

    folder_path = config.get('folder_path') or ''
    ok, err = _ensure_folder(token, site_id, drive_id, folder_path)
    if not ok:
        return {'ok': False, 'error': err}

    if not filename:
        filename = f'{art_codi}.pdf'
    item_path = _build_item_path(folder_path, filename)

    file_size = os.path.getsize(pdf_path)
    if file_size < SIMPLE_UPLOAD_LIMIT:
        item, err = _simple_upload(token, site_id, drive_id, item_path, pdf_path)
    else:
        item, err = _session_upload(token, site_id, drive_id, item_path, pdf_path)

    if err:
        return {'ok': False, 'error': err}

    web_url = (item or {}).get('webUrl', '')
    return {'ok': True, 'error': None, 'url': web_url}


def eliminar_sharepoint(art_codi, config, filename=None):
    """Elimina un PDF de SharePoint (si no existeix, no es considera error)."""
    tenant_id = (config.get('tenant_id') or '').strip()
    client_id = (config.get('client_id') or '').strip()
    client_secret = config.get('client_secret') or ''
    site_url = (config.get('site_url') or '').strip()

    if not (tenant_id and client_id and client_secret and site_url):
        return {'ok': False, 'error': "Configuracio SharePoint incompleta"}

    token, err = _get_token(tenant_id, client_id, client_secret)
    if err:
        return {'ok': False, 'error': err}

    res, err = _resolve_site_drive(token, config)
    if err:
        return {'ok': False, 'error': err}
    site_id = res['site_id']
    drive_id = res['drive_id']

    if not filename:
        filename = f'{art_codi}.pdf'
    folder_path = config.get('folder_path') or ''
    item_path = _build_item_path(folder_path, filename)

    url = f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root:{_quote_path(item_path)}"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        r = requests.delete(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        return {'ok': False, 'error': str(e)}

    if r.status_code in (200, 204, 404):
        return {'ok': True, 'error': None}
    return {'ok': False, 'error': f"Error eliminant ({r.status_code}): {r.text[:200]}"}
