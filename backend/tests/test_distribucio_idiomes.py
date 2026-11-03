"""Distribució dels PDFs per idioma (fase 2).

El risc principal és que una consulta de "l'última distribució d'un destí"
barregi el PDF principal amb els d'idioma: en retirar el principal s'esborraria
30150_EN.pdf, o la comprovació miraria el fitxer equivocat.
"""
import inspect
from types import SimpleNamespace

import pytest

from app.routes import distribucions as d
from app.services.pdf_parser import _parse_header


FITXA = SimpleNamespace(art_codi='30150', nom_producte='Nº1')
VERSIO = SimpleNamespace(num_versio=3)


@pytest.mark.parametrize('patro, idioma, esperat', [
    ('{art_codi}.pdf', None, '30150.pdf'),
    ('{art_codi}.pdf', 'en', '30150_EN.pdf'),
    ('{art_codi}.pdf', 'ca', '30150_CA.pdf'),
    ('{art_codi} {nom_producte}.pdf', 'pt', '30150 Nº1_PT.pdf'),
    ('FT_{art_codi}_v{versio}.pdf', 'es', 'FT_30150_v3_ES.pdf'),
    (None, 'en', '30150_EN.pdf'),
    ('', None, '30150.pdf'),
])
def test_nom_fitxer_amb_idioma(patro, idioma, esperat):
    assert d._generar_nom_fitxer(patro, FITXA, VERSIO, idioma) == esperat


def test_nom_sense_extensio():
    assert d._nom_amb_idioma('30150', 'en') == '30150_EN.pdf'


def test_filtre_idioma_principal_es_null():
    assert 'IS NULL' in str(d._filtre_idioma(None))
    assert 'IS NULL' not in str(d._filtre_idioma('en'))


@pytest.mark.parametrize('funcio', [
    d._referencia_al_desti,
    d._destins_amb_fitxa,
])
def test_consultes_per_desti_filtren_idioma(funcio):
    """Cap consulta de l'última distribució d'un destí pot ignorar l'idioma."""
    assert '_filtre_idioma(idioma)' in inspect.getsource(funcio)


def test_jobs_massius_nomes_pdf_principal():
    from app.routes.jobs import _parells_distribuits
    assert 'd.idioma IS NULL' in inspect.getsource(_parells_distribuits)


def test_resum_de_la_llista_nomes_pdf_principal():
    from app.routes import fitxes
    assert "filter_by(versio_id=va.id, idioma=None)" in inspect.getsource(fitxes)


def test_executar_distribucio_fa_servir_l_idioma():
    codi = inspect.getsource(d._executar_distribucio)
    assert codi.count('_assegurar_pdf(fitxa, versio, dist.idioma)') == 4
    assert codi.count('_generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio, dist.idioma)') == 4


# --- Capçaleres dels PDFs en un sol idioma (per a la comprovació) ----------

class _PaginaFalsa:
    def __init__(self, cel·les):
        self._taula = [[c] for c in cel·les]

    def extract_tables(self):
        return [self._taula]


@pytest.mark.parametrize('rev, comprov', [
    ('Fecha/Data Rev: 10/06/2024', 'Fecha/Data Comprov.: 11/06/2024'),   # bilingüe
    ('Fecha Rev.: 10/06/2024', 'Fecha Comprov.: 11/06/2024'),            # castellà
    ('Data Rev.: 10/06/2024', 'Data Comprov.: 11/06/2024'),              # català
    ('Rev. date: 10/06/2024', 'Check date: 11/06/2024'),                 # anglès
    ('Data rev.: 10/06/2024', 'Data verif.: 11/06/2024'),                # portuguès
])
def test_capcalera_en_tots_els_idiomes(rev, comprov):
    info = _parse_header([_PaginaFalsa(['Rev.: 3', rev, comprov])])
    assert info == {'rev': '3', 'data_revisio': '10/06/2024',
                    'data_comprovacio': '11/06/2024'}
