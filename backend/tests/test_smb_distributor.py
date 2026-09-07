"""Tests de descarregar_xarxa (carpeta de xarxa / SMB).

El cas critic: os.path.exists() retorna False tant si el fitxer no hi es com si
el share esta caigut. Confondre'ls faria que una auditoria amb la carpeta
inaccessible reportes centenars de "no trobat" falsos.
"""

import os
from unittest.mock import patch

from app.services.smb_distributor import descarregar_xarxa


def test_fitxer_present_es_descarrega(config_xarxa, tmp_path):
    origen = os.path.join(config_xarxa['ruta_base'], '60360.pdf')
    with open(origen, 'wb') as f:
        f.write(b'%PDF-1.4 contingut')

    desti = tmp_path / 'baixat.pdf'
    res = descarregar_xarxa('60360.pdf', config_xarxa, str(desti))

    assert res['ok'] is True
    assert res['not_found'] is False
    assert desti.read_bytes() == b'%PDF-1.4 contingut'


def test_directori_accessible_i_fitxer_absent_es_not_found(config_xarxa, tmp_path):
    res = descarregar_xarxa('60360.pdf', config_xarxa, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is True


def test_directori_inaccessible_no_es_not_found(config_xarxa, tmp_path):
    """El cas que evita el fals massiu: share caigut != fitxer inexistent."""
    config_xarxa['ruta_base'] = str(tmp_path / 'servidor-que-no-existeix')

    res = descarregar_xarxa('60360.pdf', config_xarxa, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is False
    assert "No s'arriba" in res['error']


def test_subcarpeta_es_respectada(config_xarxa, tmp_path):
    sub = os.path.join(config_xarxa['ruta_base'], 'Fitxes')
    os.makedirs(sub)
    with open(os.path.join(sub, '60360.pdf'), 'wb') as f:
        f.write(b'%PDF dins subcarpeta')
    config_xarxa['subcarpeta'] = 'Fitxes'

    desti = tmp_path / 'baixat.pdf'
    res = descarregar_xarxa('60360.pdf', config_xarxa, str(desti))

    assert res['ok'] is True
    assert desti.read_bytes() == b'%PDF dins subcarpeta'


def test_ruta_no_configurada(config_xarxa, tmp_path):
    config_xarxa['ruta_base'] = ''

    res = descarregar_xarxa('60360.pdf', config_xarxa, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is False


def test_amb_credencials_intenta_connectar_si_no_hi_arriba(config_xarxa, tmp_path):
    """Si el directori no es visible i hi ha credencials, prova d'autenticar-se."""
    config_xarxa['ruta_base'] = str(tmp_path / 'share-remot')
    config_xarxa['user'] = 'ohijazo'
    config_xarxa['password'] = 'secret'

    with patch('app.services.smb_distributor._connect_share',
               return_value={'ok': True, 'error': None}) as connect:
        res = descarregar_xarxa('60360.pdf', config_xarxa, str(tmp_path / 'x.pdf'))

    connect.assert_called_once()
    # El directori segueix sense existir: error d'acces, mai not_found
    assert res['not_found'] is False
