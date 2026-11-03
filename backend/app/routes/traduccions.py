"""Idiomes de les fitxes i traduccions per versió.

- Qualitat marca a cada fitxa en quins idiomes ha d'estar disponible
  (fitxa_tecnica.idiomes).
- Cada versió pot tenir una traducció per idioma (traduccio_versio). És una
  capa a part: mai no modifica versio_fitxa.contingut (versions immutables) i
  corregir-la no crea una revisió nova.
- Les propostes (separar el bilingüe o IA) no s'escriuen a la BD: les desa
  l'usuari des de l'editor després de revisar-les.
"""
import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, send_file, current_app
from app import db
from app.models import FitxaTecnica, VersioFitxa, TraduccioVersio, TraduccioHistorial
from app.auth import login_required, rol_requerit
from app.services.etiquetes_idioma import IDIOMES, NOMS_IDIOMA
from app.services import traduccio as srv

traduccions_bp = Blueprint('traduccions', __name__)

ROLS_EDICIO = ('admin', 'editor')
ORIGENS = ('separat', 'ia', 'manual', 'copiada', 'automatica')
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'uploads')


def _versio_activa(fitxa_id):
    versio = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, activa=True).first()
    if not versio:
        versio = VersioFitxa.query.filter_by(fitxa_id=fitxa_id)\
            .order_by(VersioFitxa.num_versio.desc()).first()
    return versio


def _es_comercialitzat(fitxa):
    return (fitxa.tipus_producte or 'elaborat') == 'comercialitzat'


def _idioma_valid(idioma):
    return idioma in IDIOMES


def _cache_pdf(fitxa, versio, idioma):
    """Mateix lloc i patró que el PDF principal (…_generat.pdf), així les
    invalidacions de memòria cau que ja existeixen també l'esborren."""
    return os.path.join(UPLOAD_DIR, fitxa.art_codi, f'v{versio.num_versio}',
                        f'{fitxa.art_codi}_{idioma.upper()}_generat.pdf')


def _invalidar_pdf(fitxa, versio, idioma):
    try:
        os.remove(_cache_pdf(fitxa, versio, idioma))
    except OSError:
        pass


def _traduccio_anterior(versio, idioma):
    """Traducció més recent d'una versió anterior de la mateixa fitxa."""
    return TraduccioVersio.query.join(VersioFitxa, TraduccioVersio.versio_id == VersioFitxa.id)\
        .filter(VersioFitxa.fitxa_id == versio.fitxa_id,
                VersioFitxa.num_versio < versio.num_versio,
                TraduccioVersio.idioma == idioma)\
        .order_by(VersioFitxa.num_versio.desc()).first()


def _estat_idioma(versio, idioma):
    """'revisada' | 'pendent' | 'desactualitzada' | 'falta'."""
    t = TraduccioVersio.query.filter_by(versio_id=versio.id, idioma=idioma).first()
    if t:
        return t.estat, t
    if _traduccio_anterior(versio, idioma):
        return 'desactualitzada', None
    return 'falta', None


# ------------------------------------------------------------------
# Resum i marques d'idioma
# ------------------------------------------------------------------
@traduccions_bp.route('/fitxes/<int:fitxa_id>/traduccions', methods=['GET'])
@login_required
def resum_traduccions(fitxa_id):
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    versio = _versio_activa(fitxa_id)
    idiomes = []
    for idioma in IDIOMES:
        estat, t = _estat_idioma(versio, idioma) if versio else ('falta', None)
        idiomes.append({
            'idioma': idioma,
            'nom': NOMS_IDIOMA[idioma],
            'marcat': idioma in (fitxa.idiomes or []),
            'estat': estat,
            'traduccio': t.to_dict(include_contingut=False) if t else None,
        })
    return jsonify({
        'fitxa_id': fitxa.id,
        'idiomes_marcats': fitxa.idiomes or [],
        'comercialitzat': _es_comercialitzat(fitxa),
        'ia_disponible': srv.ia_disponible(),
        'versio': {'id': versio.id, 'num_versio': versio.num_versio} if versio else None,
        'idiomes': idiomes,
    })


