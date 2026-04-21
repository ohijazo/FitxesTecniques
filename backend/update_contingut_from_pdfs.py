"""
Actualitza el contingut JSON de totes les fitxes a partir dels PDFs descarregats.

Per cada fitxa amb PDF associat:
1. Parseja el PDF amb pdf_parser
2. Actualitza el contingut de la versió activa
3. Actualitza nom_producte si el PDF té denominació comercial

Ús:
    cd backend
    venv\Scripts\activate
    python update_contingut_from_pdfs.py
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import FitxaTecnica, VersioFitxa
from app.services.pdf_parser import parse_pdf


def actualitzar():
    app = create_app()

    with app.app_context():
        # Buscar totes les versions amb PDF
        versions = VersioFitxa.query.filter(
            VersioFitxa.fitxer_pdf != None,
            VersioFitxa.fitxer_pdf != '',
            VersioFitxa.activa == True,
        ).all()

        print(f'Versions actives amb PDF: {len(versions)}')

        actualitzats = 0
        errors = 0
        sense_canvi = 0

        for versio in versions:
            pdf_path = versio.fitxer_pdf
            if not os.path.exists(pdf_path):
                print(f'  SKIP: PDF no existeix: {pdf_path}')
                errors += 1
                continue

            fitxa = FitxaTecnica.query.get(versio.fitxa_id)
            if not fitxa:
                continue

            try:
                result = parse_pdf(pdf_path)
                contingut_nou = result['contingut']

                if not contingut_nou or len(contingut_nou) < 3:
                    print(f'  SKIP {fitxa.art_codi}: contingut insuficient ({len(contingut_nou)} camps)')
                    sense_canvi += 1
                    continue

                # Actualitzar contingut de la versió
                versio.contingut = contingut_nou

                # Actualitzar data_comprovacio si el PDF la té
                if result['data_comprovacio']:
                    try:
                        dt = datetime.strptime(result['data_comprovacio'], '%d/%m/%Y')
                        versio.data_comprovacio = dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass

                # Actualitzar nom_producte si tenim denominació comercial
                denom = contingut_nou.get('denominacio_comercial', '').strip()
                if denom and len(denom) > 3:
                    fitxa.nom_producte = denom

                db.session.commit()
                actualitzats += 1

                if actualitzats % 20 == 0:
                    print(f'  ... {actualitzats} actualitzats')

            except Exception as e:
                db.session.rollback()
                errors += 1
                print(f'  ERROR {fitxa.art_codi}: {e}')

        print(f'\n{"="*50}')
        print(f'Actualització completada!')
        print(f'  Actualitzats: {actualitzats}')
        print(f'  Sense canvi: {sense_canvi}')
        print(f'  Errors: {errors}')


if __name__ == '__main__':
    actualitzar()
