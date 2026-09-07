"""Tests de descarregar_sharepoint (Microsoft Graph).

Cobreixen el que te logica propia: el 404 com a not_found (no com a error), el
throttling 429 amb Retry-After, i el percent-encoding del path (un nom amb
espais ha d'arribar a Graph com a %20).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.sharepoint_distributor import descarregar_sharepoint


@pytest.fixture(autouse=True)
def graph_resolt():
    """Token i site/drive ja resolts: aixi els tests nomes miren el GET final."""
    with patch('app.services.sharepoint_distributor._get_token',
               return_value=('token-fals', None)), \
         patch('app.services.sharepoint_distributor._resolve_site_drive',
               return_value=({'site_id': 'site-1', 'drive_id': 'drive-1'}, None)):
        yield


def _resposta(status, contingut=b'', headers=None):
    r = MagicMock()
    r.status_code = status
    r.headers = headers or {}
    r.text = ''
    r.iter_content = MagicMock(return_value=[contingut] if contingut else [])
    return r


def test_descarrega_correcta(config_sharepoint, tmp_path):
    desti = tmp_path / 'baixat.pdf'
    with patch('requests.get', return_value=_resposta(200, b'%PDF-1.4 ok')):
        res = descarregar_sharepoint('60360.pdf', config_sharepoint, str(desti))

    assert res['ok'] is True
    assert res['not_found'] is False
    assert desti.read_bytes() == b'%PDF-1.4 ok'


def test_404_es_not_found(config_sharepoint, tmp_path):
    with patch('requests.get', return_value=_resposta(404)):
        res = descarregar_sharepoint('60360.pdf', config_sharepoint,
                                     str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is True


def test_429_reintenta_un_cop_i_despres_va_be(config_sharepoint, tmp_path):
    desti = tmp_path / 'baixat.pdf'
    respostes = [_resposta(429, headers={'Retry-After': '1'}),
                 _resposta(200, b'%PDF ok')]
    with patch('requests.get', side_effect=respostes) as get:
        res = descarregar_sharepoint('60360.pdf', config_sharepoint, str(desti))

    assert get.call_count == 2
    assert res['ok'] is True


def test_429_persistent_acaba_en_error_no_en_not_found(config_sharepoint, tmp_path):
    with patch('requests.get',
               side_effect=[_resposta(429, headers={'Retry-After': '1'}),
                            _resposta(429, headers={'Retry-After': '1'})]):
        res = descarregar_sharepoint('60360.pdf', config_sharepoint,
                                     str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is False


def test_500_es_error_no_not_found(config_sharepoint, tmp_path):
    with patch('requests.get', return_value=_resposta(500)):
        res = descarregar_sharepoint('60360.pdf', config_sharepoint,
                                     str(tmp_path / 'x.pdf'))

    assert res['ok'] is False
    assert res['not_found'] is False


def test_nom_amb_espais_va_percent_encoded(config_sharepoint, tmp_path):
    with patch('requests.get', return_value=_resposta(200, b'%PDF')) as get:
        descarregar_sharepoint('60360 Farina morena.pdf', config_sharepoint,
                               str(tmp_path / 'x.pdf'))

    url = get.call_args[0][0]
    assert '60360%20Farina%20morena.pdf' in url
    assert 'FitxesTecniques' in url


def test_config_incompleta_no_crida_graph(config_sharepoint, tmp_path):
    config_sharepoint['site_url'] = ''

    with patch('requests.get') as get:
        res = descarregar_sharepoint('60360.pdf', config_sharepoint,
                                     str(tmp_path / 'x.pdf'))

    get.assert_not_called()
    assert res['ok'] is False
    assert res['not_found'] is False
