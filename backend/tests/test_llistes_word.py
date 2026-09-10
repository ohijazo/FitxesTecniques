"""Llistes amb vinyeta importades del Word.

Les fitxes porten llistes (p.ex. "Otra legislacion aplicable") fetes amb la
numeracio del Word. El guio i el fet de ser una llista no viuen al paragraf sino
a word/numbering.xml, aixi que el parser ha de mirar w:numPr; si no, els punts
arriben aplanats en un unic bloc de text seguit.
"""

import pytest
from docx.oxml import parse_xml
from docx.oxml.ns import nsmap

from app.services.word_parser import _list_kind
from app.services.pdf_generator import _split_paragraphs


NS = ' '.join(f'xmlns:{k}="{v}"' for k, v in nsmap.items())


def _paragraf(pPr=''):
    return parse_xml(f'<w:p {NS}>{pPr}<w:r><w:t>text</w:t></w:r></w:p>')


def _num_pr(num_id, ilvl='0'):
    return (f'<w:pPr><w:numPr><w:ilvl w:val="{ilvl}"/>'
            f'<w:numId w:val="{num_id}"/></w:numPr></w:pPr>')


# --- deteccio de l'element de llista -----------------------------------------

def test_paragraf_normal_no_es_llista():
    assert _list_kind(_paragraf(), {}) is None


def test_paragraf_amb_pPr_pero_sense_numeracio():
    p = _paragraf('<w:pPr><w:jc w:val="both"/></w:pPr>')
    assert _list_kind(p, {}) is None


def test_vinyeta():
    assert _list_kind(_paragraf(_num_pr('10')), {'10': 'bullet'}) == 'ul'


def test_llista_numerada():
    assert _list_kind(_paragraf(_num_pr('3')), {'3': 'decimal'}) == 'ol'


def test_numeracio_desconeguda_es_tracta_com_a_vinyeta():
    # Si el numId no es al mapa no podem saber el format: la vinyeta es el cas
    # habitual a les fitxes i es el valor segur.
    assert _list_kind(_paragraf(_num_pr('99')), {}) == 'ul'


def test_numeracio_anullada():
    # numId 0 vol dir que el Word ha tret la numeracio d'aquell paragraf
    assert _list_kind(_paragraf(_num_pr('0')), {'0': 'bullet'}) is None


# --- els blocs de llista no s'han d'aplanar ----------------------------------

def test_bloc_de_llista_arriba_sencer():
    text = '<ul><li>Un</li><li>Dos</li></ul>'
    assert _split_paragraphs(text) == [text]


def test_llista_barrejada_amb_text():
    text = 'Introduccio\n<ul><li>Un</li><li>Dos</li></ul>\nFinal'
    assert _split_paragraphs(text) == [
        'Introduccio', '<ul><li>Un</li><li>Dos</li></ul>', 'Final']


def test_llista_de_l_editor_amb_p_interns():
    # TipTap desa <li><p>...</p></li>: el regex de <p> no se l'ha d'endur
    text = '<ul><li><p>Un</p></li><li><p>Dos</p></li></ul>'
    assert _split_paragraphs(text) == [text]


def test_llista_niuada():
    text = '<ul><li>Un<ul><li>Un.u</li></ul></li><li>Dos</li></ul>'
    assert _split_paragraphs(text) == [text]


def test_llista_sense_tancar_no_trenca_res():
    # Contingut malmes: val mes tractar-ho com a text que no pas perdre'l
    blocs = _split_paragraphs('<ul><li>Un</li>')
    assert blocs and 'Un' in ''.join(blocs)


@pytest.mark.parametrize('text,esperat', [
    ('Una linia', ['Una linia']),
    ('Una\nAltra', ['Una', 'Altra']),
    ('<p>Una</p><p>Altra</p>', ['Una', 'Altra']),
    ('Una<br>Altra', ['Una', 'Altra']),
    ('', []),
    (None, []),
])
def test_text_sense_llistes_es_comporta_igual_que_abans(text, esperat):
    assert _split_paragraphs(text) == esperat
