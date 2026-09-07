"""
Corregeix als destins les fitxes que la comprovacio marca com a incorrectes.

Cas d'us principal: la distribucio imprimia `versio.created_at` en comptes de
`versio.data_revisio`, aixi que els PDF que ja son al FTP / SharePoint /
carpeta de xarxa porten una data que no es la de la fitxa. El codi ja esta
corregit, pero els fitxers de fora no.

Una redistribucio normal NO n'hi ha prou: _assegurar_pdf() reutilitza el PDF
local si existeix, i aquest ja porta la data dolenta gravada. Aquest script
esborra primer el PDF generat perque es torni a generar amb la data bona, i
despres redistribueix.

QUE ARREGLA I QUE NO
    desfasat       -> si, el PDF del desti es substitueix pel correcte
    error_parseig  -> si, el fitxer il·legible es substitueix
    no_trobat      -> si, es torna a pujar (la BD diu que hi ha de ser)
    sobrant        -> NO. Redistribuir empitjoraria: el fitxer s'ha d'ESBORRAR,
                      no tornar a pujar. Es llista a part perque el retiris tu.
    error_acces    -> NO. Es un problema de xarxa o de credencials del desti.

SEGURETAT
  - Nomes esborra el PDF local de producte ELABORAT (es regenerable). Els de
    producte comercialitzat tenen un original pujat a ma: es redistribueixen
    tal qual, sense tocar-los.
  - Nomes esborra fitxers de dins de uploads/<art_codi>/v<num>/.
  - Nomes actua sobre destins on la fitxa JA consta distribuida.
  - Torna a comprovar cada desti abans d'actuar-hi: si ja es correcte, el deixa.
  - Cada redistribucio queda registrada com una Distribucio normal.
  - Mode dry-run per defecte: sense --apply no esborra ni puja res.

Us:
    cd backend
    source venv/bin/activate                          # Linux
    venv\\Scripts\\activate                            # Windows

    # A partir d'una comprovacio ja feta (recomanat: no torna a escanejar-ho tot)
    python redistribuir_data_revisio.py --des-de-job 6
    python redistribuir_data_revisio.py --des-de-job 6 --apply

    # Escanejant de nou (nomes les que tenen data_revisio != created_at)
    python redistribuir_data_revisio.py
    python redistribuir_data_revisio.py --apply

    # Escanejant de nou TOTES les fitxes distribuides
    python redistribuir_data_revisio.py --tots --apply

    # Limitacions utils
    python redistribuir_data_revisio.py --art-codi 60360 --apply
    python redistribuir_data_revisio.py --des-de-job 6 --desti 1 --apply
"""

import argparse
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import (FitxaTecnica, VersioFitxa, DestiDistribucio, Distribucio,
                        JobItem)
from app.routes.distribucions import _destins_amb_fitxa, _executar_distribucio
from app.services.verificador import verificar_distribucio
from app.services.sftp_distributor import tancar_sessions

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))

# Estats que una redistribucio arregla de debo.
ARREGLABLES = ('desfasat', 'error_parseig', 'no_trobat')
# Estats que NO s'arreglen pujant el fitxer (sobrant: s'ha d'esborrar!).
NO_ARREGLABLES = ('sobrant', 'error_acces')


def _data_str(dt):
    return dt.strftime('%d/%m/%Y') if dt else '-'


def _versio_activa(fitxa_id):
    return VersioFitxa.query.filter_by(fitxa_id=fitxa_id, activa=True).first()


def _parells_des_de_job(job_id):
    """(fitxa, versio, desti) dels items d'un job de comprovacio amb incidencia.

    Aprofita la feina ja feta: nomes es tornen a mirar els que van sortir
    malament, no totes les fitxes.
    """
    items = JobItem.query.filter(
        JobItem.job_id == job_id,
        JobItem.resultat.isnot(None),
    ).all()

    parells, descartats = [], {}
    for it in items:
        estat = (it.resultat or {}).get('estat_verificacio')
        if estat in ARREGLABLES:
            parells.append((it.fitxa_id, it.desti_id))
        elif estat in NO_ARREGLABLES:
            descartats.setdefault(estat, []).append(it)
    return parells, descartats


def _parells_per_data(art_codi=None):
    """(fitxa_id, desti_id) de les versions on data_revisio != created_at.

    Nomes producte elaborat: el bug de la data nomes afecta els PDF que genera
    l'aplicacio.
    """
    q = (db.session.query(FitxaTecnica, VersioFitxa)
         .join(VersioFitxa, VersioFitxa.fitxa_id == FitxaTecnica.id)
         .filter(VersioFitxa.activa.is_(True))
         .order_by(FitxaTecnica.art_codi))
    if art_codi:
        q = q.filter(FitxaTecnica.art_codi == art_codi)

    parells = []
    for fitxa, versio in q.all():
        if (fitxa.tipus_producte or 'elaborat') == 'comercialitzat':
            continue
        if not versio.data_revisio or not versio.created_at:
            continue
        if versio.data_revisio.date() == versio.created_at.date():
            continue
        for did in sorted(_destins_amb_fitxa(fitxa.id)):
            parells.append((fitxa.id, did))
    return parells


