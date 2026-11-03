from app.services.etiquetes_idioma import ETIQUETES, IDIOMES, titol_idioma


BIL = 'Ingredientes / Ingredients'


def test_bilingue_no_toca_res():
    assert titol_idioma(BIL, 'bilingue') == BIL
    assert titol_idioma(BIL, None) == BIL


def test_castella_i_catala():
    assert titol_idioma('Uso previsto / Ús previst', 'es') == 'Uso previsto'
    assert titol_idioma('Uso previsto / Ús previst', 'ca') == 'Ús previst'


def test_capcalera_te_text_propi():
    assert titol_idioma('Fecha/Data Rev', 'ca') == 'Data Rev.'
    assert titol_idioma('Fecha/Data Rev', 'es') == 'Fecha Rev.'
    assert titol_idioma('Fecha/Data Rev', 'bilingue') == 'Fecha/Data Rev'
    assert titol_idioma('FICHA TÉCNICA / FITXA TÈCNICA', 'ca') == 'FITXA TÈCNICA'


def test_angles_i_portugues_del_diccionari():
    assert titol_idioma(BIL, 'en') == 'Ingredients'
    assert titol_idioma('Valor', 'en') == 'Value'
    assert titol_idioma('Micotoxinas / Micotoxines', 'pt') == 'Micotoxinas'


def test_titol_desconegut_queda_igual():
    assert titol_idioma('Desconegut / Desconocido', 'en') == 'Desconegut / Desconocido'
    assert titol_idioma('Valor', 'ca') == 'Valor'


def test_tots_els_titols_bilingues_tenen_en_i_pt():
    for text, trad in ETIQUETES.items():
        if ' / ' in text:
            assert trad.get('en') and trad.get('pt'), text
    assert IDIOMES == ('ca', 'es', 'en', 'pt')


def test_tots_els_titols_de_la_plantilla_son_al_diccionari():
    import os
    import re
    path = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates',
                        'fitxa_tecnica.html')
    with open(path, encoding='utf-8') as f:
        html = f.read()
    titols = re.findall(r"""\{\{ (['"])(.*?)\1\|bil \}\}""", html)
    assert titols
    for _, text in titols:
        assert text in ETIQUETES, text
