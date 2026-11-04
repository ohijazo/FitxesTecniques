"""Correcció dels superíndexs perduts («< 106 ufc/g» -> «< 10⁶ ufc/g»)."""
import pytest

from app.cli_superindexs import corregir_taules, corregir_valor


@pytest.mark.parametrize('abans, despres', [
    ('< 106 ufc/g', '< 10⁶ ufc/g'),
    ('< 104 ufc/g', '< 10⁴ ufc/g'),
    ('< 102 ufc/g', '< 10² ufc/g'),
    ('< 1x105 ufc/g', '< 1x10⁵ ufc/g'),
    ('< 1x101 ufc/g', '< 1x10¹ ufc/g'),
    ('< 106 cfu/g', '< 10⁶ cfu/g'),
    ('< 106/g', '< 10⁶/g'),
])
def test_corregeix(abans, despres):
    assert corregir_valor(abans) == despres


@pytest.mark.parametrize('text', [
    '< 100 ufc/g', '< 10 ufc/g', '< 1x10⁶ ufc/g', 'No detectado / 25g',
    '≤ 15 %', '106 kcal', '1067 kJ', '10,6 g', 'Màx. 106', None,
])
def test_no_toca(text):
    assert corregir_valor(text) == text


def test_taules_i_registre_de_canvis():
    contingut = {'microbiologiques': [{'parametre': 'Aerobios', 'valor': '< 106 ufc/g'},
                                      {'parametre': 'Salmonella', 'valor': 'No detectado / 25g'}],
                 'ingredients': '106 ufc'}
    nou, canvis = corregir_taules(contingut, ('microbiologiques',))
    assert nou['microbiologiques'][0]['valor'] == '< 10⁶ ufc/g'
    assert nou['ingredients'] == '106 ufc'                       # només taules
    assert canvis == [{'camp': 'microbiologiques', 'fila': 0, 'abans': '< 106 ufc/g', 'despres': '< 10⁶ ufc/g'}]
    assert contingut['microbiologiques'][0]['valor'] == '< 106 ufc/g'   # l'original no es modifica
