"""Regressio: quina data de revisio s'imprimeix al PDF que es distribueix.

La distribucio imprimia `versio.created_at` (quan es va crear la fila a la BD,
per exemple durant una carrega massiva) mentre que la descarrega des de l'app
imprimia `versio.data_revisio`. Resultat: el PDF que arribava al FTP o a
SharePoint mostrava una data diferent de la que es veu a la fitxa, i la
comprovacio de destins ho detectava com a 'desfasat' massivament.

Les dues vies han de fer servir el mateix criteri.
"""

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.routes.distribucions import _assegurar_pdf


@pytest.fixture
def fitxa():
    return SimpleNamespace(id=1, art_codi='60360', nom_producte='Farina morena')


def _versio(data_revisio=None, created_at=None, fitxer_pdf=None):
    return SimpleNamespace(
        num_versio=3,
        contingut={},
        data_revisio=data_revisio,
        data_comprovacio=None,
        created_at=created_at,
        fitxer_pdf=fitxer_pdf,
    )


def _dt(dia, mes, any_):
    return datetime(any_, mes, dia, tzinfo=timezone.utc)


def test_imprimeix_data_revisio_no_created_at(fitxa, tmp_path):
    """El cas del bug: la fitxa es del 12/12/2024 pero la fila es va crear el
    27/08/2026; el PDF distribuit deia 27/08/2026."""
    versio = _versio(data_revisio=_dt(12, 12, 2024), created_at=_dt(27, 8, 2026))

    with patch('app.services.pdf_generator.generar_pdf',
               return_value=b'%PDF') as generar, \
         patch('os.makedirs'), patch('builtins.open', create=True):
        _assegurar_pdf(fitxa, versio)

    _contingut, _num, data_rev, _data_comp = generar.call_args[0]
    assert data_rev == '12/12/2024'


def test_created_at_nomes_com_a_fallback(fitxa):
    """Si la versio no te data_revisio, created_at segueix sent millor que res."""
    versio = _versio(data_revisio=None, created_at=_dt(27, 8, 2026))

    with patch('app.services.pdf_generator.generar_pdf',
               return_value=b'%PDF') as generar, \
         patch('os.makedirs'), patch('builtins.open', create=True):
        _assegurar_pdf(fitxa, versio)

    assert generar.call_args[0][2] == '27/08/2026'


def test_data_comprovacio_cau_a_la_de_revisio(fitxa):
    versio = _versio(data_revisio=_dt(12, 12, 2024), created_at=_dt(27, 8, 2026))

    with patch('app.services.pdf_generator.generar_pdf',
               return_value=b'%PDF') as generar, \
         patch('os.makedirs'), patch('builtins.open', create=True):
        _assegurar_pdf(fitxa, versio)

    assert generar.call_args[0][3] == '12/12/2024'


def test_no_regenera_si_el_pdf_ja_existeix(fitxa, tmp_path):
    existent = tmp_path / '60360.pdf'
    existent.write_bytes(b'%PDF ja fet')
    versio = _versio(data_revisio=_dt(12, 12, 2024), fitxer_pdf=str(existent))

    with patch('app.services.pdf_generator.generar_pdf') as generar:
        ruta = _assegurar_pdf(fitxa, versio)

    generar.assert_not_called()
    assert ruta == str(existent)


def test_completa_el_contingut_amb_codi_i_denominacio(fitxa):
    versio = _versio(data_revisio=_dt(12, 12, 2024))

    with patch('app.services.pdf_generator.generar_pdf',
               return_value=b'%PDF') as generar, \
         patch('os.makedirs'), patch('builtins.open', create=True):
        _assegurar_pdf(fitxa, versio)

    contingut = generar.call_args[0][0]
    assert contingut['codi_referencia'] == '60360'
    assert contingut['denominacio_comercial'] == 'Farina morena'
