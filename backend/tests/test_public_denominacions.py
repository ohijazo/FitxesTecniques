"""Endpoint public de denominacions: el consumeix l'aplicacio del DeCA.

No toca la base de dades: la consulta es substitueix per dades de prova. El
que es vol protegir es el contracte —que no s'escapi res que el DeCA no
necessiti— i que la clau no es pugui saltar.
"""
import pytest

from app import create_app
from app.routes import public as modul


def _fila(art_codi, denominacio, num_versio=1, data_revisio=None):
    """Una fila tal com la torna la consulta amb with_entities()."""
    return (art_codi, {'denominacio_juridica': denominacio}, num_versio, data_revisio)


@pytest.fixture
def client(monkeypatch):
    """Aplicacio amb la clau posada i la consulta a la base de dades simulada."""
    monkeypatch.setenv('API_DENOMINACIONS_KEY', 'clau-de-prova')
    monkeypatch.setenv('ENABLE_JOB_WORKER', '0')
    app = create_app()
    app.config['TESTING'] = True
    app.config['API_DENOMINACIONS_KEY'] = 'clau-de-prova'

    files = [
        _fila('30450', 'Harina integral de trigo/ Farina integral de blat.', 3),
        _fila('30150', '<p>Harina de trigo/ Farina de blat.</p>', 2),
        _fila('31000', ''),                      # sense denominacio: no ha de sortir
    ]

    monkeypatch.setattr(modul, '_consultar', lambda: files)
    with app.test_client() as c:
        yield c


def test_torna_les_denominacions_amb_la_clau_correcta(client):
    r = client.get('/api/public/denominacions', headers={'X-API-Key': 'clau-de-prova'})

    assert r.status_code == 200
    dades = r.get_json()
    assert dades['total'] == 2                    # la buida no hi es
    codis = [d['art_codi'] for d in dades['denominacions']]
    assert codis == ['30150', '30450']            # ordenades per codi


def test_neteja_les_etiquetes_de_l_editor(client):
    r = client.get('/api/public/denominacions', headers={'X-API-Key': 'clau-de-prova'})

    primera = r.get_json()['denominacions'][0]
    assert primera['denominacio_juridica'] == 'Harina de trigo/ Farina de blat.'
    assert '<p>' not in primera['denominacio_juridica']


def test_nomes_surt_el_que_el_deca_necessita(client):
    """Cap dada comercial: ni composicio, ni vida util, ni valors reologics."""
    r = client.get('/api/public/denominacions', headers={'X-API-Key': 'clau-de-prova'})

    camps = set(r.get_json()['denominacions'][0])
    assert camps == {'art_codi', 'denominacio_juridica', 'revisio', 'data_revisio'}


@pytest.mark.parametrize('capcaleres', [
    {},                                  # sense clau
    {'X-API-Key': ''},                   # clau buida
    {'X-API-Key': 'clau-de-prov'},       # quasi be
    {'X-API-Key': 'CLAU-DE-PROVA'},      # majuscules
])
def test_sense_la_clau_bona_no_es_veu_res(client, capcaleres):
    r = client.get('/api/public/denominacions', headers=capcaleres)

    assert r.status_code == 401
    assert 'denominacions' not in r.get_json()


def test_sense_clau_configurada_l_endpoint_esta_tancat(monkeypatch):
    """Ve desactivat de serie: no es pot obrir sense voler."""
    monkeypatch.setenv('ENABLE_JOB_WORKER', '0')
    app = create_app()
    app.config['TESTING'] = True
    app.config['API_DENOMINACIONS_KEY'] = ''

    with app.test_client() as c:
        r = c.get('/api/public/denominacions', headers={'X-API-Key': 'el-que-sigui'})

    assert r.status_code == 503


@pytest.mark.parametrize('metode', ['post', 'put', 'delete', 'patch'])
def test_es_nomes_lectura(client, metode):
    r = getattr(client, metode)('/api/public/denominacions',
                                headers={'X-API-Key': 'clau-de-prova'})
    assert r.status_code == 405
