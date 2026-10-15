"""Enviament de fitxes tecniques per correu a clients.

El correu surt de la bustia M365 de l'usuari que envia (via Microsoft Graph)
amb el PDF de la versio activa de cada fitxa adjuntat. L'enviament s'executa
en un thread de fons per no bloquejar la resposta HTTP; el frontend consulta
l'estat amb GET /enviaments/<id>.
"""

import re
import logging
import threading
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import FitxaTecnica, VersioFitxa, EnviamentEmail, EnviamentEmailItem
from app.auth import login_required, rol_requerit

LOG = logging.getLogger(__name__)

enviaments_bp = Blueprint('enviaments', __name__)

ROLS_ENVIAMENT = ('admin', 'editor', 'distribuidor')
MAX_DESTINATARIS = 20
EMAIL_RE = re.compile(r'^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$')

ASSUMPTE_DEFECTE = 'Fitxes tècniques / Fichas técnicas - Farinera Coromina'
COS_DEFECTE = (
    "Benvolguts,\n\n"
    "Us adjuntem les fitxes tècniques sol·licitades:\n\n"
    "{fitxes}\n\n"
    "Per a qualsevol dubte, no dubteu a contactar-nos.\n\n"
    "Salutacions cordials,"
)


def _plantilla():
    cfg = current_app.config
    assumpte = cfg.get('EMAIL_PLANTILLA_ASSUMPTE') or ASSUMPTE_DEFECTE
    cos = (cfg.get('EMAIL_PLANTILLA_COS') or COS_DEFECTE).replace('\\n', '\n')
    return assumpte, cos


def _config_graph():
    cfg = current_app.config
    return {
        'tenant_id': cfg.get('GRAPH_TENANT_ID'),
        'client_id': cfg.get('GRAPH_CLIENT_ID'),
        'client_secret': cfg.get('GRAPH_CLIENT_SECRET'),
    }


def _preparar_fitxes(fitxa_ids):
    """Per cada fitxa: dades i versio activa, o el motiu pel qual no es pot enviar."""
    fitxes = {f.id: f for f in FitxaTecnica.query.filter(FitxaTecnica.id.in_(fitxa_ids)).all()}
    resultat = []
    for fid in fitxa_ids:
        fitxa = fitxes.get(fid)
        if not fitxa:
            resultat.append({'fitxa_id': fid, 'enviable': False, 'motiu': 'Fitxa no trobada'})
            continue
        versio = VersioFitxa.query.filter_by(fitxa_id=fitxa.id, activa=True).first()
        item = {
            'fitxa_id': fitxa.id,
            'art_codi': fitxa.art_codi,
            'nom_producte': fitxa.nom_producte,
            'enviable': versio is not None,
            'motiu': None if versio else 'No té cap versió publicada',
            'versio_id': versio.id if versio else None,
            'num_versio': versio.num_versio if versio else None,
            'nom_fitxer': f'{fitxa.art_codi}.pdf',
        }
        resultat.append(item)
    return resultat


def _llista_adreces(valor):
    """Accepta llista o text separat per comes / punt i coma. Retorna (adreces, invalides)."""
    if isinstance(valor, str):
        valor = re.split(r'[,;\s]+', valor)
    adreces, invalides = [], []
    for a in valor or []:
        a = (a or '').strip()
        if not a:
            continue
        (adreces if EMAIL_RE.match(a) else invalides).append(a)
    # Treure duplicats conservant l'ordre
    vistos = set()
    adreces = [a for a in adreces if not (a.lower() in vistos or vistos.add(a.lower()))]
    return adreces, invalides


def _executar_enviament(app, enviament_id, config_graph):
    """Thread de fons: genera/recupera els PDFs i envia el correu."""
    from app.routes.distribucions import _assegurar_pdf
    from app.services.email_sender import enviar_correu

    with app.app_context():
        env = None
        try:
            env = db.session.get(EnviamentEmail, enviament_id)
            adjunts = []
            for item in env.items:
                fitxa = db.session.get(FitxaTecnica, item.fitxa_id)
                versio = db.session.get(VersioFitxa, item.versio_id)
                if not fitxa or not versio:
                    raise RuntimeError(f"La fitxa {item.art_codi} ja no existeix")
                # Mateix PDF que es distribueix als destins
                adjunts.append((_assegurar_pdf(fitxa, versio), item.nom_fitxer))
            # _assegurar_pdf pot haver desat la ruta d'un PDF generat
            db.session.commit()

            per_a = [a for a in env.per_a.split(', ') if a]
            cc = [a for a in (env.cc or '').split(', ') if a]
            ok, err = enviar_correu(config_graph, env.remitent, per_a, cc,
                                    env.assumpte, env.cos or '', adjunts)
            env.estat = 'ok' if ok else 'error'
            env.missatge_error = err
        except Exception as e:
            LOG.exception('[EMAIL] Error a l\'enviament %s', enviament_id)
            db.session.rollback()
            env = db.session.get(EnviamentEmail, enviament_id)
            if env is None:
                return
            env.estat = 'error'
            env.missatge_error = f"Error preparant l'enviament: {e}"
        env.executat_at = datetime.now(timezone.utc)
        db.session.commit()


