import re
from flask import Blueprint, request, jsonify
from app import db
from app.models import CampFitxa, SeccioFitxa, TipusFitxa, DestiDistribucio
from app.auth import login_required, rol_requerit

admin_bp = Blueprint('admin', __name__)


def _slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[àáâã]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõ]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


# --- Tipus de fitxa ---

@admin_bp.route('/admin/tipus', methods=['GET'])
@login_required
def llistar_tipus():
    tipus = TipusFitxa.query.order_by(TipusFitxa.nom).all()
    return jsonify([t.to_dict() for t in tipus])


@admin_bp.route('/admin/tipus/<int:tid>', methods=['GET'])
@login_required
def detall_tipus(tid):
    tipus = db.get_or_404(TipusFitxa, tid)
    return jsonify(tipus.to_dict(include_seccions=True))


@admin_bp.route('/admin/tipus', methods=['POST'])
@rol_requerit('admin')
def crear_tipus():
    data = request.get_json()
    if not data or not data.get('nom'):
        return jsonify({'error': "Camp obligatori: nom"}), 400

    slug = data.get('slug') or _slugify(data['nom'])
    if TipusFitxa.query.filter_by(slug=slug).first():
        return jsonify({'error': f"Ja existeix un tipus amb slug '{slug}'"}), 409

    tipus = TipusFitxa(
        nom=data['nom'],
        slug=slug,
        descripcio=data.get('descripcio', ''),
    )
    db.session.add(tipus)
    db.session.commit()
    return jsonify(tipus.to_dict()), 201


@admin_bp.route('/admin/tipus/<int:tid>', methods=['PUT'])
@rol_requerit('admin')
def editar_tipus(tid):
    tipus = db.get_or_404(TipusFitxa, tid)
    data = request.get_json()
    if 'nom' in data:
        tipus.nom = data['nom']
    if 'descripcio' in data:
        tipus.descripcio = data['descripcio']
    if 'actiu' in data:
        tipus.actiu = data['actiu']
    db.session.commit()
    return jsonify(tipus.to_dict())


@admin_bp.route('/admin/tipus/<int:tid>', methods=['DELETE'])
@rol_requerit('admin')
def eliminar_tipus(tid):
    from app.models import FitxaTecnica
    tipus = db.get_or_404(TipusFitxa, tid)
    if FitxaTecnica.query.filter_by(tipus_id=tid).count() > 0:
        return jsonify({'error': "No es pot eliminar: hi ha fitxes associades a aquest tipus"}), 409
    db.session.delete(tipus)
    db.session.commit()
    return jsonify({'message': 'Tipus eliminat'})


@admin_bp.route('/admin/tipus/<int:tid>/duplicar', methods=['POST'])
@rol_requerit('admin')
def duplicar_tipus(tid):
    """Duplica un tipus amb totes les seves seccions i camps."""
    original = db.get_or_404(TipusFitxa, tid)
    data = request.get_json() or {}
    nom_nou = data.get('nom', f"{original.nom} (còpia)")
    slug_nou = _slugify(nom_nou)

    # Assegurar slug únic
    base_slug = slug_nou
    counter = 1
    while TipusFitxa.query.filter_by(slug=slug_nou).first():
        slug_nou = f"{base_slug}_{counter}"
        counter += 1

    nou_tipus = TipusFitxa(nom=nom_nou, slug=slug_nou, descripcio=original.descripcio)
    db.session.add(nou_tipus)
    db.session.flush()

    for seccio in original.seccions.order_by(SeccioFitxa.ordre):
        nova_seccio = SeccioFitxa(
            tipus_id=nou_tipus.id,
            titol=seccio.titol,
            ordre=seccio.ordre,
        )
        db.session.add(nova_seccio)
        db.session.flush()

        for camp in seccio.camps:
            nou_camp = CampFitxa(
                seccio_id=nova_seccio.id,
                nom=camp.nom,
                label=camp.label,
                tipus=camp.tipus,
                obligatori=camp.obligatori,
                ordre=camp.ordre,
                opcions=camp.opcions,
                valor_defecte=camp.valor_defecte,
            )
            db.session.add(nou_camp)

    db.session.commit()
    return jsonify(nou_tipus.to_dict(include_seccions=True)), 201


