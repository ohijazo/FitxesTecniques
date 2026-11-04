"""Correcció dels superíndexs perduts als valors de les taules de les fitxes.

En importar les fitxes es va perdre el format de superíndex: «< 10⁶ ufc/g» va
quedar com «< 106 ufc/g». Aquesta ordre ho corregeix a la VERSIÓ ACTIVA de
cada fitxa elaborada i a les seves traduccions.

    flask corregir-superindexs [--aplicar] [--copia FITXER]

Per defecte és una SIMULACIÓ. Amb --aplicar:
  - es corregeix el contingut de la versió activa (sense revisió nova, per
    decisió de l'usuari); a la descripció del canvi s'hi afegeix una línia que
    ho deixa registrat;
  - es corregeixen els mateixos valors a les traduccions, mantenint-ne l'estat,
    amb una entrada a l'historial (acció 'correccio');
  - s'esborren els PDF desats d'aquestes versions perquè es tornin a generar;
  - es desa una còpia de seguretat (valors abans/després) a --copia.
Les versions anteriors no es toquen.
"""
import copy
import glob
import json
import os
import re
from datetime import datetime, timezone

import click
from sqlalchemy.orm.attributes import flag_modified

USUARI_CORRECCIO = 'correcció de superíndexs'

_SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
# «10» + una xifra 1-9 just abans de la unitat (ufc/cfu) o d'una barra («/g»).
# No toca «100», «1067», «10,5», ni un número sense unitat («Màx. 106»).
_RX = re.compile(r'(?<![\d,.])10([1-9])(?=\s*(?:ufc|UFC|cfu|CFU|/))')


def corregir_valor(text):
    """'< 106 ufc/g' -> '< 10⁶ ufc/g'. Retorna el text tal qual si no hi ha res a corregir."""
    if not isinstance(text, str):
        return text
    return _RX.sub(lambda m: '10' + m.group(1).translate(_SUP), text)


def corregir_taules(contingut, camps_taula):
    """(contingut_nou, canvis) amb els valors de taula corregits."""
    nou = copy.deepcopy(contingut or {})
    canvis = []
    for camp in camps_taula:
        for i, fila in enumerate(nou.get(camp) or []):
            if isinstance(fila, dict) and fila.get('valor'):
                corregit = corregir_valor(fila['valor'])
                if corregit != fila['valor']:
                    canvis.append({'camp': camp, 'fila': i, 'abans': fila['valor'], 'despres': corregit})
                    fila['valor'] = corregit
    return nou, canvis


def registrar(app):
    @app.cli.command('corregir-superindexs')
    @click.option('--aplicar', is_flag=True, help='Desa els canvis. Sense això, només simula.')
    @click.option('--copia', default=None, help='Fitxer JSON de còpia de seguretat (per defecte a /tmp).')
    def corregir_superindexs(aplicar, copia):
        """Corregeix «< 106 ufc/g» -> «< 10⁶ ufc/g» a les versions actives (simulació per defecte)."""
        from app import db
        from app.models import FitxaTecnica, VersioFitxa, TraduccioVersio
        from app.routes.fitxes import UPLOAD_DIR
        from app.services.traduccio import CAMPS_TAULA

        ara = datetime.now(timezone.utc)
        nota = (f"[{ara:%d/%m/%Y}] Correcció automàtica de superíndexs als valors "
                f"microbiològics (p.ex. «< 106 ufc/g» → «< 10⁶ ufc/g»).")
        copia = copia or f"/tmp/superindexs_copia_{ara:%Y%m%d_%H%M%S}.json"
        registre, n_versions, n_valors, n_trad, pdfs = [], 0, 0, 0, 0

        for f in FitxaTecnica.query.order_by(FitxaTecnica.art_codi):
            if (f.tipus_producte or 'elaborat') == 'comercialitzat':
                continue
            v = VersioFitxa.query.filter_by(fitxa_id=f.id, activa=True).first()
            if not v or not v.contingut:
                continue
            nou, canvis = corregir_taules(v.contingut, CAMPS_TAULA)
            entrada = {'art_codi': f.art_codi, 'versio_id': v.id, 'num_versio': v.num_versio,
                       'canvis': canvis, 'traduccions': []}
            if canvis:
                n_versions += 1
                n_valors += len(canvis)
                if aplicar:
                    v.contingut = nou
                    flag_modified(v, 'contingut')
                    v.descripcio_canvi = (v.descripcio_canvi or '').rstrip() + '\n' + nota
                    # PDFs desats d'aquesta versió: es regeneraran amb els valors bons
                    carpeta = os.path.join(UPLOAD_DIR, f.art_codi, f'v{v.num_versio}')
                    for pdf in glob.glob(os.path.join(carpeta, f'{f.art_codi}*.pdf')):
                        try:
                            os.remove(pdf)
                            pdfs += 1
                        except OSError:
                            pass
                    if v.fitxer_pdf and not os.path.exists(v.fitxer_pdf):
                        v.fitxer_pdf = None

            for t in TraduccioVersio.query.filter_by(versio_id=v.id):
                nou_t, canvis_t = corregir_taules(t.contingut, CAMPS_TAULA)
                if not canvis_t:
                    continue
                n_trad += 1
                entrada['traduccions'].append({'idioma': t.idioma, 'canvis': canvis_t})
                if aplicar:
                    t.contingut = nou_t
                    flag_modified(t, 'contingut')
                    t.updated_at = ara
                    t.updated_by = USUARI_CORRECCIO
                    t.desar_historial('correccio', USUARI_CORRECCIO)   # l'estat es manté
            if canvis or entrada['traduccions']:
                registre.append(entrada)

        click.echo(f'Versions a corregir: {n_versions} ({n_valors} valors) | traduccions: {n_trad}')
        for e in registre[:3]:
            for c in e['canvis'][:3]:
                click.echo(f"  {e['art_codi']} v{e['num_versio']} {c['camp']}: {c['abans']!r} -> {c['despres']!r}")
        if aplicar:
            with open(copia, 'w', encoding='utf-8') as fh:
                json.dump({'data': ara.isoformat(), 'versions': registre}, fh, ensure_ascii=False, indent=1)
            db.session.commit()
            click.echo(f'DESAT. PDFs esborrats perquè es regenerin: {pdfs}. Còpia: {copia}')
        else:
            db.session.rollback()
            click.echo("SIMULACIÓ: no s'ha desat res. Torna-ho a executar amb --aplicar per desar.")
