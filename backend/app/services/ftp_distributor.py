"""Servei per distribuir PDFs via FTP/FTPS."""

import ftplib
import os


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

    try:
        if use_tls:
            ftp = ftplib.FTP_TLS()
            ftp.connect(host, port, timeout=30)
            ftp.login(user, password)
            ftp.prot_p()  # Activar proteccio de dades (canal de dades encriptat)
        else:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=30)
            ftp.login(user, password)

        if ftp_path and ftp_path != '/':
            ftp.cwd(ftp_path)

        if not filename:
            filename = f'{art_codi}.pdf'
        with open(pdf_path, 'rb') as f:
            ftp.storbinary(f'STOR {filename}', f)

        ftp.quit()

        url_base = config.get('url_publica', 'https://farineracoromina.com/fitxestecniques/')
        url = f'{url_base.rstrip("/")}/{filename}'
        return {'ok': True, 'error': None, 'url': url}

    except ftplib.all_errors as e:
        return {'ok': False, 'error': str(e)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


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

    try:
        ftp = _connectar_ftp(config)
        if not filename:
            filename = f'{art_codi}.pdf'
        ftp.delete(filename)
        ftp.quit()
        return {'ok': True, 'error': None}

    except ftplib.all_errors as e:
        error_msg = str(e)
        # Si el fitxer no existeix, no es considera error
        if '550' in error_msg:
            return {'ok': True, 'error': None}
        return {'ok': False, 'error': error_msg}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
