"""Servei per distribuir PDFs via FTP/FTPS."""

import ftplib
import logging
import os
import socket
import time

LOG = logging.getLogger(__name__)

# Reintents per errors transitoris (xarxa / 4xx). Errors d'autenticació (5xx)
# o de fitxer (550) NO es reintenten per evitar bloquejar comptes per intents
# repetits incorrectes.
RETRY_ATTEMPTS = 3
RETRY_DELAYS = (1, 4)  # segons entre intent 1->2 i 2->3


def _is_transient(exc):
    """Errors transitoris: timeout, connexió perduda, errors temporals FTP (4xx)."""
    if isinstance(exc, (socket.timeout, ConnectionError, ftplib.error_temp)):
        return True
    # Algunes implementacions llencen OSError genèric per network issues
    if isinstance(exc, OSError) and not isinstance(exc, ftplib.error_perm):
        return True
    return False


def distribuir_ftp(pdf_path, art_codi, config, filename=None):
    """Puja un PDF al servidor FTP (amb TLS si disponible).

    Args:
        pdf_path: ruta local del fitxer PDF
        art_codi: codi article (fallback per nom del fitxer)
        config: dict amb host, port, user, password, path, tls
        filename: nom del fitxer al FTP (si None, usa {art_codi}.pdf)

    Returns:
        dict amb 'ok' (bool) i 'error' (str si ha fallat)
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return {'ok': False, 'error': f"PDF no trobat: {pdf_path}"}

    host = config.get('host', '')
    port = int(config.get('port', 21))
    user = config.get('user', '')
    password = config.get('password', '')
    ftp_path = config.get('path', '')
    use_tls = config.get('tls', True)

    if not host or not user:
        return {'ok': False, 'error': "Configuracio FTP incompleta (host o user buit)"}

    if not filename:
        filename = f'{art_codi}.pdf'
    LOG.info('[FTP] Pujant %s a %s:%s%s (tls=%s)', filename, host, port, ftp_path or '/', use_tls)

    def _intent():
        if use_tls:
            ftp = ftplib.FTP_TLS()
            ftp.connect(host, port, timeout=30)
            ftp.login(user, password)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=30)
            ftp.login(user, password)

        if ftp_path and ftp_path != '/':
            ftp.cwd(ftp_path)

        with open(pdf_path, 'rb') as f:
            ftp.storbinary(f'STOR {filename}', f)

        ftp.quit()

    last_exc = None
    for i in range(RETRY_ATTEMPTS):
        try:
            _intent()
            url_base = config.get('url_publica', 'https://farineracoromina.com/fitxestecniques/')
            url = f'{url_base.rstrip("/")}/{filename}'
            LOG.info('[FTP] Pujat OK %s%s', filename, f' (intent {i+1})' if i > 0 else '')
            return {'ok': True, 'error': None, 'url': url}
        except Exception as e:
            last_exc = e
            if _is_transient(e) and i < RETRY_ATTEMPTS - 1:
                wait = RETRY_DELAYS[min(i, len(RETRY_DELAYS) - 1)]
                LOG.warning('[FTP] Intent %d/%d ha fallat (transitori): %s. Reintenta en %ss',
                            i + 1, RETRY_ATTEMPTS, e, wait)
                time.sleep(wait)
                continue
            # No transitori o últim intent: abortar
            LOG.exception('[FTP] Error pujant %s a %s (intent %d/%d)',
                          filename, host, i + 1, RETRY_ATTEMPTS)
            return {'ok': False, 'error': str(e)}

    return {'ok': False, 'error': str(last_exc) if last_exc else 'Error desconegut'}


def _connectar_ftp(config):
    """Connecta al servidor FTP i retorna l'objecte ftp."""
    host = config.get('host', '')
    port = int(config.get('port', 21))
    user = config.get('user', '')
    password = config.get('password', '')
    ftp_path = config.get('path', '')
    use_tls = config.get('tls', True)

    if use_tls:
        ftp = ftplib.FTP_TLS()
        ftp.connect(host, port, timeout=30)
        ftp.login(user, password)
        ftp.prot_p()
    else:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=30)
        ftp.login(user, password)

    if ftp_path and ftp_path != '/':
        ftp.cwd(ftp_path)

    return ftp


def descarregar_ftp(filename, config, dest_path):
    """Descarrega un PDF del servidor FTP al disc local.

    Args:
        filename: nom del fitxer al FTP (ex: '60360.pdf')
        config: dict amb host, port, user, password, path, tls
        dest_path: ruta local on guardar el fitxer descarregat

    Returns:
        dict amb 'ok' (bool), 'error' (str si ha fallat) i 'not_found' (bool)
        per distingir un 550 (no existeix) d'un error real.
    """
    host = config.get('host', '')
    user = config.get('user', '')

    if not host or not user:
        return {'ok': False, 'error': "Configuracio FTP incompleta", 'not_found': False}

    try:
        ftp = _connectar_ftp(config)
        with open(dest_path, 'wb') as f:
            ftp.retrbinary(f'RETR {filename}', f.write)
        ftp.quit()
        return {'ok': True, 'error': None, 'not_found': False}

    except ftplib.error_perm as e:
        error_msg = str(e)
        if '550' in error_msg:
            return {'ok': False, 'error': error_msg, 'not_found': True}
        LOG.exception('[FTP] Error de permis descarregant %s', filename)
        return {'ok': False, 'error': error_msg, 'not_found': False}
    except Exception as e:
        LOG.exception('[FTP] Error inesperat descarregant %s a %s', filename, host)
        return {'ok': False, 'error': str(e), 'not_found': False}


def eliminar_ftp(art_codi, config, filename=None):
    """Elimina un PDF del servidor FTP.

    Args:
        art_codi: codi article (nom del fitxer al FTP)
        config: dict amb host, port, user, password, path, tls

    Returns:
        dict amb 'ok' (bool) i 'error' (str si ha fallat)
    """
    host = config.get('host', '')
    user = config.get('user', '')

    if not host or not user:
        return {'ok': False, 'error': "Configuracio FTP incompleta"}

    if not filename:
        filename = f'{art_codi}.pdf'
    LOG.info('[FTP] Eliminant %s a %s', filename, host)

    try:
        ftp = _connectar_ftp(config)
        ftp.delete(filename)
        ftp.quit()
        LOG.info('[FTP] Eliminat OK %s', filename)
        return {'ok': True, 'error': None}

    except ftplib.all_errors as e:
        error_msg = str(e)
        # Si el fitxer no existeix, no es considera error
        if '550' in error_msg:
            LOG.info('[FTP] %s no existia (550), considerat OK', filename)
            return {'ok': True, 'error': None}
        LOG.exception('[FTP] Error eliminant %s a %s', filename, host)
        return {'ok': False, 'error': error_msg}
    except Exception as e:
        LOG.exception('[FTP] Error inesperat eliminant %s a %s', filename, host)
        return {'ok': False, 'error': str(e)}
