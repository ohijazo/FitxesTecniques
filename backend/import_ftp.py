"""
Script per descarregar tots els PDFs del FTP i associar-los a les fitxes de la BD.

- Si la fitxa ja existeix: associa el PDF a la versió activa
- Si la fitxa no existeix: crea una fitxa nova amb versió 0 i el PDF

Ús:
    cd backend
    venv\Scripts\activate
    python import_ftp.py
"""

import ftplib
import io
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models import FitxaTecnica, VersioFitxa

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')


def ensure_dir(art_codi, num_versio):
    path = os.path.join(UPLOAD_DIR, art_codi, f'v{num_versio}')
    os.makedirs(path, exist_ok=True)
    return path


def importar():
    app = create_app()

    host = os.environ.get('FTP_HOST')
    user = os.environ.get('FTP_USER')
    pwd = os.environ.get('FTP_PASSWORD')
    ftp_path = os.environ.get('FTP_PATH', '/')

    print(f'Connectant a {host}...')
    ftp = ftplib.FTP(host)
    ftp.login(user, pwd)
    if ftp_path and ftp_path != '/':
        ftp.cwd(ftp_path)
    print(f'Connectat. Directori: {ftp.pwd()}')

    # Llistar PDFs
    files = [f for f in ftp.nlst() if f.endswith('.pdf')]
    print(f'PDFs trobats: {len(files)}')

    with app.app_context():
        associats = 0
        creats = 0
        errors = 0

        for filename in files:
            art_codi = filename.replace('.pdf', '').strip()
            if not art_codi:
                continue

            try:
                fitxa = FitxaTecnica.query.filter_by(art_codi=art_codi).first()

                if fitxa:
                    # Fitxa existent: buscar versió activa o última
                    versio = VersioFitxa.query.filter_by(
                        fitxa_id=fitxa.id, activa=True
                    ).first()
                    if not versio:
                        versio = VersioFitxa.query.filter_by(
                            fitxa_id=fitxa.id
                        ).order_by(VersioFitxa.num_versio.desc()).first()

                    if not versio:
                        print(f'  SKIP {art_codi}: fitxa sense versions')
                        continue

                    num_v = versio.num_versio
                else:
                    # Fitxa nova
                    fitxa = FitxaTecnica(
                        art_codi=art_codi,
                        nom_producte=f'Producte {art_codi}',
                        categoria='',
                        estat='publicada',
                        created_by='importació FTP',
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db.session.add(fitxa)
                    db.session.flush()

                    versio = VersioFitxa(
                        fitxa_id=fitxa.id,
                        num_versio=0,
                        descripcio_canvi='Importat des del FTP',
                        contingut={},
                        created_by='importació FTP',
                        created_at=datetime.now(timezone.utc),
                        activa=True,
                    )
                    db.session.add(versio)
                    db.session.flush()
                    num_v = 0
                    creats += 1

                # Descarregar PDF
                upload_path = ensure_dir(art_codi, num_v)
                pdf_path = os.path.join(upload_path, f'{art_codi}.pdf')

                with open(pdf_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {filename}', f.write)

                versio.fitxer_pdf = pdf_path
                db.session.commit()
                associats += 1

                if associats % 20 == 0:
                    print(f'  ... {associats}/{len(files)} processats')

            except Exception as e:
                db.session.rollback()
                errors += 1
                print(f'  ERROR {art_codi}: {e}')

        ftp.quit()

        print(f'\n{"="*50}')
        print(f'Importació FTP completada!')
        print(f'  PDFs associats a fitxes existents: {associats - creats}')
        print(f'  Fitxes noves creades: {creats}')
        print(f'  Errors: {errors}')
        print(f'  Total processats: {associats + errors}')


if __name__ == '__main__':
    importar()