@traduccions_bp.route('/fitxes/<int:fitxa_id>/idiomes', methods=['PUT'])
@rol_requerit(*ROLS_EDICIO)
def marcar_idiomes(fitxa_id):
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    data = request.get_json() or {}
    idiomes = data.get('idiomes')
    if not isinstance(idiomes, list) or any(not _idioma_valid(i) for i in idiomes):
        return jsonify({'error': f"Idiomes vàlids: {', '.join(IDIOMES)}"}), 400
    if idiomes and _es_comercialitzat(fitxa):
        return jsonify({'error': "Les fitxes de producte comercialitzat no es poden traduir: el seu PDF és un fitxer pujat"}), 400
    # Ordre fix i sense repetits
    fitxa.idiomes = [i for i in IDIOMES if i in idiomes]
    fitxa.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'idiomes': fitxa.idiomes})


# ------------------------------------------------------------------
# Traducció d'una versió
# ------------------------------------------------------------------
def _carregar(fitxa_id, vid, idioma):
    """Retorna (fitxa, versio, error_response)."""
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    versio = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, id=vid).first_or_404()
    if not _idioma_valid(idioma):
        return fitxa, versio, (jsonify({'error': f"Idioma no vàlid: {idioma}"}), 400)
    if _es_comercialitzat(fitxa):
        return fitxa, versio, (jsonify({'error': "Les fitxes de producte comercialitzat no es tradueixen"}), 400)
    return fitxa, versio, None


@traduccions_bp.route('/fitxes/<int:fitxa_id>/versions/<int:vid>/traduccions/<idioma>', methods=['GET'])
@login_required
def llegir_traduccio(fitxa_id, vid, idioma):
    fitxa, versio, err = _carregar(fitxa_id, vid, idioma)
    if err:
        return err
    t = TraduccioVersio.query.filter_by(versio_id=versio.id, idioma=idioma).first()

    # Sense traducció per a aquesta versió: proposar la de la versió anterior,
    # amb els camps on el text original ha canviat des d'aleshores.
    base = None
    if not t:
        anterior = _traduccio_anterior(versio, idioma)
        if anterior:
            versio_ant = db.session.get(VersioFitxa, anterior.versio_id)
            base = {
                'contingut': anterior.contingut or {},
                'des_de_versio': versio_ant.num_versio if versio_ant else None,
                'camps_canviats': srv.camps_canviats(
                    versio_ant.contingut if versio_ant else {}, versio.contingut),
            }

    return jsonify({
        'idioma': idioma,
        'nom_idioma': NOMS_IDIOMA[idioma],
        'versio': {'id': versio.id, 'num_versio': versio.num_versio, 'activa': versio.activa},
        'original': versio.contingut or {},
        'camps_traduibles': {
            'text': list(srv.CAMPS_TEXT),
            'nota': list(srv.CAMPS_NOTA),
            'taula': list(srv.CAMPS_TAULA),
        },
        'traduccio': t.to_dict() if t else None,
        'base': base,
        'ia_disponible': srv.ia_disponible(),
        # 'bilingue' | 'es' | 'ca': decideix si es pot separar o cal traduir
        'idioma_original': idioma_original(versio),
    })


def idioma_original(versio):
    """Idioma en què està escrit el contingut de la versió: 'bilingue', 'es' o 'ca'."""
    return (versio.contingut or {}).get('_idioma') or 'bilingue'


def font_traduccio(versio):
    """(camps_font, idioma_origen) per traduir automàticament aquesta versió.

    - Original només en català: el català (la traducció CA si n'hi ha; si no,
      el text de l'original tal qual).
    - Original bilingüe o en castellà: el castellà (la traducció ES si n'hi ha;
      si no, la part castellana del bilingüe o el text tal qual).
    """
    contingut = versio.contingut or {}
    original = idioma_original(versio)
    origen = 'ca' if original == 'ca' else 'es'
    t = TraduccioVersio.query.filter_by(versio_id=versio.id, idioma=origen).first()
    if t:
        return t.contingut or {}, origen
    if original == 'bilingue':
        font, _ = srv.separar_bilingue(contingut, 'es')
        return font, 'es'
    return srv.extreure_camps(contingut), origen


