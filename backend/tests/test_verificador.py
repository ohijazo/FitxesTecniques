"""Tests del servei de comprovacio de destins.

verificar_distribucio() nomes llegeix atributs, de manera que amb SimpleNamespace
i un filename explicit no cal ni base de dades ni context Flask.

Es comprova tambe que el fitxer temporal s'esborra sempre: l'auditoria massiva
en crea un per cada item i una fuita ompliria el disc del servidor.
"""

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import verificador
from app.services.verificador import verificar_distribucio


def _data(dia, mes, any_):
    return datetime(any_, mes, dia, tzinfo=timezone.utc)


@pytest.fixture
def fitxa():
    return SimpleNamespace(id=1, art_codi='60360', nom_producte='Farina morena')


@pytest.fixture
def versio():
    return SimpleNamespace(
        id=10, num_versio=5,
        data_revisio=_data(10, 6, 2024),
        data_comprovacio=_data(10, 6, 2024),
    )


@pytest.fixture
def desti():
    return SimpleNamespace(id=3, nom='FTP Farinera Coromina', tipus='ftp',
                           configuracio={'host': 'h', 'user': 'u'})


@pytest.fixture
def espia(monkeypatch):
    """Substitueix el descarregador i el parser, i recorda el temporal usat."""
    estat = {'tmp': None, 'descarrega': MagicMock(), 'parse': MagicMock()}

    def fake_descarregar(filename, config, dest_path):
        estat['tmp'] = dest_path
        return estat['descarrega'](filename, config, dest_path)

    # El mateix doble per als quatre tipus: aixi els tests poden canviar el
    # tipus del desti sense tocar la fixture.
    modul = SimpleNamespace(
        descarregar_ftp=fake_descarregar, descarregar_sftp=fake_descarregar,
        descarregar_xarxa=fake_descarregar,
        descarregar_sharepoint=fake_descarregar)
    monkeypatch.setattr(verificador.importlib, 'import_module', lambda _n: modul)
    monkeypatch.setattr('app.services.pdf_parser.parse_pdf', estat['parse'])
    return estat


def _pdf(rev='5', data_rev='10/06/2024', data_comp='10/06/2024'):
    return {'rev': rev, 'data_revisio': data_rev, 'data_comprovacio': data_comp}


def _ok():
    return {'ok': True, 'error': None, 'not_found': False}


# --- Casos que no toquen la xarxa ------------------------------------------

def test_desti_sap_no_es_verificable(fitxa, versio, espia):
    desti_sap = SimpleNamespace(id=9, nom='SAP', tipus='sap', configuracio={})

    res = verificar_distribucio(fitxa, versio, desti_sap, filename='60360.pdf')

    assert res['estat_verificacio'] == 'no_verificable'
    espia['descarrega'].assert_not_called()


