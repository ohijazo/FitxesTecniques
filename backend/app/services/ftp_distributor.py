"""Servei per distribuir PDFs via FTP/FTPS."""

import ftplib
import os


def distribuir_ftp(pdf_path, art_codi, config):
    """Puja un PDF al servidor FTP (amb TLS si disponible).

    Args:
        pdf_path: ruta local del fitxer PDF
        art_codi: codi article (nom del fitxer al FTP)
        config: dict amb host, port, user, password, path, tls

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

        filename = f'{art_codi}.pdf'
        with open(pdf_path, 'rb') as f:
            ftp.storbinary(f'STOR {filename}', f)

        ftp.quit()
        return {'ok': True, 'error': None}

    except ftplib.all_errors as e:
        return {'ok': False, 'error': str(e)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
