"""
Corregeix la data de revisio dels PDF que ja son als destins.

La distribucio imprimia `versio.created_at` (quan es va crear la fila a la BD,
p. ex. en una carrega massiva) en comptes de `versio.data_revisio`. El codi ja
esta corregit, pero els PDF que ja son al FTP / SharePoint / carpeta de xarxa
segueixen amb la data antiga fins que es tornin a distribuir.

Una redistribucio normal NO n'hi ha prou: _assegurar_pdf() reutilitza el PDF
local si existeix, i aquest ja porta la data dolenta gravada. Aquest script
esborra primer el PDF generat (i el seu cache) perque es torni a generar amb
la data bona, i despres redistribueix.

SEGURETAT
  - Nomes toca fitxes de producte ELABORAT. Les de producte comercialitzat
    tenen un PDF original pujat a ma que no s'ha de regenerar mai.
  - Nomes esborra fitxers de dins de uploads/<art_codi>/v<num>/.
  - Nomes redistribueix als destins on la fitxa JA consta distribuida.
  - Cada redistribucio queda registrada com una Distribucio normal
    (audit trail intacte).
  - Mode dry-run per defecte: sense --apply no escriu ni puja res.

Us:
    cd backend
    venv\\Scripts\\activate                           # Windows
    source venv/bin/activate                          # Linux

    python redistribuir_data_revisio.py                    # dry-run, totes
    python redistribuir_data_revisio.py --art-codi 60360   # una sola (prova!)
    python redistribuir_data_revisio.py --art-codi 60360 --apply
    python redistribuir_data_revisio.py --apply            # totes
    python redistribuir_data_revisio.py --apply --sense-verificar
        # no comprova el desti abans: redistribueix tots els candidats
    python redistribuir_data_revisio.py --apply --desti 1
        # nomes a un desti concret
"""

import argparse
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import FitxaTecnica, VersioFitxa, DestiDistribucio, Distribucio
from app.routes.distribucions import (
    _destins_amb_fitxa,
    _executar_distribucio,
    _referencia_al_desti,
)
from app.services.verificador import verificar_distribucio

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))


def _data_str(dt):
    return dt.strftime('%d/%m/%Y') if dt else '-'


def _candidats(art_codi=None):
    """Versions actives on el PDF distribuit pot portar la data equivocada.

    Nomes producte elaborat: el PDF es genera del contingut i per tant el va
    estampar el codi que tenia el bug.
    """
    q = (db.session.query(FitxaTecnica, VersioFitxa)
         .join(VersioFitxa, VersioFitxa.fitxa_id == FitxaTecnica.id)
         .filter(VersioFitxa.activa.is_(True))
         .order_by(FitxaTecnica.art_codi))
    if art_codi:
        q = q.filter(FitxaTecnica.art_codi == art_codi)

    candidats = []
    for fitxa, versio in q.all():
        if (fitxa.tipus_producte or 'elaborat') == 'comercialitzat':
            continue
        if not versio.data_revisio or not versio.created_at:
            continue
        if versio.data_revisio.date() == versio.created_at.date():
            continue
        candidats.append((fitxa, versio))
    return candidats


def _fitxers_generats(fitxa, versio):
    """PDF generats per aquesta versio que cal invalidar.

    Nomes els dos noms que genera l'aplicacio, i sempre dins de uploads/:
    aixi mai es pot esborrar un original pujat encara que fitxer_pdf apunti
    a un altre lloc.
    """
    carpeta = os.path.join(UPLOAD_DIR, fitxa.art_codi, f'v{versio.num_versio}')
    return [
        os.path.join(carpeta, f'{fitxa.art_codi}.pdf'),          # _assegurar_pdf
        os.path.join(carpeta, f'{fitxa.art_codi}_generat.pdf'),  # cache de /pdf
    ]


