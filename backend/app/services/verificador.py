"""Comprovacio que una fitxa existeix REALMENT al desti on consta distribuida.

L'estat 'ok' d'una Distribucio nomes vol dir que la pujada no va fallar: ningu
no torna a consultar el desti despres. Aquest servei ho comprova de veritat:
descarrega el PDF del desti i compara la revisio i les dates amb la BD.

REGLA CLAU: aquest modul NO escriu res a la base de dades. Nomes informa.
"""

import importlib
import logging
import os
import tempfile
from datetime import datetime, timezone
from urllib.parse import quote

LOG = logging.getLogger(__name__)

# Vocabulari d'estats de comprovacio (no es barreja amb Distribucio.estat).
ESTATS = (
    'ok',              # tal com ha de ser: hi es i concorda, o no hi es i no hi ha de ser
    'no_trobat',       # hauria de ser-hi i no hi es
    'desfasat',        # hi es pero la revisio/dates no concorden amb la BD
    'sobrant',         # hi es i NO hi hauria de ser (retirada que no es va completar)
    'error_acces',     # no s'ha pogut arribar al desti (xarxa, credencials...)
    'error_parseig',   # s'ha descarregat pero no s'ha pogut llegir el PDF
    'no_verificable',  # tipus de desti sense descarrega (sap) o sense versio
)

# Tots els descarregadors comparteixen la signatura (filename, config, dest_path)
# i retornen {'ok', 'error', 'not_found'}.
_DESCARREGADORS = {
    'ftp': ('app.services.ftp_distributor', 'descarregar_ftp'),
    'sftp': ('app.services.sftp_distributor', 'descarregar_sftp'),
    'xarxa': ('app.services.smb_distributor', 'descarregar_xarxa'),
    'sharepoint': ('app.services.sharepoint_distributor', 'descarregar_sharepoint'),
}