# --- Seccions ---

@admin_bp.route('/admin/seccions', methods=['GET'])
@login_required
def llistar_seccions():
    tipus_id = request.args.get('tipus_id', None, type=int)
    query = SeccioFitxa.query
    if tipus_id:
        query = query.filter_by(tipus_id=tipus_id)
    seccions = query.order_by(SeccioFitxa.ordre).all()
    return jsonify([s.to_dict(include_camps=True) for s in seccions])


@admin_bp.route('/admin/seccions', methods=['POST'])
@rol_requerit('admin')
def crear_seccio():
    data = request.get_json()
    if not data or not data.get('titol'):
        return jsonify({'error': "Camp obligatori: titol"}), 400

    tipus_id = data.get('tipus_id')
    max_ordre = db.session.query(db.func.max(SeccioFitxa.ordre))\
        .filter_by(tipus_id=tipus_id).scalar() or 0
    seccio = SeccioFitxa(
        tipus_id=tipus_id,
        titol=data['titol'],
        ordre=data.get('ordre', max_ordre + 1),
    )
    db.session.add(seccio)
    db.session.commit()
    return jsonify(seccio.to_dict()), 201


@admin_bp.route('/admin/seccions/<int:sid>', methods=['PUT'])
@rol_requerit('admin')
def editar_seccio(sid):
    seccio = db.get_or_404(SeccioFitxa, sid)
    data = request.get_json()
    if 'titol' in data:
        seccio.titol = data['titol']
    if 'ordre' in data:
        seccio.ordre = data['ordre']
    db.session.commit()
    return jsonify(seccio.to_dict())


@admin_bp.route('/admin/seccions/<int:sid>', methods=['DELETE'])
@rol_requerit('admin')
def eliminar_seccio(sid):
    seccio = db.get_or_404(SeccioFitxa, sid)
    db.session.delete(seccio)
    db.session.commit()
    return jsonify({'message': 'Seccio eliminada'})


@admin_bp.route('/admin/seccions/reorder', methods=['PUT'])
@rol_requerit('admin')
def reordenar_seccions():
    data = request.get_json()
    for item in data.get('ordre', []):
        seccio = SeccioFitxa.query.get(item['id'])
        if seccio:
            seccio.ordre = item['ordre']
    db.session.commit()
    return jsonify({'message': 'Ordre actualitzat'})


# --- Camps ---

@admin_bp.route('/admin/seccions/<int:sid>/camps', methods=['GET'])
@login_required
def llistar_camps_seccio(sid):
    db.get_or_404(SeccioFitxa, sid)
    camps = CampFitxa.query.filter_by(seccio_id=sid).order_by(CampFitxa.ordre).all()
    return jsonify([c.to_dict() for c in camps])


@admin_bp.route('/admin/seccions/<int:sid>/camps', methods=['POST'])
@rol_requerit('admin')
def crear_camp_seccio(sid):
    db.get_or_404(SeccioFitxa, sid)
    data = request.get_json()
    if not data or not data.get('nom') or not data.get('label'):
        return jsonify({'error': "Camps obligatoris: nom, label"}), 400

    max_ordre = db.session.query(db.func.max(CampFitxa.ordre)).filter_by(seccio_id=sid).scalar() or 0
    camp = CampFitxa(
        seccio_id=sid,
        nom=data['nom'],
        label=data['label'],
        tipus=data.get('tipus', 'text'),
        obligatori=data.get('obligatori', False),
        ordre=data.get('ordre', max_ordre + 1),
        opcions=data.get('opcions'),
        valor_defecte=data.get('valor_defecte', ''),
    )
    db.session.add(camp)
    db.session.commit()
    return jsonify(camp.to_dict()), 201


@admin_bp.route('/admin/camps', methods=['GET'])
@login_required
def llistar_camps():
    categoria = request.args.get('categoria', None)
    query = CampFitxa.query
    if categoria:
        query = query.filter_by(categoria=categoria)
    camps = query.order_by(CampFitxa.ordre).all()
    return jsonify([c.to_dict() for c in camps])


