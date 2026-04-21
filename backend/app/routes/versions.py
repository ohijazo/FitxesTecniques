import os
import re
import glob
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app import db
from app.models import FitxaTecnica, VersioFitxa
from app.auth import login_required, rol_requerit


def _strip_html(text):
    """Elimina tags HTML i normalitza espais per comparar contingut."""
    if not text:
        return ''
    clean = re.sub(r'<[^>]+>', '', str(text))
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


# Mapa de claus internes a noms llegibles
CAMP_LABELS = {
    'codi_referencia': 'Código de referencia / Codi de referència',
    'certificacio': 'Certificación / Certificació',
    'denominacio_comercial': 'Denominación comercial / Denominació comercial',
    'denominacio_juridica': 'Denominación jurídica / Denominació jurídica',
    'codi_ean': 'Código EAN / Codi EAN',
    'descripcio': 'Descripción del producto / Descripció del producte',
    'origen': 'Origen del Producto / Origen del producte',
    'ingredients': 'Ingredientes / Ingredients',
    'alergens': 'Alérgenos / Al·lèrgens',
    'ogm': 'OGM',
    'irradiacio': 'Irradiación / Irradiació',
    'caract_organoleptiques': 'Características organolépticas / Característiques organolèptiques',
    'fisicoquimiques': 'Características físico-químicas / Característiques fisicoquímiques',
    'reologiques': 'Características reológicas / Característiques reològiques',
    'microbiologiques': 'Características Microbiológicas / Característiques microbiològiques',
    'micotoxines': 'Micotoxinas / Micotoxines',
    'alcaloides': 'Alcaloides del cornezuelo / Alcaloides del sègol banyut',
    'metalls_pesants': 'Metales pesados / Metalls pesants',
    'contaminants_altres': 'Otros contaminantes / Altres contaminants',
    'pesticidas': 'Pesticidas / Pesticides',
    'valors_nutricionals': 'Valores nutricionales / Valors nutricionals',
    'presentacio_envase': 'Presentación – envase / Presentació – envàs',
    'us_previst': 'Uso previsto / Ús previst',
    'condicions_emmagatzematge': "Condiciones de almacenaje / Condicions d'emmagatzematge",
    'condicions_transport': 'Condiciones de transporte / Condicions de transport',
    'vida_util': 'Vida útil del producto / Vida útil del producte',
    'legislacio_aplicable': 'Otra legislación aplicable / Altra legislació aplicable',
    'fabricat_per': 'Producto fabricado para / Producte fabricat per a',
    'vigencia_document': 'Vigencia del documento / Vigència del document',
}

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'uploads')

versions_bp = Blueprint('versions', __name__)


@versions_bp.route('/fitxes/<int:fitxa_id>/versions', methods=['GET'])
@login_required
def llistar_versions(fitxa_id):
    db.get_or_404(FitxaTecnica, fitxa_id)
    versions = VersioFitxa.query.filter_by(fitxa_id=fitxa_id)\
        .order_by(VersioFitxa.num_versio.desc()).all()
    return jsonify([v.to_dict() for v in versions])


@versions_bp.route('/fitxes/<int:fitxa_id>/versions/<int:vid>', methods=['GET'])
@login_required
def detall_versio(fitxa_id, vid):
    versio = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, id=vid).first_or_404()
    return jsonify(versio.to_dict())


@versions_bp.route('/fitxes/<int:fitxa_id>/versions', methods=['POST'])
@rol_requerit('admin', 'editor')
def crear_versio(fitxa_id):
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    data = request.get_json()

    if not data or not data.get('descripcio_canvi'):
        return jsonify({'error': "Camp obligatori: descripcio_canvi"}), 400

    ultima = VersioFitxa.query.filter_by(fitxa_id=fitxa_id)\
        .order_by(VersioFitxa.num_versio.desc()).first()
    nou_num = (ultima.num_versio + 1) if ultima else 1

    # Desactivar versió anterior
    VersioFitxa.query.filter_by(fitxa_id=fitxa_id, activa=True)\
        .update({'activa': False})

    versio = VersioFitxa(
        fitxa_id=fitxa_id,
        num_versio=nou_num,
        descripcio_canvi=data['descripcio_canvi'],
        contingut=data.get('contingut', {}),
        created_by=request.usuari.get('email', ''),
        activa=True,
        estat_versio='publicada',
    )
    db.session.add(versio)

    fitxa.estat = 'publicada'

    # Invalidar cache PDF de versions anteriors
    for cached in glob.glob(os.path.join(UPLOAD_DIR, fitxa.art_codi, '**', '*_generat.pdf'), recursive=True):
        try:
            os.remove(cached)
        except OSError:
            pass

    db.session.commit()

    return jsonify(versio.to_dict()), 201


