"""Crea el tipus estàndard i vincula les seccions existents."""
import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models import TipusFitxa, SeccioFitxa

app = create_app()
with app.app_context():
    # Crear tipus estàndard si no existeix
    estandard = TipusFitxa.query.filter_by(slug='estandard').first()
    if not estandard:
        estandard = TipusFitxa(
            nom='Fitxa tècnica estàndard',
            slug='estandard',
            descripcio='Plantilla estàndard per a productes elaborats (farines). Serveix com a base per crear nous tipus.',
        )
        db.session.add(estandard)
        db.session.flush()
        print(f'Tipus estàndard creat (id={estandard.id})')
    else:
        print(f'Tipus estàndard ja existeix (id={estandard.id})')

    # Vincular seccions sense tipus al tipus estàndard
    seccions_orfanes = SeccioFitxa.query.filter_by(tipus_id=None).all()
    for s in seccions_orfanes:
        s.tipus_id = estandard.id
        print(f'  Secció "{s.titol}" vinculada al tipus estàndard')

    db.session.commit()
    print('Fet.')