def _netejar_contingut(contingut):
    """Només es desen els camps traduïbles."""
    net = {}
    for camp in srv.CAMPS_TEXT + srv.CAMPS_NOTA:
        if isinstance(contingut.get(camp), str):
            net[camp] = contingut[camp]
    for camp in srv.CAMPS_TAULA:
        files = contingut.get(camp)
        if isinstance(files, list):
            net[camp] = [
                {k: str(f[k]) for k in ('parametre', 'valor') if isinstance(f, dict) and f.get(k)}
                for f in files
            ]
    return net


@traduccions_bp.route('/fitxes/<int:fitxa_id>/versions/<int:vid>/traduccions/<idioma>', methods=['PUT'])
@rol_requerit(*ROLS_EDICIO)
def desar_traduccio(fitxa_id, vid, idioma):
    fitxa, versio, err = _carregar(fitxa_id, vid, idioma)
    if err:
        return err
    data = request.get_json() or {}
    if not isinstance(data.get('contingut'), dict):
        return jsonify({'error': "Falta el contingut de la traducció"}), 400
    origen = data.get('origen') if data.get('origen') in ORIGENS else 'manual'
    canviats = data.get('camps_canviats')
    canviats = [c for c in canviats if c in srv.CAMPS_TRADUIBLES] if isinstance(canviats, list) else []

    usuari = request.usuari.get('email', '')
    ara = datetime.now(timezone.utc)
    t = TraduccioVersio.query.filter_by(versio_id=versio.id, idioma=idioma).first()
    if not t:
        t = TraduccioVersio(versio_id=versio.id, idioma=idioma,
                            created_at=ara, created_by=usuari)
        db.session.add(t)
    t.contingut = _netejar_contingut(data['contingut'])
    t.origen = origen
    t.camps_canviats = canviats
    # Qualsevol canvi torna a demanar revisió
    t.estat = 'pendent'
    t.revisat_at = None
    t.revisat_by = None
    t.updated_at = ara
    t.updated_by = usuari
    db.session.flush()
    t.desar_historial('desada', usuari)
    db.session.commit()
    _invalidar_pdf(fitxa, versio, idioma)
    return jsonify(t.to_dict())


@traduccions_bp.route('/fitxes/<int:fitxa_id>/versions/<int:vid>/traduccions/<idioma>/revisar', methods=['POST'])
@rol_requerit(*ROLS_EDICIO)
def revisar_traduccio(fitxa_id, vid, idioma):
    fitxa, versio, err = _carregar(fitxa_id, vid, idioma)
    if err:
        return err
    t = TraduccioVersio.query.filter_by(versio_id=versio.id, idioma=idioma).first()
    if not t:
        return jsonify({'error': "Primer cal desar la traducció"}), 400
    t.estat = 'revisada'
    t.camps_canviats = []
    t.revisat_at = datetime.now(timezone.utc)
    t.revisat_by = request.usuari.get('email', '')
    t.desar_historial('revisada', t.revisat_by)
    db.session.commit()
    _invalidar_pdf(fitxa, versio, idioma)
    return jsonify(t.to_dict())


