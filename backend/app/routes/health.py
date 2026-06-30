"""Endpoint de salut de l'aplicació.

Pensat per a:
- Health check d'Apache/load balancer (només cal status 200/503).
- Monitorització externa que llegeix el JSON per saber si el worker és viu.

No requereix autenticació: només indica estat operatiu, no exposa dades sensibles.
"""
from flask import Blueprint, jsonify
from sqlalchemy import text

from app import db
from app.services import heartbeat

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health():
    """Retorna estat de la BD i del worker.

    Codis HTTP:
      200 — tot OK
      503 — BD o worker no responen com s'espera

    Resposta JSON:
      {
        "ok": bool,
        "db": "ok" | "error",
        "db_error": str (opcional),
        "worker": {"estat": "ok"|"stale"|"unknown", "workers": [...]}
      }
    """
    estat = {'ok': True, 'db': 'ok', 'worker': heartbeat.estat()}

    try:
        db.session.execute(text('SELECT 1'))
    except Exception as e:
        estat['db'] = 'error'
        estat['db_error'] = str(e)[:200]
        estat['ok'] = False

    if not estat['worker']['ok']:
        estat['ok'] = False

    return jsonify(estat), (200 if estat['ok'] else 503)
