from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app
import jwt
from app import db
from app.models import Usuari
from app.auth import login_required, rol_requerit

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': "Camps obligatoris: email, password"}), 400

    usuari = Usuari.query.filter_by(email=data['email']).first()
    if not usuari or not usuari.check_password(data['password']):
        return jsonify({'error': "Email o contrasenya incorrectes"}), 401

    if not usuari.actiu:
        return jsonify({'error': "Usuari desactivat"}), 403

    token = jwt.encode({
        'id': usuari.id,
        'email': usuari.email,
        'nom': usuari.nom,
        'rol': usuari.rol,
        'exp': datetime.now(timezone.utc) + timedelta(hours=12),
    }, current_app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'token': token,
        'usuari': usuari.to_dict(),
    })


@auth_bp.route('/auth/me', methods=['GET'])
@login_required
def perfil():
    usuari = db.get_or_404(Usuari, request.usuari['id'])
    return jsonify(usuari.to_dict())


@auth_bp.route('/auth/refresh', methods=['POST'])
@login_required
def refresh_token():
    """Refresca el token JWT si encara és vàlid."""
    usuari = db.get_or_404(Usuari, request.usuari['id'])
    if not usuari.actiu:
        return jsonify({'error': "Usuari desactivat"}), 403

    token = jwt.encode({
        'id': usuari.id,
        'email': usuari.email,
        'nom': usuari.nom,
        'rol': usuari.rol,
        'exp': datetime.now(timezone.utc) + timedelta(hours=12),
    }, current_app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token})


# --- Gestió d'usuaris (admin) ---

@auth_bp.route('/admin/usuaris', methods=['GET'])
@rol_requerit('admin')
def llistar_usuaris():
    usuaris = Usuari.query.order_by(Usuari.nom).all()
    return jsonify([u.to_dict() for u in usuaris])


@auth_bp.route('/admin/usuaris', methods=['POST'])
@rol_requerit('admin')
def crear_usuari():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('nom') or not data.get('password'):
        return jsonify({'error': "Camps obligatoris: email, nom, password"}), 400

    if data.get('rol') not in ('admin', 'editor', 'visualitzador'):
        return jsonify({'error': "Rol no vàlid. Opcions: admin, editor, visualitzador"}), 400

    if Usuari.query.filter_by(email=data['email']).first():
        return jsonify({'error': "Ja existeix un usuari amb aquest email"}), 409

    usuari = Usuari(
        email=data['email'],
        nom=data['nom'],
        rol=data.get('rol', 'visualitzador'),
    )
    usuari.set_password(data['password'])
    db.session.add(usuari)
    db.session.commit()

    return jsonify(usuari.to_dict()), 201


@auth_bp.route('/admin/usuaris/<int:uid>', methods=['PUT'])
@rol_requerit('admin')
def editar_usuari(uid):
    usuari = db.get_or_404(Usuari, uid)
    data = request.get_json()

    if 'nom' in data:
        usuari.nom = data['nom']
    if 'email' in data:
        existing = Usuari.query.filter_by(email=data['email']).first()
        if existing and existing.id != uid:
            return jsonify({'error': "Ja existeix un usuari amb aquest email"}), 409
        usuari.email = data['email']
    if 'rol' in data:
        if data['rol'] not in ('admin', 'editor', 'visualitzador'):
            return jsonify({'error': "Rol no vàlid"}), 400
        usuari.rol = data['rol']
    if 'actiu' in data:
        usuari.actiu = data['actiu']
    if 'password' in data and data['password']:
        usuari.set_password(data['password'])

    db.session.commit()
    return jsonify(usuari.to_dict())


@auth_bp.route('/admin/usuaris/<int:uid>', methods=['DELETE'])
@rol_requerit('admin')
def eliminar_usuari(uid):
    usuari = db.get_or_404(Usuari, uid)
    if usuari.id == request.usuari['id']:
        return jsonify({'error': "No pots eliminar-te a tu mateix"}), 400
    db.session.delete(usuari)
    db.session.commit()
    return jsonify({'message': 'Usuari eliminat'})