@traduccions_bp.route('/fitxes/<int:fitxa_id>/versions/<int:vid>/traduccions/<idioma>/proposta', methods=['POST'])
@rol_requerit(*ROLS_EDICIO)
def proposta_traduccio(fitxa_id, vid, idioma):
    """Proposta automàtica. NO es desa: la revisa i desa l'usuari."""
    fitxa, versio, err = _carregar(fitxa_id, vid, idioma)
    if err:
        return err
    metode = (request.get_json() or {}).get('metode')
    contingut = versio.contingut or {}

    if metode == 'separar':
        if idioma not in ('es', 'ca'):
            return jsonify({'error': "Separar el bilingüe només serveix per al català i el castellà"}), 400
        original = idioma_original(versio)
        if original == idioma:
            # L'original ja és en aquest idioma: es copia tal qual
            return jsonify({'proposta': srv.extreure_camps(contingut), 'dubtosos': [], 'origen': 'separat'})
        if original != 'bilingue':
            return jsonify({'error': "L'original no és bilingüe: aquest idioma s'ha de traduir"}), 400
        proposta, dubtosos = srv.separar_bilingue(contingut, idioma)
        return jsonify({'proposta': proposta, 'dubtosos': dubtosos, 'origen': 'separat'})

    if metode == 'ia':
        font, idioma_origen = font_traduccio(versio)
        proposta, error = srv.traduir_ia(font, idioma, valors_originals=contingut,
                                         idioma_origen=idioma_origen)
        if error:
            current_app.logger.warning('Traducció IA %s %s: %s', fitxa.art_codi, idioma, error)
            # Error del servei extern: missatge clar, no un 500 genèric
            return jsonify({'error': error}), 502
        return jsonify({'proposta': proposta, 'dubtosos': [], 'origen': 'ia'})

    return jsonify({'error': "metode ha de ser 'separar' o 'ia'"}), 400


# ------------------------------------------------------------------
# PDF per idioma
# ------------------------------------------------------------------
@traduccions_bp.route('/fitxes/<int:fitxa_id>/pdf/<idioma>', methods=['GET'])
@login_required
def pdf_idioma(fitxa_id, idioma):
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    if not _idioma_valid(idioma):
        return jsonify({'error': f"Idioma no vàlid: {idioma}"}), 400
    vid = request.args.get('versio_id', None, type=int)
    versio = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, id=vid).first_or_404() \
        if vid else _versio_activa(fitxa_id)
    if not versio:
        return jsonify({'error': "No hi ha versions"}), 404
    t = TraduccioVersio.query.filter_by(versio_id=versio.id, idioma=idioma).first()
    if not t:
        return jsonify({'error': f"La versió {versio.num_versio} no té traducció ({NOMS_IDIOMA[idioma]})"}), 404

    cache_path = _cache_pdf(fitxa, versio, idioma)
    regen = request.args.get('regen') == '1'
    # Igual que el PDF principal: regenerar si la plantilla o el generador són més nous
    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        for src in (os.path.join(current_app.root_path, 'templates', 'fitxa_tecnica.html'),
                    os.path.join(current_app.root_path, 'services', 'pdf_generator.py'),
                    os.path.join(current_app.root_path, 'services', 'etiquetes_idioma.py')):
            if os.path.exists(src) and os.path.getmtime(src) > mtime:
                regen = True
                break
    if regen and os.path.exists(cache_path):
        os.remove(cache_path)

    if not os.path.exists(cache_path):
        pdf_bytes = _generar_pdf_traduccio(fitxa, versio, t.contingut, idioma)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'wb') as f:
            f.write(pdf_bytes)

    return send_file(cache_path, mimetype='application/pdf', as_attachment=False,
                     download_name=f'{fitxa.art_codi}_{idioma.upper()}.pdf')


def _generar_pdf_traduccio(fitxa, versio, contingut_traduccio, idioma):
    from app.services.pdf_generator import generar_pdf
    contingut = srv.combinar(versio.contingut, contingut_traduccio, idioma)
    contingut.setdefault('codi_referencia', fitxa.art_codi)
    contingut.setdefault('denominacio_comercial', fitxa.nom_producte)
    data_comp = versio.data_comprovacio.strftime('%d/%m/%Y') if versio.data_comprovacio else ''
    if versio.data_revisio:
        data_rev = versio.data_revisio.strftime('%d/%m/%Y')
    elif versio.created_at:
        data_rev = versio.created_at.strftime('%d/%m/%Y')
    else:
        data_rev = ''
    return generar_pdf(contingut, versio.num_versio, data_rev, data_comp)