def test_sense_versio_activa_no_es_verificable(fitxa, desti, espia):
    res = verificar_distribucio(fitxa, None, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'no_verificable'
    espia['descarrega'].assert_not_called()


# --- Comparacio de contingut ------------------------------------------------

def test_tot_coincideix(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'ok'
    assert res['nivell'] == 'contingut'
    assert res['diferencies'] == []
    assert res['desti_nom'] == 'FTP Farinera Coromina'


def test_revisio_diferent_es_desfasat(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf(rev='4')

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'desfasat'
    assert res['diferencies'] == ['rev']
    assert res['bd']['rev'] == 5
    assert res['desti_valors']['rev'] == '4'


def test_nomes_data_diferent(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf(data_rev='02/01/2023')

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'desfasat'
    assert res['diferencies'] == ['data_revisio']


def test_data_absent_al_pdf_no_compta_com_diferencia(fitxa, versio, desti, espia):
    """Criteri conservador: si el PDF no porta la data, no s'inventa un error."""
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf(data_rev='', data_comp='')

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'ok'
    assert res['diferencies'] == []


def test_pdf_sense_metadades_es_ok_a_nivell_existencia(fitxa, versio, desti, espia):
    """Producte comercialitzat: original de tercers, sense capcalera Rev."""
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf(rev='', data_rev='', data_comp='')

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'ok'
    assert res['nivell'] == 'existencia'


# --- Errors -----------------------------------------------------------------

def test_not_found_es_no_trobat(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = {'ok': False, 'error': '550',
                                        'not_found': True}

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'no_trobat'
    espia['parse'].assert_not_called()


def test_error_de_connexio_es_error_acces(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = {'ok': False, 'error': 'Connection refused',
                                        'not_found': False}

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'error_acces'
    assert 'Connection refused' in res['missatge']


def test_excepcio_del_descarregador_no_propaga(fitxa, versio, desti, espia):
    espia['descarrega'].side_effect = RuntimeError('socket mort')

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'error_acces'


def test_parse_que_falla_es_error_parseig(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = _ok()
    espia['parse'].side_effect = ValueError('PDF corrupte')

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'error_parseig'


# --- Higiene ----------------------------------------------------------------

@pytest.mark.parametrize('escenari', ['ok', 'not_found', 'error', 'parse_error'])
def test_el_temporal_sempre_s_esborra(fitxa, versio, desti, espia, escenari):
    if escenari == 'ok':
        espia['descarrega'].return_value = _ok()
        espia['parse'].return_value = _pdf()
    elif escenari == 'not_found':
        espia['descarrega'].return_value = {'ok': False, 'error': '550', 'not_found': True}
    elif escenari == 'error':
        espia['descarrega'].side_effect = RuntimeError('boom')
    else:
        espia['descarrega'].return_value = _ok()
        espia['parse'].side_effect = ValueError('corrupte')

    verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert espia['tmp'] is not None
    assert not os.path.exists(espia['tmp'])


def test_timeout_arriba_a_la_configuracio(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    verificar_distribucio(fitxa, versio, desti, filename='60360.pdf', timeout=10)

    config = espia['descarrega'].call_args[0][1]
    assert config['timeout'] == 10
    # No ha de mutar la configuracio guardada al desti
    assert 'timeout' not in desti.configuracio


# --- Direccio inversa: el fitxer NO hi hauria de ser ------------------------

def test_absent_on_no_hi_ha_de_ser_es_ok(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = {'ok': False, 'error': '550', 'not_found': True}

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf',
                                esperat=False)

    assert res['estat_verificacio'] == 'ok'
    assert res['nivell'] == 'absencia'
    assert res['esperat_al_desti'] is False
    espia['parse'].assert_not_called()


def test_present_on_no_hi_ha_de_ser_es_sobrant(fitxa, versio, desti, espia):
    """El cas que abans passava desapercebut: retirada que no es va completar."""
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf(rev='3')

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf',
                                esperat=False)

    assert res['estat_verificacio'] == 'sobrant'
    assert 'rev. 3' in res['missatge']
    assert res['desti_valors']['rev'] == '3'


def test_sobrant_illegible_segueix_sent_sobrant(fitxa, versio, desti, espia):
    """Que no es pugui parsejar no canvia el fet que hi es i no hi ha de ser."""
    espia['descarrega'].return_value = _ok()
    espia['parse'].side_effect = ValueError('PDF corrupte')

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf',
                                esperat=False)

    assert res['estat_verificacio'] == 'sobrant'


def test_error_dacces_no_es_confon_amb_absencia_correcta(fitxa, versio, desti, espia):
    """Si no s'arriba al desti no es pot afirmar que el fitxer no hi sigui."""
    espia['descarrega'].return_value = {'ok': False, 'error': 'Connection refused',
                                        'not_found': False}

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf',
                                esperat=False)

    assert res['estat_verificacio'] == 'error_acces'


def test_esperat_al_desti_sempre_al_resultat(fitxa, versio, desti, espia):
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['esperat_al_desti'] is True


# --- Enllac al fitxer del desti --------------------------------------------

def test_enllac_ftp_es_construeix_de_url_publica(fitxa, versio, desti, espia):
    desti.configuracio['url_publica'] = 'https://farineracoromina.com/fitxestecniques/'
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['enllac'] == 'https://farineracoromina.com/fitxestecniques/60360.pdf'


def test_enllac_explicit_te_prioritat_sobre_el_calculat(fitxa, versio, desti, espia):
    """El de l'historial es la URL exacta amb que es va pujar: mana."""
    desti.configuracio['url_publica'] = 'https://exemple.local/fitxes'
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf',
                                enllac='https://historic.local/60360.pdf')

    assert res['enllac'] == 'https://historic.local/60360.pdf'


def test_enllac_amb_espais_va_codificat(fitxa, versio, desti, espia):
    desti.configuracio['url_publica'] = 'https://exemple.local/fitxes'
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    res = verificar_distribucio(fitxa, versio, desti,
                                filename='60360 Farina morena.pdf')

    assert res['enllac'] == 'https://exemple.local/fitxes/60360%20Farina%20morena.pdf'


def test_enllac_xarxa_es_el_path_complet(fitxa, versio, espia):
    desti_xarxa = SimpleNamespace(
        id=4, nom='Carpeta', tipus='xarxa',
        configuracio={'ruta_base': r'\tomatera\Farinera', 'subcarpeta': 'Fitxes'})
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    res = verificar_distribucio(fitxa, versio, desti_xarxa, filename='60360.pdf')

    assert res['enllac'].endswith('60360.pdf')
    assert 'Fitxes' in res['enllac']


def test_hi_ha_enllac_encara_que_el_fitxer_no_hi_sigui(fitxa, versio, desti, espia):
    """Un 'no trobat' tambe ha de dir on s'ha mirat."""
    desti.configuracio['url_publica'] = 'https://exemple.local/fitxes'
    espia['descarrega'].return_value = {'ok': False, 'error': '550', 'not_found': True}

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['estat_verificacio'] == 'no_trobat'
    assert res['enllac'] == 'https://exemple.local/fitxes/60360.pdf'


def test_ftp_sense_url_publica_usa_el_valor_per_defecte(fitxa, versio, desti, espia):
    """El mateix que fa servir distribuir_ftp, aixi l'enllac coincideix."""
    from app.services.ftp_distributor import URL_PUBLICA_DEFECTE

    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    res = verificar_distribucio(fitxa, versio, desti, filename='60360.pdf')

    assert res['enllac'] == f"{URL_PUBLICA_DEFECTE.rstrip('/')}/60360.pdf"


def test_sharepoint_sense_historial_no_inventa_enllac(fitxa, versio, espia):
    """El webUrl de Graph no es pot construir: val mes no donar cap enllac que
    enviar l'usuari a un 404."""
    sp = SimpleNamespace(id=7, nom='SharePoint', tipus='sharepoint',
                         configuracio={'site_url': 'https://x.sharepoint.com/sites/q'})
    espia['descarrega'].return_value = _ok()
    espia['parse'].return_value = _pdf()

    res = verificar_distribucio(fitxa, versio, sp, filename='60360.pdf')

    assert res['enllac'] is None
