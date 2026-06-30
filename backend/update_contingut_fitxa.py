"""
Actualitza el contingut JSON d'una sola fitxa a partir del PDF associat
a la seva versió activa.

Pensat per a casos puntuals on una fitxa té el PDF però no té el contingut
estructurat registrat a la BD.

Per defecte fa **dry-run** (mostra què faria sense escriure).
Per aplicar realment cal passar --apply.

Ús:
    cd backend
    venv\\Scripts\\activate                          # Windows
    source venv/bin/activate                          # Linux

    python update_contingut_fitxa.py 01921           # dry-run
    python update_contingut_fitxa.py 01921 --apply   # aplica
    python update_contingut_fitxa.py 01921 --apply --force
        # sobreescriu encara que ja hi hagi contingut (perillos!)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import FitxaTecnica, VersioFitxa
from app.services.pdf_parser import parse_pdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('art_codi', help="Codi d'article de la fitxa (ex: 01921)")
    parser.add_argument('--apply', action='store_true',
                        help='Aplica els canvis (sense aquest flag és dry-run)')
    parser.add_argument('--force', action='store_true',
                        help='Sobreescriu encara que la versió ja tingui contingut')
    parser.add_argument('--pdf', default=None,
                        help='Ruta al PDF (per defecte, fa servir versio.fitxer_pdf '
                             'o el patró uploads/<art_codi>/v<num>/<art_codi>.pdf)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        fitxa = FitxaTecnica.query.filter_by(art_codi=args.art_codi).first()
        if not fitxa:
            print(f'ERROR: no existeix cap fitxa amb art_codi={args.art_codi}')
            sys.exit(1)

        versio = VersioFitxa.query.filter_by(fitxa_id=fitxa.id, activa=True).first()
        if not versio:
            versio = (VersioFitxa.query.filter_by(fitxa_id=fitxa.id)
                      .order_by(VersioFitxa.num_versio.desc()).first())
        if not versio:
            print(f'ERROR: la fitxa {args.art_codi} no te cap versio')
            sys.exit(1)

        print(f'Fitxa: id={fitxa.id} art_codi={fitxa.art_codi} '
              f'nom_actual="{fitxa.nom_producte}"')
        print(f'Versio: id={versio.id} num_versio={versio.num_versio} '
              f'activa={versio.activa} estat={versio.estat_versio}')

        # Resoldre la ruta del PDF: --pdf > versio.fitxer_pdf > fallback patró
        pdf_path = None
        candidates = []
        if args.pdf:
            candidates.append(args.pdf)
        if versio.fitxer_pdf:
            candidates.append(versio.fitxer_pdf)
        # Fallback al patró convencional (uploads/<art_codi>/v<num>/<art_codi>.pdf)
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        fallback = os.path.join(backend_dir, 'uploads', fitxa.art_codi,
                                f'v{versio.num_versio}', f'{fitxa.art_codi}.pdf')
        candidates.append(fallback)

        for c in candidates:
            if c and os.path.exists(c):
                pdf_path = c
                break

        if not pdf_path:
            print('ERROR: PDF no trobat. He provat:')
            for c in candidates:
                print(f'  - {c!r}')
            sys.exit(1)
        print(f'PDF: {pdf_path}')
        if versio.fitxer_pdf and pdf_path != versio.fitxer_pdf:
            print(f'  (BD apunta a: {versio.fitxer_pdf!r} -- no existeix, '
                  'fent servir fallback)')

        contingut_actual = versio.contingut or {}
        n_camps_actual = len(contingut_actual)
        print(f'Contingut actual: {n_camps_actual} camps')

        if n_camps_actual > 0 and not args.force:
            print()
            print('La versio JA TE contingut. Per sobreescriure cal --force.')
            print('Camps actuals:', sorted(contingut_actual.keys()))
            sys.exit(2)

        result = parse_pdf(pdf_path)
        contingut_nou = result['contingut']
        if not contingut_nou or len(contingut_nou) < 3:
            print(f'ERROR: el parser ha extret nomes {len(contingut_nou)} camps; '
                  'el PDF no es valid o el parser no l\'entoma')
            sys.exit(1)

        camps_text = sorted(k for k, v in contingut_nou.items()
                            if not isinstance(v, list))
        camps_taula = sorted(k for k, v in contingut_nou.items()
                             if isinstance(v, list))
        print()
        print(f'Contingut nou: {len(contingut_nou)} camps')
        print(f'  Text   ({len(camps_text)}): {camps_text}')
        print(f'  Taules ({len(camps_taula)}): {camps_taula}')

        denom = (contingut_nou.get('denominacio_comercial') or '').strip()
        canviara_nom = denom and len(denom) > 3 and denom != fitxa.nom_producte
        if canviara_nom:
            print(f'\nnom_producte canviara: "{fitxa.nom_producte}" -> "{denom}"')

        canviara_data_comp = False
        nova_data_comp = None
        if result.get('data_comprovacio'):
            try:
                nova_data_comp = (datetime.strptime(result['data_comprovacio'], '%d/%m/%Y')
                                  .replace(tzinfo=timezone.utc))
                canviara_data_comp = (versio.data_comprovacio != nova_data_comp)
            except ValueError:
                pass
        if canviara_data_comp:
            print(f'data_comprovacio canviara: {versio.data_comprovacio} '
                  f'-> {nova_data_comp}')

        print()
        if not args.apply:
            print('DRY-RUN. No s\'ha escrit res. Per aplicar afegeix --apply')
            # Dump JSON per inspeccio
            dump = f'/tmp/contingut_{args.art_codi}.json'
            if not os.path.isdir('/tmp'):
                dump = os.path.join(os.path.dirname(__file__),
                                    f'contingut_{args.art_codi}.json')
            with open(dump, 'w', encoding='utf-8') as f:
                json.dump(contingut_nou, f, indent=2, ensure_ascii=False)
            print(f'JSON parsejat guardat a: {dump}')
            return

        # APPLY
        versio.contingut = contingut_nou
        if canviara_nom:
            fitxa.nom_producte = denom
        if canviara_data_comp:
            versio.data_comprovacio = nova_data_comp

        db.session.commit()
        print('OK: canvis aplicats i committats.')


if __name__ == '__main__':
    main()
