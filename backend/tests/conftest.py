"""Fixtures compartides pels tests.

Cap test d'aquest paquet toca la base de dades ni la xarxa: els distribuidors
son funcions pures (dict entra, dict surt) i les connexions FTP/SFTP es
substitueixen per mocks.
"""

import pytest


@pytest.fixture(autouse=True)
def sense_espera(monkeypatch):
    """Neutralitza els time.sleep() dels reintents.

    Sense aixo, cada test que esgota els 3 intents trigaria 5 segons reals.
    """
    monkeypatch.setattr('time.sleep', lambda _s: None)


@pytest.fixture
def pdf_temporal(tmp_path):
    """Un PDF minim al disc, per als casos que comproven que el fitxer existeix."""
    pdf = tmp_path / '60360.pdf'
    pdf.write_bytes(b'%PDF-1.4 contingut de prova')
    return str(pdf)


@pytest.fixture
def config_ftp():
    return {
        'host': 'ftp.exemple.local',
        'port': 21,
        'user': 'qualitat',
        'password': 'secret',
        'path': '/fitxestecniques',
        'tls': True,
    }


@pytest.fixture
def config_sftp():
    return {
        'host': 'sftp.exemple.local',
        'port': 22,
        'user': 'qualitat',
        'password': 'secret',
        'path': '/fitxestecniques',
    }
