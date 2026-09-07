"""Servei per distribuir PDFs via SFTP (SSH File Transfer Protocol)."""

import logging
import threading
import os
import socket
import time

import paramiko

LOG = logging.getLogger(__name__)

RETRY_ATTEMPTS = 3
RETRY_DELAYS = (1, 4)


def _is_transient(exc):
    """Errors transitoris: timeout, connexió perduda, errors SSH temporals.

    Els errors d'autenticacio (AuthenticationException) NO son transitoris —
    no es reintenten per evitar bloquejar comptes per intents repetits.
    """
    if isinstance(exc, paramiko.ssh_exception.AuthenticationException):
        return False
    if isinstance(exc, (socket.timeout, TimeoutError, EOFError, ConnectionError)):
        return True
    if isinstance(exc, paramiko.ssh_exception.NoValidConnectionsError):
        return True
    if isinstance(exc, paramiko.ssh_exception.SSHException):
        return True
    if isinstance(exc, OSError):
        return True
    return False


def _connectar_sftp(config):
    """Connecta al servidor SFTP i retorna (client_ssh, sftp).

    Cal cridar client_ssh.close() (que tanca la sessio SFTP tambe).
    """
    host = config.get('host', '')
    port = int(config.get('port', 22))
    user = config.get('user', '')
    password = config.get('password', '')
    remote_path = config.get('path', '')
    # Timeout configurable (veure _connectar_ftp): per defecte 30s com sempre.
    timeout = int(config.get('timeout', 30))

    client = paramiko.SSHClient()
    # AutoAddPolicy: accepta la clau del servidor la primera vegada, com fa
    # FileZilla en xarxa interna. Si mai s'usa contra un servidor extern
    # caldria fixar la host key esperada aqui.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            port=port,
            username=user,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )

        sftp = client.open_sftp()
        if remote_path and remote_path not in ('.', '/'):
            sftp.chdir(remote_path)
    except Exception:
        # Si la sessio SSH ja estava establerta i despres ha fallat obrir el
        # canal SFTP o entrar a la ruta, cal tancar-la aqui: el cridador no
        # rebra mai el client i no la podra tancar ell. Una sessio penjada
        # consumeix una de les connexions que el servidor permet, i en una
        # auditoria de centenars de fitxes s'esgoten i tot passa a fer timeout.
        try:
            client.close()
        except Exception:
            pass
        raise

    return client, sftp


# Sessions SFTP reaprofitades, una per desti i per proces.
#
# Obrir una connexio per fitxa fa que els servidors amb proteccio
# anti-forca-bruta ens bloquegin: n'accepten unes quantes seguides i despres
# descarten els paquets en silenci, cosa que es veu com un timeout. Amb una
# auditoria de centenars de fitxes aixo vol dir que gairebe totes fallen.
#
# El lock serialitza l'us: un SFTPClient no es pot fer servir des de dos fils
# alhora, i aqui hi arriben tant el worker de jobs com les peticions HTTP.
_sessions = {}
_sessions_lock = threading.RLock()
SESSIO_MAX_INACTIVITAT = 300  # segons sense us abans de reconnectar


def _clau_sessio(config):
    return (config.get('host', ''), int(config.get('port', 22) or 22),
            config.get('user', ''), config.get('path', ''))


def _sessio_viva(entrada):
    try:
        transport = entrada['client'].get_transport()
        return transport is not None and transport.is_active()
    except Exception:
        return False


def _tancar_sessio(clau):
    """Tanca i oblida la sessio d'aquest desti (si n'hi ha)."""
    entrada = _sessions.pop(clau, None)
    if not entrada:
        return
    try:
        entrada['sftp'].close()
    except Exception:
        pass
    try:
        entrada['client'].close()
    except Exception:
        pass


def _obtenir_sessio(config):
    """Sessio SFTP d'aquest desti, reconnectant nomes si cal."""
    clau = _clau_sessio(config)
    entrada = _sessions.get(clau)
    if entrada:
        prou_recent = time.time() - entrada['ultim_us'] < SESSIO_MAX_INACTIVITAT
        if prou_recent and _sessio_viva(entrada):
            entrada['ultim_us'] = time.time()
            return entrada['sftp']
        _tancar_sessio(clau)

    client, sftp = _connectar_sftp(config)
    _sessions[clau] = {'client': client, 'sftp': sftp, 'ultim_us': time.time()}
    LOG.info('[SFTP] Sessio oberta amb %s@%s', config.get('user'), config.get('host'))
    return sftp


def tancar_sessions():
    """Tanca totes les sessions obertes (per scripts que acaben)."""
    with _sessions_lock:
        for clau in list(_sessions):
            _tancar_sessio(clau)


