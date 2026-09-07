"""Tests de _filename_de_referencia.

Aquesta funcio dedueix amb quin nom es va pujar realment un PDF a partir de la
URL o el path que Distribucio.missatge_error guarda quan l'estat es 'ok'. La
fan servir tant la retirada com la comprovacio, i un error aqui provoca que es
busqui (o s'esborri) un fitxer que no existeix.
"""

import pytest

from app.routes.distribucions import _filename_de_referencia


@pytest.mark.parametrize('ref, esperat', [
    # FTP: URL publica
    ('https://farineracoromina.com/fitxestecniques/60360.pdf', '60360.pdf'),
    # SharePoint: webUrl de Graph, amb els espais percent-encoded
    ('https://agrienergia.sharepoint.com/sites/qualitat/Documents/'
     '60360%20Farina%20morena.pdf', '60360 Farina morena.pdf'),
    # Carpeta de xarxa: path UNC de Windows
    (r'\\tomatera\Farinera\ProvaFitxesTecniques\60360.pdf', '60360.pdf'),
    # URL amb query string
    ('https://exemple.local/fitxes/60360.pdf?v=3', '60360.pdf'),
    # Nom amb accents ja desxifrats
    ('https://exemple.local/fitxes/Farina%20d%27espelta.pdf', "Farina d'espelta.pdf"),
])
def test_extreu_el_nom(ref, esperat):
    assert _filename_de_referencia(ref) == esperat


@pytest.mark.parametrize('ref', [
    None,
    '',
    # Motiu de retirada: text lliure, no es cap fitxer
    'Producte descatalogat pel client',
    # Missatge d'error
    '550 Permission denied',
    # Un fitxer que no es PDF
    'https://exemple.local/fitxes/60360.docx',
])
def test_referencies_que_no_son_pdf(ref):
    assert _filename_de_referencia(ref) is None
