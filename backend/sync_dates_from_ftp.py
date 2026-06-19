"""
Corregeix data_revisio i data_comprovacio de la versio activa de cada fitxa
a partir del PDF que hi ha al FTP corporatiu (font de veritat).

La configuracio del FTP es llegeix del registre de DestiDistribucio amb
tipus='ftp' (per defecte el que es diu 'ftp'; per altres noms usa --desti).

Mode dry-run per defecte (no escriu res). Per aplicar realment cal --apply.

Us:
    cd backend
    venv\\Scripts\\activate                          # Windows
    source venv/bin/activate                          # Linux

    python sync_dates_from_ftp.py                    # dry-run, totes les fitxes
    python sync_dates_from_ftp.py --apply            # aplica els canvis
    python sync_dates_from_ftp.py --art-codi 60360   # nomes una fitxa (debug)
    python sync_dates_from_ftp.py --desti "ftp clients"
        # usa un desti FTP amb un nom diferent
    python sync_dates_from_ftp.py --apply --force-null
        # si el PDF no te data, posa NULL a la BD (per defecte preserva)
"""

import argparse
import csv
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import FitxaTecnica, VersioFitxa, DestiDistribucio
from app.routes.distribucions import _generar_nom_fitxer
from app.services.ftp_distributor import descarregar_ftp
from app.services.pdf_parser import parse_pdf


def _data_str(dt):
    """Format dd/mm/aaaa o '-' si None."""
    if not dt:
        return '-'
    return dt.strftime('%d/%m/%Y')