@admin_bp.route('/admin/camps/<int:camp_id>', methods=['PUT'])
@rol_requerit('admin')
def editar_camp(camp_id):
    camp = db.get_or_404(CampFitxa, camp_id)
    data = request.get_json()

    for attr in ('nom', 'label', 'tipus', 'obligatori', 'ordre', 'opcions', 'valor_defecte', 'seccio_id'):
        if attr in data:
            setattr(camp, attr, data[attr])

    db.session.commit()
    return jsonify(camp.to_dict())


@admin_bp.route('/admin/camps/<int:camp_id>', methods=['DELETE'])
@rol_requerit('admin')
def eliminar_camp(camp_id):
    camp = db.get_or_404(CampFitxa, camp_id)
    db.session.delete(camp)
    db.session.commit()
    return jsonify({'message': 'Camp eliminat'}), 200


@admin_bp.route('/admin/seccions/<int:sid>/camps/reorder', methods=['PUT'])
@rol_requerit('admin')
def reordenar_camps(sid):
    data = request.get_json()
    for item in data.get('ordre', []):
        camp = CampFitxa.query.get(item['id'])
        if camp and camp.seccio_id == sid:
            camp.ordre = item['ordre']
    db.session.commit()
    return jsonify({'message': 'Ordre actualitzat'})


# --- Destins de distribucio ---

@admin_bp.route('/admin/destins', methods=['GET'])
@rol_requerit('admin')
def llistar_destins():
    destins = DestiDistribucio.query.order_by(DestiDistribucio.nom).all()
    return jsonify([d.to_dict(include_config=True) for d in destins])


@admin_bp.route('/admin/destins', methods=['POST'])
@rol_requerit('admin')
def crear_desti():
    data = request.get_json()
    if not data or not data.get('nom') or not data.get('tipus'):
        return jsonify({'error': "Camps obligatoris: nom, tipus"}), 400

    if data['tipus'] not in ('ftp', 'xarxa', 'sap'):
        return jsonify({'error': "Tipus no valid. Opcions: ftp, xarxa, sap"}), 400

    desti = DestiDistribucio(
        nom=data['nom'],
        tipus=data['tipus'],
        configuracio=data.get('configuracio', {}),
        patro_nom_fitxer=data.get('patro_nom_fitxer', '{art_codi}.pdf'),
        actiu=data.get('actiu', True),
        created_by=request.usuari.get('email', ''),
    )
    db.session.add(desti)
    db.session.commit()
    return jsonify(desti.to_dict(include_config=True)), 201


@admin_bp.route('/admin/destins/<int:did>', methods=['GET'])
@rol_requerit('admin')
def detall_desti(did):
    desti = db.get_or_404(DestiDistribucio, did)
    return jsonify(desti.to_dict(include_config=True))


@admin_bp.route('/admin/destins/<int:did>', methods=['PUT'])
@rol_requerit('admin')
def editar_desti(did):
    desti = db.get_or_404(DestiDistribucio, did)
    data = request.get_json()

    if 'nom' in data:
        desti.nom = data['nom']
    if 'tipus' in data:
        if data['tipus'] not in ('ftp', 'xarxa', 'sap'):
            return jsonify({'error': "Tipus no valid"}), 400
        desti.tipus = data['tipus']
    if 'configuracio' in data:
        new_config = data['configuracio']
        if desti.configuracio and new_config.get('password') == '********':
            new_config['password'] = desti.configuracio.get('password', '')
        desti.configuracio = new_config
    if 'patro_nom_fitxer' in data:
        desti.patro_nom_fitxer = data['patro_nom_fitxer']
    if 'actiu' in data:
        desti.actiu = data['actiu']

    db.session.commit()
    return jsonify(desti.to_dict(include_config=True))


@admin_bp.route('/admin/destins/<int:did>', methods=['DELETE'])
@rol_requerit('admin')
def eliminar_desti(did):
    desti = db.get_or_404(DestiDistribucio, did)
    db.session.delete(desti)
    db.session.commit()
    return jsonify({'message': 'Desti eliminat'}), 200