@enviaments_bp.route('/enviaments/plantilla', methods=['GET'])
@rol_requerit(*ROLS_ENVIAMENT)
def plantilla():
    assumpte, cos = _plantilla()
    cfg = _config_graph()
    return jsonify({
        'assumpte': assumpte,
        'cos': cos,
        'remitent': request.usuari.get('email'),
        'configurat': all(cfg.values()),
        'max_adjunts': current_app.config.get('EMAIL_MAX_ADJUNTS', 30),
    }), 200


@enviaments_bp.route('/enviaments/preparar', methods=['POST'])
@rol_requerit(*ROLS_ENVIAMENT)
def preparar():
    data = request.get_json(silent=True) or {}
    ids = [i for i in (data.get('fitxa_ids') or []) if isinstance(i, int)]
    return jsonify({'fitxes': _preparar_fitxes(ids)}), 200


@enviaments_bp.route('/enviaments', methods=['POST'])
@rol_requerit(*ROLS_ENVIAMENT)
def crear_enviament():
    data = request.get_json(silent=True) or {}
    ids = list(dict.fromkeys(i for i in (data.get('fitxa_ids') or []) if isinstance(i, int)))
    per_a, inv_per_a = _llista_adreces(data.get('per_a'))
    cc, inv_cc = _llista_adreces(data.get('cc'))
    assumpte = (data.get('assumpte') or '').strip()
    cos = data.get('cos') or ''

    invalides = inv_per_a + inv_cc
    if invalides:
        return jsonify({'error': f"Adreces no vàlides: {', '.join(invalides)}"}), 400
    if not per_a:
        return jsonify({'error': "Cal indicar almenys un destinatari"}), 400
    if len(per_a) + len(cc) > MAX_DESTINATARIS:
        return jsonify({'error': f"Màxim {MAX_DESTINATARIS} destinataris per enviament"}), 400
    if not assumpte:
        return jsonify({'error': "Cal indicar l'assumpte"}), 400
    if len(assumpte) > 500:
        return jsonify({'error': "L'assumpte és massa llarg"}), 400
    if not ids:
        return jsonify({'error': "No hi ha cap fitxa seleccionada"}), 400
    max_adj = current_app.config.get('EMAIL_MAX_ADJUNTS', 30)
    if len(ids) > max_adj:
        return jsonify({'error': f"Màxim {max_adj} fitxes per correu"}), 400

    cfg = _config_graph()
    if not all(cfg.values()):
        return jsonify({'error': "L'enviament per correu no està configurat al servidor. Avisa l'administrador."}), 400

    remitent = request.usuari.get('email')
    if not remitent:
        return jsonify({'error': "El teu usuari no té adreça de correu"}), 400

    fitxes = _preparar_fitxes(ids)
    no_enviables = [f for f in fitxes if not f['enviable']]
    if no_enviables:
        llista = ', '.join(f"{f.get('art_codi', f['fitxa_id'])} ({f['motiu']})" for f in no_enviables)
        return jsonify({'error': f"No es poden enviar: {llista}"}), 400

    env = EnviamentEmail(
        remitent=remitent,
        per_a=', '.join(per_a),
        cc=', '.join(cc) or None,
        assumpte=assumpte,
        cos=cos,
        estat='pendent',
        created_by=remitent,
    )
    db.session.add(env)
    db.session.flush()
    for f in fitxes:
        db.session.add(EnviamentEmailItem(
            enviament_id=env.id,
            fitxa_id=f['fitxa_id'],
            versio_id=f['versio_id'],
            art_codi=f['art_codi'],
            num_versio=f['num_versio'],
            nom_fitxer=f['nom_fitxer'],
        ))
    db.session.commit()

    app = current_app._get_current_object()
    threading.Thread(target=_executar_enviament, args=(app, env.id, cfg),
                     daemon=True, name=f'enviament-email-{env.id}').start()

    return jsonify(env.to_dict()), 202


@enviaments_bp.route('/enviaments/<int:enviament_id>', methods=['GET'])
@login_required
def detall_enviament(enviament_id):
    env = db.session.get(EnviamentEmail, enviament_id)
    if not env:
        return jsonify({'error': 'Enviament no trobat'}), 404
    return jsonify(env.to_dict()), 200


@enviaments_bp.route('/enviaments', methods=['GET'])
@login_required
def llistar_enviaments():
    """Historial d'enviaments; amb ?fitxa_id= nomes els que inclouen aquesta fitxa."""
    query = EnviamentEmail.query
    fitxa_id = request.args.get('fitxa_id', type=int)
    if fitxa_id:
        query = query.join(EnviamentEmailItem).filter(EnviamentEmailItem.fitxa_id == fitxa_id)
    envs = query.order_by(EnviamentEmail.created_at.desc()).limit(100).all()
    return jsonify([e.to_dict() for e in envs]), 200