def _parse_pdf_date(s):
    """Converteix 'dd/mm/aaaa' a datetime UTC. None si invalid."""
    if not s:
        return None
    try:
        return datetime.strptime(s, '%d/%m/%Y').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _dates_iguals(a, b):
    """Compara dues dates ignorant l'hora (nomes any/mes/dia)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return (a.year, a.month, a.day) == (b.year, b.month, b.day)


def _trobar_desti_ftp(nom):
    """Troba el desti de tipus FTP. Si nom està especificat, l'usa; sino
    busca un desti actiu de tipus 'ftp' (preferint el que es diu 'ftp')."""
    if nom:
        d = DestiDistribucio.query.filter_by(nom=nom, tipus='ftp').first()
        if not d:
            print(f'ERROR: no existeix cap desti FTP amb nom="{nom}"')
            sys.exit(1)
        return d

    # Sense --desti: busca per defecte
    d = DestiDistribucio.query.filter_by(nom='ftp', tipus='ftp', actiu=True).first()
    if d:
        return d
    # Fallback: qualsevol desti FTP actiu
    candidates = DestiDistribucio.query.filter_by(tipus='ftp', actiu=True).all()
    if not candidates:
        print('ERROR: no s\'ha trobat cap desti de tipus FTP actiu a la BD')
        sys.exit(1)
    if len(candidates) > 1:
        noms = ', '.join(f'"{c.nom}"' for c in candidates)
        print(f'ERROR: hi ha {len(candidates)} destins FTP actius ({noms}). '
              f'Especifica --desti <nom>')
        sys.exit(1)
    return candidates[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true',
                        help='Aplica els canvis (sense aquest flag es dry-run)')
    parser.add_argument('--art-codi', default=None,
                        help='Processa nomes la fitxa amb aquest codi (debug)')
    parser.add_argument('--desti', default=None,
                        help='Nom del DestiDistribucio FTP a usar '
                             '(per defecte: el que es diu "ftp")')
    parser.add_argument('--force-null', action='store_true',
                        help='Si el PDF no te data, posa NULL a la BD '
                             '(per defecte preserva el valor existent)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        desti = _trobar_desti_ftp(args.desti)
        # configuracio_segura() desxifra password si l'encriptacio esta desplegada;
        # si el codi de producció encara no la té, llegim el JSON directament.
        if hasattr(desti, 'configuracio_segura'):
            config = desti.configuracio_segura() or {}
        else:
            config = dict(desti.configuracio or {})
        host = config.get('host', '')
        user = config.get('user', '')
        if not host or not user:
            print(f'ERROR: desti FTP "{desti.nom}" no te host/user configurats')
            sys.exit(1)
        print(f"Desti FTP: \"{desti.nom}\" -> {user}@{host}:"
              f"{config.get('port', 21)}{config.get('path', '/')} "
              f"(tls={config.get('tls', True)})")
        print(f"Patro nom fitxer: {desti.patro_nom_fitxer}")
        print()

        # Fitxes amb almenys una versio activa
        query = (db.session.query(FitxaTecnica, VersioFitxa)
                 .join(VersioFitxa, VersioFitxa.fitxa_id == FitxaTecnica.id)
                 .filter(VersioFitxa.activa.is_(True))
                 .order_by(FitxaTecnica.art_codi))
        if args.art_codi:
            query = query.filter(FitxaTecnica.art_codi == args.art_codi)

        parelles = query.all()
        if not parelles:
            print('No s\'ha trobat cap fitxa amb versio activa.')
            sys.exit(0)
        print(f'Processant {len(parelles)} fitxes amb versio activa...')
        print()

        canvis = []      # [(art_codi, versio_id, camp, valor_antic, valor_nou)]
        report_rows = []  # per CSV
        stats = {
            'total': len(parelles),
            'iguals': 0,
            'canvi_revisio': 0,
            'canvi_comprovacio': 0,
            'missing_ftp': 0,
            'parse_error': 0,
            'ftp_error': 0,
        }

        for fitxa, versio in parelles:
            filename = _generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio)
            status = ''
            data_rev_pdf = None
            data_comp_pdf = None

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp_path = tmp.name
            try:
                result = descarregar_ftp(filename, config, tmp_path)
                if not result['ok']:
                    if result['not_found']:
                        stats['missing_ftp'] += 1
                        status = 'MISSING_FTP'
                        print(f'  {fitxa.art_codi} ({filename}): PDF no trobat al FTP')
                    else:
                        stats['ftp_error'] += 1
                        status = f"FTP_ERROR: {result['error']}"
                        print(f'  {fitxa.art_codi} ({filename}): error FTP: '
                              f'{result["error"]}')
                    report_rows.append({
                        'art_codi': fitxa.art_codi,
                        'filename_ftp': filename,
                        'versio_id': versio.id,
                        'status': status,
                        'data_revisio_bd': _data_str(versio.data_revisio),
                        'data_revisio_pdf': '',
                        'data_comprovacio_bd': _data_str(versio.data_comprovacio),
                        'data_comprovacio_pdf': '',
                    })
                    continue

                try:
                    parsed = parse_pdf(tmp_path)
                except Exception as e:
                    stats['parse_error'] += 1
                    status = f'PARSE_ERROR: {e}'
                    print(f'  {fitxa.art_codi}: error parseig: {e}')
                    report_rows.append({
                        'art_codi': fitxa.art_codi,
                        'filename_ftp': filename,
                        'versio_id': versio.id,
                        'status': status,
                        'data_revisio_bd': _data_str(versio.data_revisio),
                        'data_revisio_pdf': '',
                        'data_comprovacio_bd': _data_str(versio.data_comprovacio),
                        'data_comprovacio_pdf': '',
                    })
                    continue
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            data_rev_pdf = _parse_pdf_date(parsed.get('data_revisio'))
            data_comp_pdf = _parse_pdf_date(parsed.get('data_comprovacio'))

            # Comparar i preparar canvis
            row_canvis = []

            if data_rev_pdf is None and parsed.get('data_revisio'):
                print(f'  {fitxa.art_codi}: data_revisio al PDF no valida '
                      f'({parsed.get("data_revisio")!r})')

            if data_comp_pdf is None and parsed.get('data_comprovacio'):
                print(f'  {fitxa.art_codi}: data_comprovacio al PDF no valida '
                      f'({parsed.get("data_comprovacio")!r})')

            # data_revisio
            if data_rev_pdf is not None:
                if not _dates_iguals(versio.data_revisio, data_rev_pdf):
                    row_canvis.append(('data_revisio',
                                       versio.data_revisio, data_rev_pdf))
                    stats['canvi_revisio'] += 1
            elif args.force_null and versio.data_revisio is not None:
                row_canvis.append(('data_revisio',
                                   versio.data_revisio, None))
                stats['canvi_revisio'] += 1

            # data_comprovacio
            if data_comp_pdf is not None:
                if not _dates_iguals(versio.data_comprovacio, data_comp_pdf):
                    row_canvis.append(('data_comprovacio',
                                       versio.data_comprovacio, data_comp_pdf))
                    stats['canvi_comprovacio'] += 1
            elif args.force_null and versio.data_comprovacio is not None:
                row_canvis.append(('data_comprovacio',
                                   versio.data_comprovacio, None))
                stats['canvi_comprovacio'] += 1

            if row_canvis:
                status = 'CANVI'
                for camp, antic, nou in row_canvis:
                    canvis.append((fitxa.art_codi, versio.id, camp, antic, nou))
                    print(f'  {fitxa.art_codi}: {camp} {_data_str(antic)} -> '
                          f'{_data_str(nou)}')
            else:
                stats['iguals'] += 1
                status = 'OK'

            report_rows.append({
                'art_codi': fitxa.art_codi,
                'filename_ftp': filename,
                'versio_id': versio.id,
                'status': status,
                'data_revisio_bd': _data_str(versio.data_revisio),
                'data_revisio_pdf': _data_str(data_rev_pdf),
                'data_comprovacio_bd': _data_str(versio.data_comprovacio),
                'data_comprovacio_pdf': _data_str(data_comp_pdf),
            })

        # Resum
        print()
        print('=' * 60)
        print('RESUM')
        print('=' * 60)
        print(f'  Total fitxes processades:        {stats["total"]}')
        print(f'  Ja correctes:                    {stats["iguals"]}')
        print(f'  Canvis pendents data_revisio:    {stats["canvi_revisio"]}')
        print(f'  Canvis pendents data_comprovacio:{stats["canvi_comprovacio"]}')
        print(f'  PDF no trobat al FTP:            {stats["missing_ftp"]}')
        print(f'  Errors de parseig PDF:           {stats["parse_error"]}')
        print(f'  Errors FTP:                      {stats["ftp_error"]}')

        # Guardar report CSV
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(os.path.dirname(__file__),
                                   f'sync_dates_report_{ts}.csv')
        with open(report_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'art_codi', 'filename_ftp', 'versio_id', 'status',
                'data_revisio_bd', 'data_revisio_pdf',
                'data_comprovacio_bd', 'data_comprovacio_pdf',
            ])
            writer.writeheader()
            writer.writerows(report_rows)
        print(f'\nReport guardat a: {report_path}')

        if not canvis:
            print('\nNo hi ha canvis a aplicar.')
            return

        if not args.apply:
            print(f'\nDRY-RUN. {len(canvis)} canvis pendents. '
                  'Per aplicar afegeix --apply')
            return

        # APPLY
        print(f'\nAplicant {len(canvis)} canvis...')
        for art_codi, versio_id, camp, _antic, nou in canvis:
            versio = db.session.get(VersioFitxa, versio_id)
            if not versio:
                print(f'  AVIS: versio {versio_id} no existeix (saltada)')
                continue
            setattr(versio, camp, nou)

        db.session.commit()
        print(f'OK: {len(canvis)} canvis aplicats i committats.')


if __name__ == '__main__':
    main()