@versions_bp.route('/fitxes/<int:fitxa_id>/versions/<int:vid>/publicar', methods=['POST'])
@rol_requerit('admin', 'editor')
def publicar_versio(fitxa_id, vid):
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    versio = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, id=vid).first_or_404()

    # Enforcar workflow: per publicar cal que estigui aprovada
    # (excepte si es restaura una versio ja publicada anteriorment)
    if versio.estat_versio not in ('aprovada', 'publicada'):
        return jsonify({
            'error': "Nomes es pot publicar una versio aprovada. "
                     f"Estat actual: {versio.estat_versio}"
        }), 400

    VersioFitxa.query.filter_by(fitxa_id=fitxa_id, activa=True)\
        .update({'activa': False})

    versio.activa = True
    versio.estat_versio = 'publicada'
    fitxa.estat = 'publicada'
    db.session.commit()

    return jsonify(versio.to_dict())


@versions_bp.route('/fitxes/<int:fitxa_id>/versions/<int:vid>/aprovar', methods=['POST'])
@rol_requerit('admin')
def aprovar_versio(fitxa_id, vid):
    """Aprova una versió (canvia estat a 'aprovada')."""
    versio = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, id=vid).first_or_404()

    versio.estat_versio = 'aprovada'
    versio.aprovat_per = request.usuari.get('email', '')
    versio.aprovat_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(versio.to_dict())


@versions_bp.route('/fitxes/<int:fitxa_id>/versions/<int:vid>/revisar', methods=['POST'])
@rol_requerit('admin', 'editor')
def enviar_revisio(fitxa_id, vid):
    """Envia una versió a revisió."""
    versio = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, id=vid).first_or_404()
    versio.estat_versio = 'en_revisio'
    db.session.commit()
    return jsonify(versio.to_dict())


@versions_bp.route('/fitxes/<int:fitxa_id>/versions/diff', methods=['GET'])
@login_required
def diff_versions(fitxa_id):
    """Compara dues versions d'una fitxa.
    Params: v1 (id versió antiga), v2 (id versió nova)
    """
    db.get_or_404(FitxaTecnica, fitxa_id)

    v1_id = request.args.get('v1', type=int)
    v2_id = request.args.get('v2', type=int)

    if not v1_id or not v2_id:
        return jsonify({'error': "Cal indicar v1 i v2"}), 400

    v1 = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, id=v1_id).first_or_404()
    v2 = VersioFitxa.query.filter_by(fitxa_id=fitxa_id, id=v2_id).first_or_404()

    c1 = v1.contingut or {}
    c2 = v2.contingut or {}

    all_keys = sorted(set(list(c1.keys()) + list(c2.keys())))
    canvis = []

    for key in all_keys:
        val1 = c1.get(key)
        val2 = c2.get(key)
        camp_label = CAMP_LABELS.get(key, key)

        if isinstance(val1, list) or isinstance(val2, list):
            rows1 = val1 if isinstance(val1, list) else []
            rows2 = val2 if isinstance(val2, list) else []

            if rows1 == rows2:
                continue

            file_canvis = []
            max_len = max(len(rows1), len(rows2))
            for i in range(max_len):
                r1 = rows1[i] if i < len(rows1) else None
                r2 = rows2[i] if i < len(rows2) else None

                if r1 is None:
                    file_canvis.append({'tipus': 'afegit', 'valor': r2})
                elif r2 is None:
                    file_canvis.append({'tipus': 'eliminat', 'valor': r1})
                elif r1 != r2:
                    file_canvis.append({'tipus': 'modificat', 'antic': r1, 'nou': r2})
                else:
                    file_canvis.append({'tipus': 'igual', 'valor': r1})

            canvis.append({
                'camp': camp_label,
                'tipus': 'taula',
                'files': file_canvis,
            })
        else:
            # Netejar HTML per comparar contingut real
            clean1 = _strip_html(val1)
            clean2 = _strip_html(val2)

            if clean1 == clean2:
                continue

            # Mostrar text net (sense tags HTML)
            if not clean1 and clean2:
                canvis.append({'camp': camp_label, 'tipus': 'afegit', 'nou': clean2})
            elif clean1 and not clean2:
                canvis.append({'camp': camp_label, 'tipus': 'eliminat', 'antic': clean1})
            else:
                canvis.append({'camp': camp_label, 'tipus': 'modificat', 'antic': clean1, 'nou': clean2})

    return jsonify({
        'v1': {'id': v1.id, 'num': v1.num_versio, 'data': v1.created_at.isoformat() if v1.created_at else '', 'autor': v1.created_by or ''},
        'v2': {'id': v2.id, 'num': v2.num_versio, 'data': v2.created_at.isoformat() if v2.created_at else '', 'autor': v2.created_by or ''},
        'total_canvis': len(canvis),
        'canvis': canvis,
    })