def _parse_pdf_date(s):
    """Converteix 'dd/mm/aaaa' a datetime UTC. None si invalid o buit."""
    if not s:
        return None
    try:
        return datetime.strptime(s, '%d/%m/%Y').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _dates_iguals(a, b):
    """Compara dues dates ignorant l'hora (nomes any/mes/dia)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return (a.year, a.month, a.day) == (b.year, b.month, b.day)


def _data_str(dt):
    return dt.strftime('%d/%m/%Y') if dt else ''


def _resultat(desti, filename, estat, missatge, **extra):
    base = {
        'estat_verificacio': estat,
        'nivell': extra.pop('nivell', None),
        'desti_id': getattr(desti, 'id', None),
        'desti_nom': getattr(desti, 'nom', ''),
        'desti_tipus': getattr(desti, 'tipus', ''),
        'filename': filename,
        'enllac': extra.pop('enllac', None),
        'missatge': missatge,
        'bd': extra.pop('bd', None),
        'desti_valors': extra.pop('desti_valors', None),
        'diferencies': extra.pop('diferencies', []),
        'esperat_al_desti': extra.pop('esperat', None),
        'comprovat_at': datetime.now(timezone.utc).isoformat(),
    }
    base.update(extra)
    return base


def _enllac_previst(desti, config, filename):
    """Enllac al fitxer deduit de la configuracio del desti.

    Nomes s'usa quan no hi ha cap distribucio 'ok' d'on treure la URL real.
    SharePoint queda fora: el webUrl de Graph no es pot construir de manera
    fiable a partir del site_url, i inventar-lo enviaria l'usuari a un 404.
    """
    tipus = getattr(desti, 'tipus', '')

    if tipus in ('ftp', 'sftp'):
        base = (config.get('url_publica') or '').strip().rstrip('/')
        if not base and tipus == 'ftp':
            # Mateix valor que fa servir distribuir_ftp per construir la URL
            # que desa a Distribucio, aixi l'enllac es el mateix.
            from app.services.ftp_distributor import URL_PUBLICA_DEFECTE
            base = URL_PUBLICA_DEFECTE.rstrip('/')
        return f'{base}/{quote(filename)}' if base else None

    if tipus == 'xarxa':
        base = (config.get('ruta_base') or '').strip()
        if not base:
            return None
        sub = (config.get('subcarpeta') or '').strip()
        return os.path.join(base, sub, filename) if sub else os.path.join(base, filename)

    return None


def _config_desti(desti, timeout=None):
    """Configuracio del desti, desxifrada si el model ho suporta."""
    if hasattr(desti, 'configuracio_segura'):
        config = dict(desti.configuracio_segura() or {})
    else:
        config = dict(desti.configuracio or {})
    if timeout:
        config['timeout'] = timeout
    return config


def verificar_distribucio(fitxa, versio, desti, filename=None, timeout=None,
                          esperat=True, enllac=None):
    """Comprova el desti i hi afegeix l'enllac al fitxer, per poder-lo revisar.

    L'enllac surt de l'ultima distribucio 'ok' (es la URL exacta amb que es va
    pujar) i, si no n'hi ha, es dedueix de la configuracio del desti.
    """
    if filename is None:
        # Import mandros: distribucions.py importa models, i aquest modul
        # s'ha de poder usar sense context Flask quan es passa filename.
        from app.routes.distribucions import _referencia_al_desti
        filename, enllac_historic = _referencia_al_desti(fitxa, versio, desti)
        enllac = enllac or enllac_historic

    resultat = _verificar(fitxa, versio, desti, filename, timeout, esperat)

    if not resultat.get('enllac'):
        try:
            config = _config_desti(desti)
            resultat['enllac'] = enllac or _enllac_previst(desti, config, filename)
        except Exception:  # una config il·legible no ha de tombar la comprovacio
            resultat['enllac'] = enllac
    return resultat


def _verificar(fitxa, versio, desti, filename, timeout, esperat):
    """Comprova si l'estat real del desti coincideix amb el que diu la BD.

    La comprovacio es bidireccional: `esperat` diu si la fitxa HI HA DE SER.
      - esperat=True  -> ha de ser-hi i coincidir  (si no: no_trobat / desfasat)
      - esperat=False -> NO hi ha de ser           (si hi es: sobrant)

    Args:
        fitxa: FitxaTecnica
        versio: VersioFitxa (normalment l'activa)
        desti: DestiDistribucio
        filename: nom al desti; si es None s'infereix de l'historial (fa consulta)
        timeout: segons de connexio (mode sincron el baixa per no bloquejar HTTP)
        esperat: si la BD diu que la fitxa hi es ara mateix

    Returns:
        dict normalitzat (veure _resultat). Mai llenca excepcio ni escriu a la BD.
    """
    tipus = getattr(desti, 'tipus', '')

    if versio is None:
        return _resultat(desti, filename, 'no_verificable',
                         "La fitxa no te cap versio activa", esperat=esperat)

    if tipus not in _DESCARREGADORS:
        return _resultat(desti, filename, 'no_verificable',
                         f"Els destins de tipus '{tipus}' no es poden comprovar",
                         esperat=esperat)

    modul, func = _DESCARREGADORS[tipus]
    descarregar = getattr(importlib.import_module(modul), func)
    config = _config_desti(desti, timeout)

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        try:
            res = descarregar(filename, config, tmp_path)
        except Exception as e:  # cap error de xarxa ha de tombar l'auditoria
            LOG.exception('[Verificacio] Error descarregant %s de %s', filename,
                          getattr(desti, 'nom', ''))
            return _resultat(desti, filename, 'error_acces', str(e),
                             esperat=esperat)

        if not res.get('ok'):
            if res.get('not_found'):
                if not esperat:
                    # Correctament absent: es el resultat desitjat, no una incidencia.
                    return _resultat(desti, filename, 'ok',
                                     "No hi es, i no hi ha de ser",
                                     nivell='absencia', esperat=esperat)
                return _resultat(desti, filename, 'no_trobat',
                                 f"El fitxer '{filename}' no hi es", esperat=esperat)
            return _resultat(desti, filename, 'error_acces',
                             res.get('error') or "No s'ha pogut accedir al desti",
                             esperat=esperat)

        # El fitxer HI ES. Si no hi hauria de ser ja tenim el veredicte: es una
        # copia que va quedar enrere (retirada que no es va completar, o pujada
        # a un desti que despres es va desmarcar).
        from app.services.pdf_parser import parse_pdf
        try:
            parsed = parse_pdf(tmp_path) or {}
        except Exception as e:
            if not esperat:
                # Que no es pugui llegir no canvia el fet que hi es i sobra.
                LOG.warning('[Verificacio] Sobrant illegible %s: %s', filename, e)
                return _resultat(desti, filename, 'sobrant',
                                 f"Hi ha un fitxer '{filename}' que no hi hauria de ser",
                                 esperat=esperat)
            LOG.warning('[Verificacio] Error parsejant %s: %s', filename, e)
            return _resultat(desti, filename, 'error_parseig',
                             f"El PDF del desti no s'ha pogut llegir: {e}",
                             esperat=esperat)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not esperat:
        rev_pdf = (parsed.get('rev') or '').strip()
        detall = f" (rev. {rev_pdf})" if rev_pdf else ''
        return _resultat(
            desti, filename, 'sobrant',
            f"Hi ha un fitxer '{filename}'{detall} que no hi hauria de ser",
            bd={'rev': versio.num_versio,
                'data_revisio': _data_str(versio.data_revisio),
                'data_comprovacio': _data_str(versio.data_comprovacio)},
            desti_valors={'rev': rev_pdf,
                          'data_revisio': parsed.get('data_revisio') or '',
                          'data_comprovacio': parsed.get('data_comprovacio') or ''},
            esperat=esperat)

    return _comparar(fitxa, versio, desti, filename, parsed, esperat)


def _comparar(fitxa, versio, desti, filename, parsed, esperat=True):
    """Compara les metadades del PDF descarregat amb les de la BD."""
    rev_pdf = (parsed.get('rev') or '').strip()
    data_rev_pdf = _parse_pdf_date(parsed.get('data_revisio'))
    data_comp_pdf = _parse_pdf_date(parsed.get('data_comprovacio'))

    bd = {
        'rev': versio.num_versio,
        'data_revisio': _data_str(versio.data_revisio),
        'data_comprovacio': _data_str(versio.data_comprovacio),
    }
    desti_valors = {
        'rev': rev_pdf,
        'data_revisio': parsed.get('data_revisio') or '',
        'data_comprovacio': parsed.get('data_comprovacio') or '',
    }

    # Els PDFs de producte comercialitzat son originals de tercers: no porten la
    # capcalera 'Rev.:' i no hi ha res comparable. Confirmar que hi son ja es
    # tota la informacio disponible.
    if not rev_pdf and data_rev_pdf is None and data_comp_pdf is None:
        return _resultat(
            desti, filename, 'ok',
            "El PDF hi es, pero no porta metadades comparables (rev ni dates)",
            nivell='existencia', bd=bd, desti_valors=desti_valors,
            esperat=esperat)

    diferencies = []
    if rev_pdf and rev_pdf != str(versio.num_versio):
        diferencies.append('rev')
    # Si el PDF no porta una data, no compta com a diferencia (criteri
    # conservador, el mateix que sync_dates_from_ftp.py sense --force-null).
    if data_rev_pdf is not None and not _dates_iguals(versio.data_revisio, data_rev_pdf):
        diferencies.append('data_revisio')
    if data_comp_pdf is not None and not _dates_iguals(versio.data_comprovacio, data_comp_pdf):
        diferencies.append('data_comprovacio')

    if not diferencies:
        return _resultat(desti, filename, 'ok',
                         "El PDF del desti coincideix amb la fitxa",
                         nivell='contingut', bd=bd, desti_valors=desti_valors,
                         esperat=esperat)

    if 'rev' in diferencies:
        missatge = (f"La revisio del desti ({rev_pdf}) no coincideix amb la de "
                    f"la BD ({versio.num_versio})")
    else:
        camps = ' i '.join(d.replace('_', ' ') for d in diferencies)
        missatge = f"El PDF del desti te una {camps} diferent de la BD"

    return _resultat(desti, filename, 'desfasat', missatge,
                     nivell='contingut', bd=bd, desti_valors=desti_valors,
                     diferencies=diferencies, esperat=esperat)
