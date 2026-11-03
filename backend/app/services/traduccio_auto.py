"""Actualització automàtica de les traduccions quan es crea una versió nova.

Quan es desa una versió nova d'una fitxa amb idiomes marcats, per a cada idioma
que ja tenia traducció en una versió anterior es crea la traducció de la versió
nova:
  - els camps que no han canviat a l'original es copien de la traducció anterior;
  - els camps canviats es tornen a proposar (separant el bilingüe, copiant
    l'original si ja és en aquest idioma, o amb el proveïdor de traducció);
  - si no es poden traduir (sense proveïdor o error), conserven el text
    anterior i l'origen queda com a 'copiada';
  - la traducció queda 'pendent' de revisar, amb els camps canviats marcats.

No toca la creació de versions: un escoltador de SQLAlchemy detecta les
versions noves i, quan la transacció ja està confirmada, fa la feina en un fil
de fons (com l'enviament de correus). Si falla, la versió no se'n ressent: es
registra al log i l'editor continua oferint la traducció anterior com a base.

Desactivable amb TRADUCCIO_AUTOMATICA=0 al .env.
"""
import copy
import logging
import os
import threading

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

LOG = logging.getLogger(__name__)

USUARI_AUTO = 'actualització automàtica'
_CLAU = 'versions_noves_traduccio'
_registrat = False


def registrar(app):
    """Registra els escoltadors (un sol cop per procés)."""
    global _registrat
    if _registrat or os.environ.get('TRADUCCIO_AUTOMATICA', '1') == '0':
        return
    from app.models import VersioFitxa

    @event.listens_for(VersioFitxa, 'after_insert')
    def _versio_nova(mapper, connection, target):
        sessio = object_session(target)
        if sessio is not None:
            sessio.info.setdefault(_CLAU, set()).add(target.id)

    @event.listens_for(Session, 'after_commit')
    def _despres_commit(sessio):
        ids = sessio.info.pop(_CLAU, None)
        if ids:
            threading.Thread(target=_actualitzar_en_fons, args=(app, sorted(ids)),
                             daemon=True, name='traduccions-automatiques').start()

    @event.listens_for(Session, 'after_rollback')
    def _despres_rollback(sessio):
        sessio.info.pop(_CLAU, None)

    _registrat = True


def _actualitzar_en_fons(app, versio_ids):
    with app.app_context():
        for vid in versio_ids:
            try:
                actualitzar_versio(vid)
            except Exception:  # una fitxa amb problemes no ha d'aturar la resta
                LOG.exception('[Traduccions] Error actualitzant la versió %s', vid)
                from app import db
                db.session.rollback()


def _ordre_idiomes(idiomes, idioma_origen):
    """L'idioma d'origen primer: les traduccions automàtiques en parteixen."""
    return sorted(idiomes, key=lambda i: (i != idioma_origen, i))


def actualitzar_versio(versio_id):
    """Crea les traduccions de la versió a partir de les de la versió anterior.

    Returns:
        llista de (idioma, origen) creats (per als tests i el log).
    """
    from app import db
    from app.models import FitxaTecnica, VersioFitxa, TraduccioVersio
    from app.routes.traduccions import _traduccio_anterior, font_traduccio, idioma_original
    from app.services import traduccio as srv

    versio = db.session.get(VersioFitxa, versio_id)
    if not versio:
        return []
    fitxa = db.session.get(FitxaTecnica, versio.fitxa_id)
    if not fitxa or not fitxa.idiomes or (fitxa.tipus_producte or 'elaborat') == 'comercialitzat':
        return []

    original = idioma_original(versio)
    origen_ia = 'ca' if original == 'ca' else 'es'
    creats = []
    for idioma in _ordre_idiomes(fitxa.idiomes, origen_ia):
        if TraduccioVersio.query.filter_by(versio_id=versio.id, idioma=idioma).first():
            continue    # ja n'hi ha (l'usuari s'ha avançat)
        anterior = _traduccio_anterior(versio, idioma)
        if not anterior:
            continue    # mai no s'ha traduït: es fa a mà des de l'editor
        versio_ant = db.session.get(VersioFitxa, anterior.versio_id)
        canviats = srv.camps_canviats(versio_ant.contingut if versio_ant else {}, versio.contingut)

        contingut = copy.deepcopy(anterior.contingut or {})
        origen = 'automatica'
        if canviats:
            if original == idioma:
                proposta, error = srv.extreure_camps(versio.contingut), None
            elif original == 'bilingue' and idioma in ('ca', 'es'):
                proposta, dubtosos = srv.separar_bilingue(versio.contingut, idioma)
                error = None
                dubtosos = [c for c in dubtosos if c in canviats]
                if dubtosos and srv.ia_disponible():
                    resolts, avis = srv.separar_amb_ia(versio.contingut, idioma, dubtosos)
                    if resolts:
                        proposta.update(resolts)
                    elif avis:
                        LOG.warning('[Traduccions] %s %s v%s: separació amb IA: %s',
                                    fitxa.art_codi, idioma, versio.num_versio, avis)
            else:
                font, origen_font = font_traduccio(versio)
                proposta, error = srv.traduir_ia(font, idioma, valors_originals=versio.contingut,
                                                 idioma_origen=origen_font, camps=canviats)
            if error:
                LOG.warning('[Traduccions] %s %s v%s: no s\'han pogut traduir els camps '
                            'canviats (%s). Es conserva el text anterior.',
                            fitxa.art_codi, idioma, versio.num_versio, error)
                origen = 'copiada'
            else:
                for camp in canviats:
                    if camp in proposta:
                        contingut[camp] = proposta[camp]
                    elif not (versio.contingut or {}).get(camp):
                        contingut.pop(camp, None)   # el camp s'ha buidat a l'original

        t = TraduccioVersio(versio_id=versio.id, idioma=idioma, contingut=contingut,
                            estat='pendent', origen=origen, camps_canviats=canviats,
                            created_by=USUARI_AUTO, updated_by=USUARI_AUTO)
        db.session.add(t)
        try:
            db.session.flush()
            t.desar_historial('automatica', USUARI_AUTO)
            db.session.commit()
        except IntegrityError:
            # L'usuari l'ha creada mentrestant: es respecta la seva
            db.session.rollback()
            continue
        creats.append((idioma, origen))
        LOG.info('[Traduccions] %s v%s %s creada (%s, %d camps canviats)',
                 fitxa.art_codi, versio.num_versio, idioma, origen, len(canviats))
    return creats
