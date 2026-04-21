import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/fitxes_tecniques'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Entorn: development | production
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'

    # CORS
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 'http://localhost:5173,http://localhost:5174'
    ).split(',')

    # FTP
    FTP_HOST = os.environ.get('FTP_HOST', '')
    FTP_PORT = int(os.environ.get('FTP_PORT', 21))
    FTP_USER = os.environ.get('FTP_USER', '')
    FTP_PASSWORD = os.environ.get('FTP_PASSWORD', '')
    FTP_PATH = os.environ.get('FTP_PATH', '/')

    # Carpeta xarxa (pendent)
    NETWORK_SHARE_PATH = os.environ.get('NETWORK_SHARE_PATH', '')
