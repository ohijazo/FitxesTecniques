"""Tests del distribuidor SFTP.

Mateixa politica que el FTP, amb un matis important: paramiko distingeix
AuthenticationException (permanent, NO reintentar) de la resta de
SSHException (transitories, si reintentar).
"""

import socket
from unittest.mock import patch

import paramiko
import pytest

from app.services import sftp_distributor
from app.services.sftp_distributor import (
    RETRY_ATTEMPTS,
    descarregar_sftp,
    distribuir_sftp,
    eliminar_sftp,
    _is_transient,
)


@pytest.fixture(autouse=True)
def sessio_neta():
    """Buida la sessio SFTP reaprofitada abans i despres de cada test.

    Sense aixo, el client simulat d'un test es reutilitzaria al seguent: la
    sessio es considera viva perque get_transport().is_active() d'un MagicMock
    sempre es cert.
    """
    sftp_distributor._sessions.clear()
    yield
    sftp_distributor._sessions.clear()


def _sftp_de(fake_client):
    """La sessio SFTP que retorna el client mockejat."""
    return fake_client.return_value.open_sftp.return_value


# --- Validacio previa -------------------------------------------------------

def test_pdf_inexistent_no_connecta(config_sftp):
    with patch('paramiko.SSHClient') as fake:
        res = distribuir_sftp('/no/existeix.pdf', '60360', config_sftp)

    assert res['ok'] is False
    assert 'PDF no trobat' in res['error']
    fake.assert_not_called()


@pytest.mark.parametrize('camp', ['host', 'user'])
def test_config_incompleta_no_connecta(config_sftp, pdf_temporal, camp):
    config_sftp[camp] = ''

    with patch('paramiko.SSHClient') as fake:
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['ok'] is False
    assert 'incompleta' in res['error']
    fake.assert_not_called()


# --- Pujada correcta --------------------------------------------------------

def test_puja_ok_i_mante_la_sessio_oberta(config_sftp, pdf_temporal):
    """La sessio NO es tanca despres de cada operacio: es reaprofita.

    Obrir una connexio per fitxa fa que els servidors amb proteccio
    anti-forca-bruta ens bloquegin a partir de la cinquena.
    """
    with patch('paramiko.SSHClient') as fake:
        sftp = _sftp_de(fake)
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['ok'] is True
    sftp.put.assert_called_once_with(pdf_temporal, '60360.pdf')
    sftp.chdir.assert_called_once_with('/fitxestecniques')
    fake.return_value.close.assert_not_called()


def test_operacions_seguides_no_reconnecten(config_sftp, pdf_temporal, tmp_path):
    """Tres operacions al mateix desti han de fer servir UNA sola connexio."""
    with patch('paramiko.SSHClient') as fake:
        _sftp_de(fake)
        distribuir_sftp(pdf_temporal, '60360', config_sftp)
        descarregar_sftp('60360.pdf', config_sftp, str(tmp_path / 'a.pdf'))
        descarregar_sftp('60361.pdf', config_sftp, str(tmp_path / 'b.pdf'))

    assert fake.return_value.connect.call_count == 1


def test_sessio_morta_es_reconnecta(config_sftp, tmp_path):
    """Si el servidor ha tancat la connexio pel seu compte, se n'obre una de nova."""
    with patch('paramiko.SSHClient') as fake:
        _sftp_de(fake)
        descarregar_sftp('60360.pdf', config_sftp, str(tmp_path / 'a.pdf'))
        fake.return_value.get_transport.return_value.is_active.return_value = False
        descarregar_sftp('60361.pdf', config_sftp, str(tmp_path / 'b.pdf'))

    assert fake.return_value.connect.call_count == 2


def test_destins_diferents_no_comparteixen_sessio(config_sftp, tmp_path):
    altre = dict(config_sftp, host='altre.exemple.local')
    with patch('paramiko.SSHClient') as fake:
        _sftp_de(fake)
        descarregar_sftp('60360.pdf', config_sftp, str(tmp_path / 'a.pdf'))
        descarregar_sftp('60360.pdf', altre, str(tmp_path / 'b.pdf'))

    assert fake.return_value.connect.call_count == 2


def test_filename_explicit_te_prioritat_sobre_art_codi(config_sftp, pdf_temporal):
    with patch('paramiko.SSHClient') as fake:
        sftp = _sftp_de(fake)
        distribuir_sftp(pdf_temporal, '60360', config_sftp, filename='60360_ES.pdf')

    assert sftp.put.call_args[0][1] == '60360_ES.pdf'


def test_tanca_connexio_encara_que_falli_la_pujada(config_sftp, pdf_temporal):
    """Una pujada fallida no ha de deixar la sessio SSH oberta."""
    with patch('paramiko.SSHClient') as fake:
        sftp = _sftp_de(fake)
        sftp.put.side_effect = paramiko.ssh_exception.AuthenticationException('denegat')
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['ok'] is False
    fake.return_value.close.assert_called_once()


def test_url_buida_si_no_hi_ha_url_publica(config_sftp, pdf_temporal):
    with patch('paramiko.SSHClient'):
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['url'] == ''


def test_url_construida_si_hi_ha_url_publica(config_sftp, pdf_temporal):
    config_sftp['url_publica'] = 'https://exemple.local/fitxes/'

    with patch('paramiko.SSHClient'):
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['url'] == 'https://exemple.local/fitxes/60360.pdf'


