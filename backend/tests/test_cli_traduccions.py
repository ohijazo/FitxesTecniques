"""Validació dels registres del fitxer d'importació de traduccions."""
from app.cli_traduccions import _registre_valid

BO = {'art_codi': '30150', 'versio_id': 2, 'num_versio': 6, 'idioma': 'en',
      'contingut': {'ingredients': 'WHEAT flour'}}


def test_registre_correcte():
    assert _registre_valid(BO) is None


def test_registres_incorrectes():
    assert 'falta versio_id' == _registre_valid({k: v for k, v in BO.items() if k != 'versio_id'})
    assert 'idioma no vàlid' in _registre_valid({**BO, 'idioma': 'fr'})
    assert _registre_valid({**BO, 'contingut': {}}) == 'contingut buit'
    assert _registre_valid('text') == 'no és un objecte'