def distribuir_sftp(pdf_path, art_codi, config, filename=None):
    """Puja un PDF al servidor SFTP.

    Args:
        pdf_path: ruta local del fitxer PDF
        art_codi: codi article (fallback per nom del fitxer)
        config: dict amb host, port, user, password, path, url_publica
        filename: nom del fitxer al servidor (si None, usa {art_codi}.pdf)

    Returns:
        dict amb 'ok' (bool), 'error' (str si ha fallat) i 'url' (opcional)
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return {'ok': False, 'error': f"PDF no trobat: {pdf_path}"}

    host = config.get('host', '')
    port = int(config.get('port', 22))
    user = config.get('user', '')

    if not host or not user:
        return {'ok': False, 'error': "Configuracio SFTP incompleta (host o user buit)"}

    if not filename:
        filename = f'{art_codi}.pdf'
    LOG.info('[SFTP] Pujant %s a %s:%s%s', filename, host, port, config.get('path', '') or '/')

    def _intent():
        with _sessions_lock:
            try:
                _obtenir_sessio(config).put(pdf_path, filename)
            except Exception:
                # La sessio pot haver quedat inservible: tancar-la perque el
                # reintent en obri una de nova.
                _tancar_sessio(_clau_sessio(config))
                raise

    last_exc = None
    for i in range(RETRY_ATTEMPTS):
        try:
            _intent()
            url_base = config.get('url_publica', '')
            url = f'{url_base.rstrip("/")}/{filename}' if url_base else ''
            LOG.info('[SFTP] Pujat OK %s%s', filename, f' (intent {i+1})' if i > 0 else '')
            return {'ok': True, 'error': None, 'url': url}
        except Exception as e:
            last_exc = e
            if _is_transient(e) and i < RETRY_ATTEMPTS - 1:
                wait = RETRY_DELAYS[min(i, len(RETRY_DELAYS) - 1)]
                LOG.warning('[SFTP] Intent %d/%d ha fallat (transitori): %s. Reintenta en %ss',
                            i + 1, RETRY_ATTEMPTS, e, wait)
                time.sleep(wait)
                continue
            LOG.exception('[SFTP] Error pujant %s a %s (intent %d/%d)',
                          filename, host, i + 1, RETRY_ATTEMPTS)
            return {'ok': False, 'error': str(e)}

    return {'ok': False, 'error': str(last_exc) if last_exc else 'Error desconegut'}


def descarregar_sftp(filename, config, dest_path):
    """Descarrega un PDF del servidor SFTP al disc local.

    Returns:
        dict amb 'ok' (bool), 'error' (str si ha fallat) i 'not_found' (bool)
        per distingir un fitxer inexistent d'un error real.
    """
    host = config.get('host', '')
    user = config.get('user', '')

    if not host or not user:
        return {'ok': False, 'error': "Configuracio SFTP incompleta", 'not_found': False}

    with _sessions_lock:
        try:
            _obtenir_sessio(config).get(filename, dest_path)
            return {'ok': True, 'error': None, 'not_found': False}

        except FileNotFoundError as e:
            # El fitxer no hi es: es un resultat normal, la sessio segueix bona.
            return {'ok': False, 'error': str(e), 'not_found': True}
        except IOError as e:
            # paramiko llenca IOError amb errno ENOENT quan el fitxer no existeix
            if getattr(e, 'errno', None) == 2 or 'No such file' in str(e):
                return {'ok': False, 'error': str(e), 'not_found': True}
            _tancar_sessio(_clau_sessio(config))
            LOG.exception('[SFTP] Error IO descarregant %s', filename)
            return {'ok': False, 'error': str(e), 'not_found': False}
        except Exception as e:
            _tancar_sessio(_clau_sessio(config))
            LOG.exception('[SFTP] Error inesperat descarregant %s a %s', filename, host)
            return {'ok': False, 'error': str(e), 'not_found': False}


def eliminar_sftp(art_codi, config, filename=None):
    """Elimina un PDF del servidor SFTP.

    Si el fitxer no existeix, es considera OK (idempotent).
    """
    host = config.get('host', '')
    user = config.get('user', '')

    if not host or not user:
        return {'ok': False, 'error': "Configuracio SFTP incompleta"}

    if not filename:
        filename = f'{art_codi}.pdf'
    LOG.info('[SFTP] Eliminant %s a %s', filename, host)

    with _sessions_lock:
        try:
            try:
                _obtenir_sessio(config).remove(filename)
            except IOError as e:
                if getattr(e, 'errno', None) == 2 or 'No such file' in str(e):
                    LOG.info('[SFTP] %s no existia, considerat OK', filename)
                    return {'ok': True, 'error': None}
                raise
            LOG.info('[SFTP] Eliminat OK %s', filename)
            return {'ok': True, 'error': None}

        except Exception as e:
            _tancar_sessio(_clau_sessio(config))
            LOG.exception('[SFTP] Error inesperat eliminant %s a %s', filename, host)
            return {'ok': False, 'error': str(e)}