def _parells_tots(art_codi=None):
    """(fitxa_id, desti_id) de tot el que consta distribuit."""
    q = (db.session.query(FitxaTecnica.id)
         .join(VersioFitxa, VersioFitxa.fitxa_id == FitxaTecnica.id)
         .filter(VersioFitxa.activa.is_(True))
         .order_by(FitxaTecnica.art_codi))
    if art_codi:
        q = q.filter(FitxaTecnica.art_codi == art_codi)

    parells = []
    for (fid,) in q.all():
        for did in sorted(_destins_amb_fitxa(fid)):
            parells.append((fid, did))
    return parells


def _invalidar_pdf(fitxa, versio, aplicar):
    """Esborra els PDF generats perque es tornin a generar correctament.

    Els de producte comercialitzat no es toquen: son originals pujats a ma i
    no es poden regenerar.
    """
    if (fitxa.tipus_producte or 'elaborat') == 'comercialitzat':
        return []

    carpeta = os.path.join(UPLOAD_DIR, fitxa.art_codi, f'v{versio.num_versio}')
    rutes = [
        os.path.join(carpeta, f'{fitxa.art_codi}.pdf'),          # _assegurar_pdf
        os.path.join(carpeta, f'{fitxa.art_codi}_generat.pdf'),  # cache de /pdf
    ]

    esborrats = []
    for ruta in rutes:
        if not os.path.exists(ruta):
            continue
        if not os.path.abspath(ruta).startswith(UPLOAD_DIR + os.sep):
            print(f"    AVIS: {ruta} es fora de uploads/, no s'esborra")
            continue
        if aplicar:
            os.remove(ruta)
        esborrats.append(os.path.basename(ruta))

    if aplicar and versio.fitxer_pdf and not os.path.exists(versio.fitxer_pdf):
        versio.fitxer_pdf = None
    return esborrats


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true',
                        help='Aplica els canvis (sense aquest flag es dry-run)')
    parser.add_argument('--des-de-job', type=int, default=None,
                        help='Agafa els candidats del resultat d\'un job de '
                             'comprovacio (recomanat)')
    parser.add_argument('--tots', action='store_true',
                        help='Escaneja totes les fitxes distribuides, no nomes '
                             'les que tenen data_revisio != created_at')
    parser.add_argument('--art-codi', default=None, help='Nomes aquesta fitxa')
    parser.add_argument('--desti', type=int, default=None, help='Nomes aquest desti (id)')
    parser.add_argument('--sense-verificar', action='store_true',
                        help='No torna a comprovar el desti abans d\'actuar-hi')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        descartats = {}
        if args.des_de_job:
            parells, descartats = _parells_des_de_job(args.des_de_job)
            origen = f'job de comprovacio #{args.des_de_job}'
        elif args.tots:
            parells = _parells_tots(args.art_codi)
            origen = 'totes les fitxes distribuides'
        else:
            parells = _parells_per_data(args.art_codi)
            origen = 'fitxes amb data_revisio != created_at'

        if args.desti:
            parells = [(f, d) for f, d in parells if d == args.desti]
        if args.art_codi and args.des_de_job:
            codis = {f.id for f in FitxaTecnica.query.filter_by(
                art_codi=args.art_codi).all()}
            parells = [(f, d) for f, d in parells if f in codis]

        print(f'Origen dels candidats: {origen}')
        print(f'Parells fitxa-desti a tractar: {len(parells)}')

        if descartats:
            print('\nNO es tractaran (redistribuir no ho arregla):')
            for estat, items in sorted(descartats.items()):
                print(f'  {estat}: {len(items)}')
                if estat == 'sobrant':
                    print('    -> aquests fitxers s\'han d\'ESBORRAR del desti, '
                          'no tornar a pujar.')
                    print('       Fes-ho des del detall de la fitxa: '
                          'Distribucions > Retirar.')
                    for it in items[:10]:
                        codi = it.fitxa.art_codi if it.fitxa else it.fitxa_id
                        nom = it.desti.nom if it.desti else it.desti_id
                        print(f'       - {codi} a {nom}')
                    if len(items) > 10:
                        print(f'       ... i {len(items) - 10} mes (veure CSV)')
                elif estat == 'error_acces':
                    print('    -> revisa la configuracio del desti '
                          '(Configuracio > Destins).')

        if not parells:
            print('\nNo hi ha res a redistribuir.')
            return

        print()
        if not args.apply:
            print("MODE DRY-RUN: no s'esborrara ni es pujara res.\n")
        else:
            print('MODE APPLY: es regeneraran i es pujaran als destins.\n')

        # Agrupar per fitxa: el PDF s'invalida un cop, no un per desti.
        per_fitxa = {}
        for fid, did in parells:
            per_fitxa.setdefault(fid, []).append(did)

        cache_destins = {}
        files_csv = []
        stats = {'ok': 0, 'ja_correctes': 0, 'omesos': 0, 'errors': 0,
                 'a_redistribuir': 0}

        for estat, items in descartats.items():
            for it in items:
                files_csv.append({
                    'art_codi': it.fitxa.art_codi if it.fitxa else str(it.fitxa_id),
                    'desti': it.desti.nom if it.desti else str(it.desti_id),
                    'accio': 'descartat', 'estat': estat, 'detall': it.missatge_error or '',
                })

        for fid, dids in per_fitxa.items():
            fitxa = db.session.get(FitxaTecnica, fid)
            versio = _versio_activa(fid) if fitxa else None
            if not fitxa or not versio:
                continue

            print(f'{fitxa.art_codi} — {fitxa.nom_producte}')
            print(f'  BD: rev {versio.num_versio}, data_revisio '
                  f'{_data_str(versio.data_revisio)} '
                  f'(created_at {_data_str(versio.created_at)})')

            # 1) Confirmar quins destins cal tocar
            a_corregir = []
            for did in dids:
                desti = cache_destins.get(did)
                if desti is None:
                    desti = db.session.get(DestiDistribucio, did)
                    cache_destins[did] = desti
                if not desti or not desti.actiu:
                    continue

                if args.sense_verificar:
                    a_corregir.append(desti)
                    continue

                res = verificar_distribucio(fitxa, versio, desti, timeout=15)
                estat = res['estat_verificacio']
                if estat in ARREGLABLES:
                    print(f'  [{desti.nom}] {estat}: {res["missatge"]}')
                    a_corregir.append(desti)
                elif estat == 'ok':
                    print(f'  [{desti.nom}] ja es correcte, no cal tocar-lo')
                    stats['ja_correctes'] += 1
                else:
                    print(f'  [{desti.nom}] {estat}: {res["missatge"]} — s\'omet')
                    stats['omesos'] += 1
                    files_csv.append({
                        'art_codi': fitxa.art_codi, 'desti': desti.nom,
                        'accio': 'omes', 'estat': estat, 'detall': res['missatge'],
                    })

            if not a_corregir:
                print()
                continue

            # 2) Invalidar el PDF local (si no, es tornaria a pujar el dolent)
            esborrats = _invalidar_pdf(fitxa, versio, args.apply)
            if esborrats:
                verb = 'Esborrats' if args.apply else "S'esborrarien"
                print(f'  {verb}: {", ".join(esborrats)}')
            elif (fitxa.tipus_producte or 'elaborat') == 'comercialitzat':
                print('  (producte comercialitzat: es puja l\'original, no es regenera)')

            # 3) Redistribuir
            for desti in a_corregir:
                if not args.apply:
                    stats['a_redistribuir'] += 1
                    print(f'  [{desti.nom}] es redistribuiria')
                    files_csv.append({
                        'art_codi': fitxa.art_codi, 'desti': desti.nom,
                        'accio': 'es_redistribuiria', 'estat': '', 'detall': '',
                    })
                    continue

                dist = Distribucio(versio_id=versio.id, desti_id=desti.id,
                                   desti=desti.nom, estat='pendent')
                db.session.add(dist)
                db.session.flush()
                try:
                    _executar_distribucio(dist, fitxa, versio, desti,
                                          executat_by='redistribuir_data_revisio')
                except Exception as e:
                    dist.estat = 'error'
                    dist.missatge_error = str(e)
                db.session.commit()

                if dist.estat == 'ok':
                    stats['ok'] += 1
                    print(f'  [{desti.nom}] redistribuit OK')
                else:
                    stats['errors'] += 1
                    print(f'  [{desti.nom}] ERROR: {dist.missatge_error}')
                files_csv.append({
                    'art_codi': fitxa.art_codi, 'desti': desti.nom,
                    'accio': 'redistribuit', 'estat': dist.estat,
                    'detall': dist.missatge_error or '',
                })
            print()

        print('=' * 60)
        print('RESUM')
        print('=' * 60)
        print(f'  Fitxes tractades:           {len(per_fitxa)}')
        if not args.apply:
            print(f'  ES REDISTRIBUIRIEN:         {stats["a_redistribuir"]}'
                  ' parells fitxa-desti')
        print(f'  Destins ja correctes:       {stats["ja_correctes"]}')
        print(f'  Destins omesos:             {stats["omesos"]}')
        print(f'  Redistribucions OK:         {stats["ok"]}')
        print(f'  Redistribucions amb error:  {stats["errors"]}')
        if descartats:
            total_desc = sum(len(v) for v in descartats.values())
            print(f'  Descartats (sobrant/acces): {total_desc}')

        if files_csv:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            ruta = os.path.join(os.path.dirname(__file__),
                                f'redistribucio_{ts}.csv')
            with open(ruta, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=['art_codi', 'desti', 'accio',
                                                  'estat', 'detall'])
                w.writeheader()
                w.writerows(files_csv)
            print(f'\nInforme: {ruta}')

        if not args.apply:
            print('\nDRY-RUN. Per aplicar-ho de debo, afegeix --apply')

        # Les sessions SFTP es reaprofiten entre operacions:
        # cal tancar-les explicitament en acabar l'script.
        tancar_sessions()


if __name__ == '__main__':
    main()
