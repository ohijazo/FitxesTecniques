from functools import wraps
from flask import request, jsonify, current_app
import jwt


def get_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def decode_token(token):
    try:
        return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token()
        if not token:
            return jsonify({'error': "Cal autenticar-se"}), 401
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': "Token invàlid o expirat"}), 401
        request.usuari = payload
        return f(*args, **kwargs)
    return decorated


def rol_requerit(*rols):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token()
            if not token:
                return jsonify({'error': "Cal autenticar-se"}), 401
            payload = decode_token(token)
            if not payload:
                return jsonify({'error': "Token invàlid o expirat"}), 401
            if payload.get('rol') not in rols:
                return jsonify({'error': "No tens permisos per aquesta acció"}), 403
            request.usuari = payload
            return f(*args, **kwargs)
        return decorated
    return decorator