def _invalidar_pdf(fitxa, versio, aplicar):
    """Esborra els PDF generats perque es tornin a generar amb la data bona."""
    esborrats = []
    for ruta in _fitxers_generats(fitxa, versio):
        if not os.path.exists(ruta):
            continue
        if not os.path.abspath(ruta).startswith(UPLOAD_DIR + os.sep):
            print(f'    AVIS: {ruta} es fora de uploads/, no s\'esborra')
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
    parser.add_argument('--art-codi', default=None,
                        help='Nomes aquesta fitxa (recomanat per la primera prova)')
    parser.add_argument('--desti', type=int, default=None,
                        help='Nomes aquest desti (id)')
    parser.add_argument('--sense-verificar', action='store_true',
                        help='No comprova el desti abans: redistribueix tots '
                             'els candidats (mes rapid, menys precis)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        candidats = _candidats(args.art_codi)
        if not candidats:
            print('No hi ha cap fitxa candidata: totes les versions actives de '
                  'producte elaborat tenen data_revisio igual a created_at.')
            return

        print(f'Candidates: {len(candidats)} fitxes amb data_revisio != created_at')
        if not args.apply:
            print('MODE DRY-RUN: no s\'esborrara ni es pujara res.\n')
        else:
            print('MODE APPLY: es regeneraran i es pujaran als destins.\n')

        destins_cache = {}
        files_csv = []
        stats = {'redistribuides': 0, 'ja_correctes': 0, 'sense_desti': 0,
                 'errors': 0, 'omeses': 0}

        for fitxa, versio in candidats:
            ids_desti = _destins_amb_fitxa(fitxa.id)
            if args.desti:
                ids_desti = {d for d in ids_desti if d == args.desti}
            if not ids_desti:
                stats['sense_desti'] += 1
                continue

            print(f'{fitxa.art_codi} — {fitxa.nom_producte}')
            print(f'  BD: rev {versio.num_versio}, data_revisio '
                  f'{_data_str(versio.data_revisio)} '
                  f'(created_at {_data_str(versio.created_at)})')

            # 1) Quins destins tenen realment la data malament
            a_corregir = []
            for did in sorted(ids_desti):
                desti = destins_cache.get(did)
                if desti is None:
                    desti = db.session.get(DestiDistribucio, did)
                    destins_cache[did] = desti
                if not desti or not desti.actiu:
                    continue

                if args.sense_verificar:
                    a_corregir.append(desti)
                    continue

                res = verificar_distribucio(fitxa, versio, desti, timeout=15)
                estat = res['estat_verificacio']
                if estat == 'desfasat':
                    print(f'  [{desti.nom}] {res["missatge"]}')
                    a_corregir.append(desti)
                elif estat == 'ok':
                    print(f'  [{desti.nom}] ja es correcte, no cal tocar-lo')
                    stats['ja_correctes'] += 1
                else:
                    print(f'  [{desti.nom}] {estat}: {res["missatge"]} — s\'omet')
                    stats['omeses'] += 1
                files_csv.append({
                    'art_codi': fitxa.art_codi, 'desti': desti.nom,
                    'fase': 'abans', 'estat': estat,
                    'data_bd': _data_str(versio.data_revisio),
                    'data_desti': (res.get('desti_valors') or {}).get('data_revisio', ''),
                })

            if not a_corregir:
                continue

            # 2) Invalidar el PDF local (si no, es tornaria a pujar el dolent)
            esborrats = _invalidar_pdf(fitxa, versio, args.apply)
            if esborrats:
                verb = 'Esborrats' if args.apply else 'S\'esborrarien'
                print(f'  {verb}: {", ".join(esborrats)}')

            # 3) Redistribuir
            for desti in a_corregir:
                if not args.apply:
                    print(f'  [{desti.nom}] es redistribuiria')
                    continue

                nom, _enllac = _referencia_al_desti(fitxa, versio, desti)
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
                    stats['redistribuides'] += 1
                    print(f'  [{desti.nom}] redistribuit OK ({nom})')
                else:
                    stats['errors'] += 1
                    print(f'  [{desti.nom}] ERROR: {dist.missatge_error}')
                files_csv.append({
                    'art_codi': fitxa.art_codi, 'desti': desti.nom,
                    'fase': 'redistribucio', 'estat': dist.estat,
                    'data_bd': _data_str(versio.data_revisio),
                    'data_desti': '',
                })
            print()

        print('=' * 60)
        print('RESUM')
        print('=' * 60)
        print(f'  Fitxes candidates:            {len(candidats)}')
        print(f'  Sense cap desti distribuit:   {stats["sense_desti"]}')
        print(f'  Destins ja correctes:         {stats["ja_correctes"]}')
        print(f'  Destins omesos (error/absent):{stats["omeses"]}')
        print(f'  Redistribucions OK:           {stats["redistribuides"]}')
        print(f'  Redistribucions amb error:    {stats["errors"]}')

        if files_csv:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            ruta = os.path.join(os.path.dirname(__file__),
                                f'redistribucio_data_revisio_{ts}.csv')
            with open(ruta, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=['art_codi', 'desti', 'fase',
                                                  'estat', 'data_bd', 'data_desti'])
                w.writeheader()
                w.writerows(files_csv)
            print(f'\nInforme: {ruta}')

        if not args.apply:
            print('\nDRY-RUN. Per aplicar-ho de debo, torna-ho a executar amb --apply')


if __name__ == '__main__':
    main()
