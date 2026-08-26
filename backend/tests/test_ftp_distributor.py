"""Tests del distribuidor FTP/FTPS.

Cobreixen la logica delicada del modul:
  - validacio de configuracio incompleta (mai s'ha d'intentar connectar)
  - nom del fitxer remot: {art_codi}.pdf o el filename explicit
  - politica de reintents: els errors permanents (5xx) NO es reintenten,
    per no bloquejar el compte del FTP
  - el 550 en eliminar es considera OK (idempotent)
  - el 550 en descarregar es marca com a not_found, no com a error
"""

import ftplib
from unittest.mock import patch, MagicMock

import pytest

from app.services.ftp_distributor import (
    RETRY_ATTEMPTS,
    descarregar_ftp,
    distribuir_ftp,
    eliminar_ftp,
    _is_transient,
)


# --- Validacio previa: no s'ha de connectar mai -----------------------------

def test_pdf_inexistent_no_connecta(config_ftp):
    with patch('ftplib.FTP_TLS') as fake:
        res = distribuir_ftp('/ruta/que/no/existeix.pdf', '60360', config_ftp)

    assert res['ok'] is False
    assert 'PDF no trobat' in res['error']
    fake.assert_not_called()


@pytest.mark.parametrize('camp', ['host', 'user'])
def test_config_incompleta_no_connecta(config_ftp, pdf_temporal, camp):
    config_ftp[camp] = ''

    with patch('ftplib.FTP_TLS') as fake:
        res = distribuir_ftp(pdf_temporal, '60360', config_ftp)

    assert res['ok'] is False
    assert 'incompleta' in res['error']
    fake.assert_not_called()


# --- Pujada correcta --------------------------------------------------------

def test_puja_amb_tls_i_retorna_url(config_ftp, pdf_temporal):
    with patch('ftplib.FTP_TLS') as fake:
        ftp = fake.return_value
        res = distribuir_ftp(pdf_temporal, '60360', config_ftp)

    assert res['ok'] is True
    assert res['error'] is None
    # El nom al FTP es sempre {art_codi}.pdf
    assert ftp.storbinary.call_args[0][0] == 'STOR 60360.pdf'
    # TLS actiu: cal protegir el canal de dades
    ftp.prot_p.assert_called_once()
    ftp.cwd.assert_called_once_with('/fitxestecniques')
    ftp.quit.assert_called_once()
    assert res['url'].endswith('/60360.pdf')


def test_puja_sense_tls_usa_ftp_pla(config_ftp, pdf_temporal):
    config_ftp['tls'] = False

    with patch('ftplib.FTP') as fake_pla, patch('ftplib.FTP_TLS') as fake_tls:
        res = distribuir_ftp(pdf_temporal, '60360', config_ftp)

    assert res['ok'] is True
    fake_pla.assert_called_once()
    fake_tls.assert_not_called()


def test_filename_explicit_te_prioritat_sobre_art_codi(config_ftp, pdf_temporal):
    with patch('ftplib.FTP_TLS') as fake:
        ftp = fake.return_value
        distribuir_ftp(pdf_temporal, '60360', config_ftp, filename='60360_ES.pdf')

    assert ftp.storbinary.call_args[0][0] == 'STOR 60360_ES.pdf'


def test_path_arrel_no_fa_cwd(config_ftp, pdf_temporal):
    config_ftp['path'] = '/'

    with patch('ftplib.FTP_TLS') as fake:
        ftp = fake.return_value
        distribuir_ftp(pdf_temporal, '60360', config_ftp)

    ftp.cwd.assert_not_called()


# --- Politica de reintents --------------------------------------------------

def test_error_permanent_no_es_reintenta(config_ftp, pdf_temporal):
    """Credencials incorrectes (5xx): un sol intent, per no bloquejar el compte."""
    with patch('ftplib.FTP_TLS') as fake:
        fake.return_value.login.side_effect = ftplib.error_perm('530 Login incorrect')
        res = distribuir_ftp(pdf_temporal, '60360', config_ftp)

    assert res['ok'] is False
    assert '530' in res['error']
    assert fake.call_count == 1


def test_error_transitori_es_reintenta_i_acaba_ok(config_ftp, pdf_temporal):
    with patch('ftplib.FTP_TLS') as fake:
        fake.return_value.storbinary.side_effect = [
            ftplib.error_temp('421 Service not available'),
            None,
        ]
        res = distribuir_ftp(pdf_temporal, '60360', config_ftp)

    assert res['ok'] is True
    assert fake.call_count == 2


def test_error_transitori_esgota_els_reintents(config_ftp, pdf_temporal):
    with patch('ftplib.FTP_TLS') as fake:
        fake.return_value.storbinary.side_effect = TimeoutError('timeout')
        res = distribuir_ftp(pdf_temporal, '60360', config_ftp)

    assert res['ok'] is False
    assert fake.call_count == RETRY_ATTEMPTS


def test_classificacio_errors_transitoris():
    assert _is_transient(ftplib.error_temp('421')) is True
    assert _is_transient(TimeoutError()) is True
    assert _is_transient(ConnectionResetError()) is True
    assert _is_transient(ftplib.error_perm('530')) is False


# --- Eliminacio -------------------------------------------------------------

def test_eliminar_fitxer_inexistent_es_considera_ok(config_ftp):
    """550 = el fitxer ja no hi es. L'objectiu (que no hi sigui) s'ha complert."""
    with patch('ftplib.FTP_TLS') as fake:
        fake.return_value.delete.side_effect = ftplib.error_perm('550 File not found')
        res = eliminar_ftp('60360', config_ftp)

    assert res['ok'] is True
    assert res['error'] is None


def test_eliminar_error_real_retorna_error(config_ftp):
    with patch('ftplib.FTP_TLS') as fake:
        fake.return_value.delete.side_effect = ftplib.error_perm('553 Permission denied')
        res = eliminar_ftp('60360', config_ftp)

    assert res['ok'] is False
    assert '553' in res['error']


def test_eliminar_config_incompleta_no_connecta(config_ftp):
    config_ftp['host'] = ''

    with patch('ftplib.FTP_TLS') as fake:
        res = eliminar_ftp('60360', config_ftp)

    assert res['ok'] is False
    fake.assert_not_called()


# --- Descarrega -------------------------------------------------------------

def test_descarregar_ok(config_ftp, tmp_path):
    desti = tmp_path / 'baixat.pdf'

    with patch('ftplib.FTP_TLS') as fake:
        fake.return_value.retrbinary.side_effect = (
            lambda _cmd, callback: callback(b'%PDF-1.4 baixat')
        )
        res = descarregar_ftp('60360.pdf', config_ftp, str(desti))

    assert res['ok'] is True
    assert res['not_found'] is False
    assert desti.read_bytes() == b'%PDF-1.4 baixat'


def test_descarregar_inexistent_marca_not_found(config_ftp, tmp_path):
    """Distingir "no existeix" d'"ha fallat" es el que permet a la sincronitzacio
    amb el FTP saber si cal pujar el fitxer o si hi ha un problema real."""
    with patch('ftplib.FTP_TLS') as fake:
        fake.return_value.retrbinary.side_effect = ftplib.error_perm('550 Not found')
        res = descarregar_ftp('99999.pdf', config_ftp, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is True


def test_descarregar_error_permis_no_es_not_found(config_ftp, tmp_path):
    with patch('ftplib.FTP_TLS') as fake:
        fake.return_value.retrbinary.side_effect = ftplib.error_perm('553 Denied')
        res = descarregar_ftp('60360.pdf', config_ftp, str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is False