# ------------------------------------------------------------------
# Historial de traduccions (només lectura)
# ------------------------------------------------------------------
@traduccions_bp.route('/fitxes/<int:fitxa_id>/traduccions/<idioma>/historial', methods=['GET'])
@login_required
def historial_traduccio(fitxa_id, idioma):
    """Totes les còpies d'aquest idioma, de totes les versions de la fitxa."""
    db.get_or_404(FitxaTecnica, fitxa_id)
    if not _idioma_valid(idioma):
        return jsonify({'error': f"Idioma no vàlid: {idioma}"}), 400
    versions = {v.id: v.num_versio for v in VersioFitxa.query.filter_by(fitxa_id=fitxa_id)}
    registres = TraduccioHistorial.query.filter(
        TraduccioHistorial.versio_id.in_(list(versions) or [0]),
        TraduccioHistorial.idioma == idioma,
    ).order_by(TraduccioHistorial.id.desc()).all()
    # On s'ha enviat cada còpia (distribucions i correus)
    from app.models import Distribucio, EnviamentEmailItem, EnviamentEmail
    ids = [h.id for h in registres] or [0]
    enviat = {}
    for d in Distribucio.query.filter(Distribucio.traduccio_historial_id.in_(ids),
                                      Distribucio.estat == 'ok'):
        enviat.setdefault(d.traduccio_historial_id, []).append(
            {'tipus': 'distribucio', 'desti': d.desti,
             'data': d.executat_at.isoformat() if d.executat_at else None})
    for it, env in db.session.query(EnviamentEmailItem, EnviamentEmail).join(
            EnviamentEmail, EnviamentEmail.id == EnviamentEmailItem.enviament_id).filter(
            EnviamentEmailItem.traduccio_historial_id.in_(ids), EnviamentEmail.estat == 'ok'):
        enviat.setdefault(it.traduccio_historial_id, []).append(
            {'tipus': 'correu', 'desti': env.per_a,
             'data': env.executat_at.isoformat() if env.executat_at else None})
    resultat = []
    for h in registres:
        d = h.to_dict()
        d['num_versio'] = versions.get(h.versio_id)
        d['enviat'] = enviat.get(h.id, [])
        resultat.append(d)
    return jsonify(resultat)


def _carregar_copia(fitxa_id, hid):
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    h = db.get_or_404(TraduccioHistorial, hid)
    versio = db.session.get(VersioFitxa, h.versio_id)
    if not versio or versio.fitxa_id != fitxa.id:
        return fitxa, None, None
    return fitxa, h, versio


@traduccions_bp.route('/fitxes/<int:fitxa_id>/traduccions/historial/<int:hid>', methods=['GET'])
@login_required
def copia_traduccio(fitxa_id, hid):
    fitxa, h, versio = _carregar_copia(fitxa_id, hid)
    if not h:
        return jsonify({'error': "Aquesta còpia no és d'aquesta fitxa"}), 404
    d = h.to_dict(include_contingut=True)
    d['num_versio'] = versio.num_versio
    return jsonify(d)


@traduccions_bp.route('/fitxes/<int:fitxa_id>/traduccions/historial/<int:hid>/pdf', methods=['GET'])
@login_required
def pdf_copia_traduccio(fitxa_id, hid):
    """PDF tal com era aquesta còpia (no es desa en memòria cau)."""
    import io
    fitxa, h, versio = _carregar_copia(fitxa_id, hid)
    if not h:
        return jsonify({'error': "Aquesta còpia no és d'aquesta fitxa"}), 404
    pdf_bytes = _generar_pdf_traduccio(fitxa, versio, h.contingut, h.idioma)
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=False,
                     download_name=f'{fitxa.art_codi}_{h.idioma.upper()}_historial_{h.id}.pdf')
