"""Servei per distribuir PDFs a carpetes de xarxa (SMB/CIFS)."""

import os
import shutil
import subprocess
import platform


def _connect_share(share_path, user, password, domain=''):
    """Connecta a una carpeta de xarxa amb credencials (Windows: net use)."""
    if platform.system() != 'Windows':
        # En Linux, assumim que la carpeta esta muntada via fstab/mount
        return {'ok': True, 'error': None}

    try:
        # Desconnectar primer si existeix connexio anterior
        subprocess.run(
            ['net', 'use', share_path, '/delete', '/y'],
            capture_output=True, timeout=10
        )

        # Connectar amb credencials
        cmd = ['net', 'use', share_path, f'/user:{domain}\\{user}' if domain else f'/user:{user}', password]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode != 0:
            return {'ok': False, 'error': f'Error connectant: {result.stderr.strip()}'}

        return {'ok': True, 'error': None}

    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Timeout connectant a la carpeta de xarxa'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def _disconnect_share(share_path):
    """Desconnecta la carpeta de xarxa."""
    if platform.system() != 'Windows':
        return
    try:
        subprocess.run(
            ['net', 'use', share_path, '/delete', '/y'],
            capture_output=True, timeout=10
        )
    except Exception:
        pass


def distribuir_xarxa(pdf_path, art_codi, config):
    """Copia un PDF a una carpeta de xarxa.

    Args:
        pdf_path: ruta local del fitxer PDF
        art_codi: codi article (nom del fitxer)
        config: dict amb ruta_base, user, password, domain, subcarpeta

    Returns:
        dict amb 'ok' (bool), 'error' (str) i 'path' (str)
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return {'ok': False, 'error': f"PDF no trobat: {pdf_path}"}

    ruta_base = config.get('ruta_base', '').strip()
    user = config.get('user', '')
    password = config.get('password', '')
    domain = config.get('domain', '')
    subcarpeta = config.get('subcarpeta', '').strip()

    if not ruta_base:
        return {'ok': False, 'error': "Ruta de xarxa no configurada"}

    # Construir ruta completa
    # ruta_base: \\servidor\compartit
    # subcarpeta: ProvaFitxesTecniques (opcional)
    dest_dir = ruta_base
    if subcarpeta:
        dest_dir = os.path.join(ruta_base, subcarpeta)

    filename = f'{art_codi}.pdf'
    dest_path = os.path.join(dest_dir, filename)

    # Intent 1: copiar directament (funciona si ja estem autenticats a la xarxa)
    try:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(pdf_path, dest_path)
        return {'ok': True, 'error': None, 'path': dest_path}
    except (PermissionError, FileNotFoundError, OSError):
        pass

    # Intent 2: connectar amb credencials i reintentar
    if user and password:
        conn = _connect_share(ruta_base, user, password, domain)
        if not conn['ok']:
            return conn

        try:
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(pdf_path, dest_path)
            return {'ok': True, 'error': None, 'path': dest_path}
        except PermissionError as e:
            return {'ok': False, 'error': f"Sense permisos: {e}"}
        except FileNotFoundError as e:
            return {'ok': False, 'error': f"Ruta no trobada: {e}"}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    return {'ok': False, 'error': f"No es pot accedir a {dest_dir}"}


def eliminar_xarxa(art_codi, config):
    """Elimina un PDF de la carpeta de xarxa."""
    ruta_base = config.get('ruta_base', '').strip()
    subcarpeta = config.get('subcarpeta', '').strip()
    user = config.get('user', '')
    password = config.get('password', '')
    domain = config.get('domain', '')

    if not ruta_base:
        return {'ok': False, 'error': "Ruta no configurada"}

    dest_dir = ruta_base
    if subcarpeta:
        dest_dir = os.path.join(ruta_base, subcarpeta)

    try:
        if user and password:
            _connect_share(ruta_base, user, password, domain)

        filepath = os.path.join(dest_dir, f'{art_codi}.pdf')
        if os.path.exists(filepath):
            os.remove(filepath)

        return {'ok': True, 'error': None}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
