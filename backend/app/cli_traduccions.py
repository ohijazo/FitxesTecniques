"""Ordres per a la traducció inicial de totes les fitxes fora del servidor.

    flask exportar-per-traduir [--sortida /tmp/fitxes_per_traduir.json]
        Només llegeix. Escriu el contingut traduïble de la versió activa de
        cada fitxa elaborada.

    flask importar-traduccions FITXER [--aplicar]
        Importa traduccions generades fora (p.ex. amb Claude Code). Per
        defecte és una SIMULACIÓ: només diu què faria. Amb --aplicar, desa.
        - Cada traducció queda 'pendent' de revisar, amb còpia a l'historial.
        - Si la fitxa ha canviat de versió des de l'exportació, se la salta.
        - Si ja té traducció en aquell idioma, no la toca.
        - Marca l'idioma com a disponible a la fitxa (fitxa_tecnica.idiomes).
"""
import json
from datetime import datetime, timezone

import click

USUARI_IMPORTACIO = 'traducció inicial (Claude Code)'


def _registre_valid(r):
    """Motiu pel qual un registre del fitxer no és vàlid, o None."""
    from app.services.etiquetes_idioma import IDIOMES
    if not isinstance(r, dict):
        return 'no és un objecte'
    for clau in ('art_codi', 'versio_id', 'num_versio', 'idioma', 'contingut'):
        if clau not in r:
            return f'falta {clau}'
    if r['idioma'] not in IDIOMES:
        return f"idioma no vàlid: {r['idioma']}"
    if not isinstance(r['contingut'], dict) or not r['contingut']:
        return 'contingut buit'
    return None


def registrar(app):
    @app.cli.command('exportar-per-traduir')
    @click.option('--sortida', default='/tmp/fitxes_per_traduir.json', show_default=True)
    def exportar_per_traduir(sortida):
        """Exporta el contingut traduïble de la versió activa de cada fitxa (només lectura)."""
        from app.models import FitxaTecnica, VersioFitxa, TraduccioVersio
        from app.services.traduccio import CAMPS_TEXT, CAMPS_NOTA, CAMPS_TAULA

        fitxes = []
        for f in FitxaTecnica.query.order_by(FitxaTecnica.art_codi):
            if (f.tipus_producte or 'elaborat') == 'comercialitzat':
                continue
            v = VersioFitxa.query.filter_by(fitxa_id=f.id, activa=True).first()
            if not v or not v.contingut:
                continue
            c = v.contingut
            contingut = {k: c[k] for k in CAMPS_TEXT + CAMPS_NOTA if c.get(k)}
            for k in CAMPS_TAULA:
                if isinstance(c.get(k), list) and c[k]:
                    contingut[k] = [{'parametre': (fila or {}).get('parametre', ''),
                                     'valor': (fila or {}).get('valor', '')} for fila in c[k]]
            fitxes.append({
                'art_codi': f.art_codi,
                'nom_producte': f.nom_producte,
                'versio_id': v.id,
                'num_versio': v.num_versio,
                'idioma_original': c.get('_idioma') or 'bilingue',
                'ja_traduits': sorted(t.idioma for t in TraduccioVersio.query.filter_by(versio_id=v.id)),
                'contingut': contingut,
            })
        dades = {'exportat': datetime.now(timezone.utc).isoformat(), 'fitxes': fitxes}
        with open(sortida, 'w', encoding='utf-8') as fh:
            json.dump(dades, fh, ensure_ascii=False, indent=1)
        click.echo(f'{len(fitxes)} fitxes exportades a {sortida}')

    @app.cli.command('importar-traduccions')
    @click.argument('fitxer', type=click.Path(exists=True, dir_okay=False))
    @click.option('--aplicar', is_flag=True, help='Desa a la BD. Sense això, només simula.')
    def importar_traduccions(fitxer, aplicar):
        """Importa traduccions (pendents de revisar). Sense --aplicar és una simulació."""
        from app import db
        from app.models import FitxaTecnica, VersioFitxa, TraduccioVersio
        from app.routes.traduccions import _netejar_contingut
        from app.services.etiquetes_idioma import IDIOMES

        with open(fitxer, encoding='utf-8') as fh:
            registres = json.load(fh).get('traduccions', [])

        compta = {'creades': 0, 'ja_existien': 0, 'versio_canviada': 0,
                  'fitxa_no_trobada': 0, 'invalides': 0}
        avisos = []
        ara = datetime.now(timezone.utc)
        for r in registres:
            motiu = _registre_valid(r)
            if motiu:
                compta['invalides'] += 1
                avisos.append(f"{r.get('art_codi', '?') if isinstance(r, dict) else '?'}: {motiu}")
                continue
            f = FitxaTecnica.query.filter_by(art_codi=r['art_codi']).first()
            if not f or (f.tipus_producte or 'elaborat') == 'comercialitzat':
                compta['fitxa_no_trobada'] += 1
                avisos.append(f"{r['art_codi']}: fitxa no trobada o comercialitzada")
                continue
            v = VersioFitxa.query.filter_by(fitxa_id=f.id, activa=True).first()
            if not v or v.id != r['versio_id'] or v.num_versio != r['num_versio']:
                compta['versio_canviada'] += 1
                avisos.append(f"{r['art_codi']} {r['idioma']}: la versió activa ha canviat "
                              f"des de l'exportació (exportada v{r['num_versio']}"
                              f"{f', ara v{v.num_versio}' if v else ''}); no s'importa")
                continue
            if TraduccioVersio.query.filter_by(versio_id=v.id, idioma=r['idioma']).first():
                compta['ja_existien'] += 1
                continue
            t = TraduccioVersio(versio_id=v.id, idioma=r['idioma'],
                                contingut=_netejar_contingut(r['contingut']),
                                estat='pendent', origen='importada', camps_canviats=[],
                                created_at=ara, created_by=USUARI_IMPORTACIO,
                                updated_at=ara, updated_by=USUARI_IMPORTACIO)
            db.session.add(t)
            db.session.flush()
            t.desar_historial('importada', USUARI_IMPORTACIO)
            marcats = set(f.idiomes or []) | {r['idioma']}
            f.idiomes = [i for i in IDIOMES if i in marcats]
            compta['creades'] += 1

        for a in avisos[:50]:
            click.echo(f'  AVÍS {a}')
        if len(avisos) > 50:
            click.echo(f'  … i {len(avisos) - 50} avisos més')
        click.echo(', '.join(f'{k}: {v}' for k, v in compta.items()))
        if aplicar:
            db.session.commit()
            click.echo('DESAT a la base de dades.')
        else:
            db.session.rollback()
            click.echo("SIMULACIÓ: no s'ha desat res. Torna-ho a executar amb --aplicar per desar.")
