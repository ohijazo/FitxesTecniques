"""Tests de services/traduccio.py amb textos reals de fitxes (30150, 01921)."""
from app.services.traduccio import (
    camps_canviats, combinar, separar_bilingue, separar_text, traduir_ia,
)


def test_separar_una_parella_tallada_en_linies():
    text = ('Producto que se obtiene de la molienda del grano de trigo entero, maduro y sano /\n'
            'Producte que s’obté de la molturació del gra de blat sencer, madur i sa.')
    assert separar_text(text, 'es') == (
        'Producto que se obtiene de la molienda del grano de trigo entero, maduro y sano', False)
    assert separar_text(text, 'ca') == (
        'Producte que s’obté de la molturació del gra de blat sencer, madur i sa.', False)


def test_separar_barra_sense_espai_davant():
    assert separar_text('Harina de trigo/ Farina de blat.', 'ca') == ('Farina de blat.', False)


def test_separar_diverses_parelles_i_data_final_comuna():
    text = ('Harina de TRIGO / Farina de BLAT.\n'
            'Según Directiva 1999/2/CE / Segons Directiva 1999/2/CE.\n10/06/2024')
    ca, dubtos = separar_text(text, 'ca')
    assert ca == 'Farina de BLAT.\nSegons Directiva 1999/2/CE.\n10/06/2024'
    assert not dubtos
    es, _ = separar_text(text, 'es')
    assert es == 'Harina de TRIGO\nSegún Directiva 1999/2/CE\n10/06/2024'


def test_referencies_amb_barra_no_es_tallen():
    text = ('Conforme a los Reglamentos (CE) Núm. 1829/2003 y 1830/2003 / Conforme els '
            'Reglaments (CE) Núm.\n1829/2003 i 1830/2003.')
    ca, _ = separar_text(text, 'ca')
    assert ca == 'Conforme els Reglaments (CE) Núm. 1829/2003 i 1830/2003.'


def test_continuacio_numerica_no_es_data_comuna():
    text = ('Contiene GLUTEN. No contiene trazas de ningún otro alérgeno del Reglamento UE\n'
            'Nº 1169/2011. / Conté GLUTEN. No conté traces de cap altre al·lergen del Reglament UE Nº\n'
            '1169/2011.')
    es, _ = separar_text(text, 'es')
    ca, _ = separar_text(text, 'ca')
    assert es.endswith('Reglamento UE Nº 1169/2011.')
    assert ca.endswith('Reglament UE Nº 1169/2011.')
    assert '\n' not in ca


def test_sense_separador_es_dubtos():
    assert separar_text('RD 677/2016, de 16 de diciembre', 'ca') == ('RD 677/2016, de 16 de diciembre', True)


def test_data_enmig_del_text_es_dubtosa():
    text = ('Almacenes a Tª ambiente / Magatzems a Tª\n10/06/2024\nambient.')
    _, dubtos = separar_text(text, 'ca')
    assert dubtos


def test_llistes_html_no_es_toquen():
    text = '<ul><li>Sac / Sac</li></ul>'
    assert separar_text(text, 'ca') == (text, True)


def test_separar_bilingue_taules():
    contingut = {
        'microbiologiques': [
            {'parametre': 'Aerobios mesófilos / Aerobis mesòfils', 'valor': '< 106 ufc/g'},
            {'parametre': 'E. coli', 'valor': '< 102 ufc/g'},
            {'parametre': 'Salmonella', 'valor': 'No detectado / 25g\nNo detectat / 25g'},
        ],
        'codi_referencia': '30150',
    }
    proposta, dubtosos = separar_bilingue(contingut, 'ca')
    assert proposta['microbiologiques'] == [
        {'parametre': 'Aerobis mesòfils'},
        {'parametre': 'E. coli'},
        {'parametre': 'Salmonella', 'valor': 'No detectat / 25g'},
    ]
    assert 'codi_referencia' not in proposta
    assert dubtosos == ['microbiologiques']