# --- Politica de reintents --------------------------------------------------

def test_error_autenticacio_no_es_reintenta(config_sftp, pdf_temporal):
    """Reintentar credencials incorrectes bloquejaria el compte del servidor."""
    with patch('paramiko.SSHClient') as fake:
        fake.return_value.connect.side_effect = (
            paramiko.ssh_exception.AuthenticationException('Auth failed')
        )
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['ok'] is False
    assert fake.call_count == 1


def test_error_transitori_es_reintenta_i_acaba_ok(config_sftp, pdf_temporal):
    with patch('paramiko.SSHClient') as fake:
        _sftp_de(fake).put.side_effect = [socket.timeout('timeout'), None]
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['ok'] is True
    assert fake.call_count == 2


def test_error_transitori_esgota_els_reintents(config_sftp, pdf_temporal):
    with patch('paramiko.SSHClient') as fake:
        fake.return_value.connect.side_effect = paramiko.ssh_exception.SSHException('banner')
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['ok'] is False
    assert fake.call_count == RETRY_ATTEMPTS


def test_classificacio_errors_transitoris():
    auth = paramiko.ssh_exception.AuthenticationException('nope')
    assert _is_transient(auth) is False
    assert _is_transient(paramiko.ssh_exception.SSHException('x')) is True
    assert _is_transient(socket.timeout()) is True
    assert _is_transient(EOFError()) is True


# --- Eliminacio -------------------------------------------------------------

def test_eliminar_fitxer_inexistent_es_considera_ok(config_sftp):
    with patch('paramiko.SSHClient') as fake:
        _sftp_de(fake).remove.side_effect = IOError(2, 'No such file')
        res = eliminar_sftp('60360', config_sftp)

    assert res['ok'] is True
    assert res['error'] is None


def test_eliminar_error_real_retorna_error(config_sftp):
    with patch('paramiko.SSHClient') as fake:
        _sftp_de(fake).remove.side_effect = IOError(13, 'Permission denied')
        res = eliminar_sftp('60360', config_sftp)

    assert res['ok'] is False
    assert 'Permission denied' in res['error']


def test_eliminar_config_incompleta_no_connecta(config_sftp):
    config_sftp['user'] = ''

    with patch('paramiko.SSHClient') as fake:
        res = eliminar_sftp('60360', config_sftp)

    assert res['ok'] is False
    fake.assert_not_called()


# --- Descarrega -------------------------------------------------------------

def test_descarregar_ok(config_sftp, tmp_path):
    with patch('paramiko.SSHClient') as fake:
        sftp = _sftp_de(fake)
        res = descarregar_sftp('60360.pdf', config_sftp, str(tmp_path / 'baixat.pdf'))

    assert res['ok'] is True
    assert res['not_found'] is False
    sftp.get.assert_called_once()


def test_descarregar_inexistent_marca_not_found(config_sftp, tmp_path):
    with patch('paramiko.SSHClient') as fake:
        _sftp_de(fake).get.side_effect = IOError(2, 'No such file')
        res = descarregar_sftp('99999.pdf', config_sftp, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is True


def test_descarregar_error_real_no_es_not_found(config_sftp, tmp_path):
    with patch('paramiko.SSHClient') as fake:
        _sftp_de(fake).get.side_effect = IOError(13, 'Permission denied')
        res = descarregar_sftp('60360.pdf', config_sftp, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is False


# --- Fuita de sessions SSH a _connectar_sftp --------------------------------
# Si connect() va be pero falla obrir el canal SFTP o entrar a la ruta, el
# cridador no rep mai el client i no el pot tancar. La sessio queda penjada al
# servidor i consumeix una de les connexions que permet; en una auditoria de
# centenars de fitxes s'esgoten i tot passa a fer timeout.

def test_tanca_si_falla_obrir_el_canal_sftp(config_sftp, tmp_path):
    with patch('paramiko.SSHClient') as fake:
        fake.return_value.open_sftp.side_effect = OSError('no channel')
        res = descarregar_sftp('60360.pdf', config_sftp, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    fake.return_value.close.assert_called_once()


def test_tanca_si_falla_el_chdir_a_la_ruta(config_sftp, tmp_path):
    """El cas mes probable en produccio: `path` mal configurat al desti."""
    with patch('paramiko.SSHClient') as fake:
        fake.return_value.open_sftp.return_value.chdir.side_effect = \
            IOError('No such file or directory')
        res = descarregar_sftp('60360.pdf', config_sftp, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    fake.return_value.close.assert_called_once()


def test_no_tanca_res_si_ni_tan_sols_connecta(config_sftp, tmp_path):
    """Si connect() peta no hi ha cap sessio oberta: close() seria inutil pero
    tampoc ha de petar."""
    with patch('paramiko.SSHClient') as fake:
        fake.return_value.connect.side_effect = OSError('timed out')
        res = descarregar_sftp('60360.pdf', config_sftp, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is False


def test_pujada_tanca_si_falla_el_chdir(config_sftp, pdf_temporal):
    with patch('paramiko.SSHClient') as fake:
        fake.return_value.open_sftp.return_value.chdir.side_effect = \
            IOError('No such file or directory')
        res = distribuir_sftp(pdf_temporal, '60360', config_sftp)

    assert res['ok'] is False
    assert fake.return_value.close.called
