"""Lectura de la capcalera del PDF: revisio i dates.

Regressio d'un fals 'desfasat' massiu: a les fitxes en castella la capcalera
imprimeix "Fecha Rev.: 07/02/2025", que tambe conte "rev.:". El patro que
buscava la revisio hi entrava i capturava el DIA de la data, de manera que la
comprovacio de destins deia que el PDF tenia la revisio 07 quan la fitxa en
tenia la 2. A les bilingues surt "Fecha/Data Rev:" (sense punt) i per aixo
nomes fallaven algunes.
"""

import pytest

from app.services.pdf_parser import _parse_header


class _PaginaFalsa:
    """Prou per a _parse_header, que nomes crida extract_tables()."""

    def __init__(self, cel·les):
        self._taula = [[c] for c in cel·les]

    def extract_tables(self):
        return [self._taula]


def _capcalera(*cel·les):
    return _parse_header([_PaginaFalsa(list(cel·les))])


def test_revisio_simple():
    assert _capcalera('Rev.: 2')['rev'] == '2'


def test_revisio_de_dues_xifres():
    assert _capcalera('Rev.: 12')['rev'] == '12'


def test_revisio_zero():
    assert _capcalera('Rev.: 0')['rev'] == '0'


def test_data_de_revisio_no_es_pren_per_revisio():
    """El cas del bug: cel·la en castella, sense cap 'Rev.: N' de veritat."""
    info = _capcalera('Fecha Rev.: 07/02/2025')

    assert info['rev'] == ''
    assert info['data_revisio'] == '07/02/2025'


def test_revisio_i_data_a_la_mateixa_cella():
    """Si pdfplumber fusiona la capcalera, s'ha d'agafar la revisio bona."""
    info = _capcalera('Rev.: 3 Fecha Rev.: 13/12/2024')

    assert info['rev'] == '3'
    assert info['data_revisio'] == '13/12/2024'


def test_capcalera_bilingue():
    info = _capcalera('Rev.: 5', 'Fecha/Data Rev: 10/06/2024',
                      'Fecha/Data Comprov.: 11/06/2024')

    assert info['rev'] == '5'
    assert info['data_revisio'] == '10/06/2024'
    assert info['data_comprovacio'] == '11/06/2024'


def test_capcalera_castella_completa():
    info = _capcalera('Rev.: 2', 'Fecha Rev.: 07/02/2025',
                      'Fecha Comprov.: 08/02/2025')

    assert info['rev'] == '2'
    assert info['data_revisio'] == '07/02/2025'
    assert info['data_comprovacio'] == '08/02/2025'