def test_combinar_no_toca_la_versio_i_aplica_la_traduccio():
    versio = {
        'codi_referencia': '30150',
        'ingredients': 'Harina / Farina',
        'microbiologiques': [{'parametre': 'Hongos / Fongs', 'valor': '< 104'},
                             {'parametre': 'Salmonella', 'valor': 'No detectado / 25g'}],
    }
    trad = {'ingredients': 'Farina',
            'microbiologiques': [{'parametre': 'Fongs'}, {'parametre': 'Salmonella', 'valor': 'No detectat / 25g'}]}
    res = combinar(versio, trad, 'ca')
    assert res['ingredients'] == 'Farina'
    assert res['codi_referencia'] == '30150'
    assert res['microbiologiques'] == [{'parametre': 'Fongs', 'valor': '< 104'},
                                       {'parametre': 'Salmonella', 'valor': 'No detectat / 25g'}]
    assert res['_idioma'] == 'ca'
    # La versió original no s'ha modificat (les versions són immutables)
    assert versio['ingredients'] == 'Harina / Farina'
    assert versio['microbiologiques'][0]['parametre'] == 'Hongos / Fongs'


def test_camps_canviats():
    abans = {'ingredients': 'A', 'origen': 'B', 'micotoxines': [{'parametre': 'DON', 'valor': '750'}]}
    ara = {'ingredients': 'A', 'origen': 'C', 'micotoxines': [{'parametre': 'DON', 'valor': '1000'}]}
    assert camps_canviats(abans, ara) == ['origen', 'micotoxines']


def test_ia_sense_clau_retorna_error(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    proposta, error = traduir_ia({'ingredients': 'Harina'}, 'en')
    assert proposta is None
    assert 'ANTHROPIC_API_KEY' in error


def test_ia_nomes_en_i_pt():
    proposta, error = traduir_ia({'ingredients': 'Harina'}, 'ca')
    assert proposta is None and error


def test_ia_munta_la_proposta_amb_la_resposta(monkeypatch):
    """Client simulat: comprova la petició i com es reconstrueix la proposta."""
    import json
    from types import SimpleNamespace
    import anthropic

    rebut = {}

    class FakeMessages:
        def create(self, **kwargs):
            rebut.update(kwargs)
            items = json.loads(kwargs['messages'][0]['content'])
            trad = {'ingredients': 'Wheat FLOUR', 'microbiologiques.0.parametre': 'Moulds and yeasts',
                    'microbiologiques.1.valor': 'Not detected / 25g'}
            out = {'items': [{'id': it['id'], 'text': trad.get(it['id'], it['text'])} for it in items]}
            return SimpleNamespace(stop_reason='end_turn',
                                   content=[SimpleNamespace(type='text', text=json.dumps(out))])

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test')
    monkeypatch.delenv('TRADUCCIO_MODEL', raising=False)
    monkeypatch.setattr(anthropic, 'Anthropic', FakeClient)

    es = {'ingredients': 'Harina de TRIGO',
          'microbiologiques': [{'parametre': 'Hongos y levaduras'}, {'parametre': 'Salmonella'}]}
    versio = {'microbiologiques': [{'parametre': 'x', 'valor': '≤ 15 %'},
                                   {'parametre': 'y', 'valor': 'No detectado / 25g'}]}
    proposta, error = traduir_ia(es, 'en', valors_originals=versio)

    assert error is None
    assert rebut['model'] == 'claude-opus-5-5'
    assert rebut['output_config']['format']['type'] == 'json_schema'
    ids = [it['id'] for it in json.loads(rebut['messages'][0]['content'])]
    # El valor numèric no s'envia; el que té text sí
    assert 'microbiologiques.0.valor' not in ids
    assert 'microbiologiques.1.valor' in ids
    assert proposta == {
        'ingredients': 'Wheat FLOUR',
        'microbiologiques': [{'parametre': 'Moulds and yeasts'},
                             {'parametre': 'Salmonella', 'valor': 'Not detected / 25g'}],
    }
