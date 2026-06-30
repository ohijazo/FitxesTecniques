"""Utility per registrar entrades a la taula audit_log.

Pensat per ser cridat des d'endpoints admin després d'un canvi reeixit, just
abans del commit o just després (no és crític que pugui fallar — qualsevol
excepció es captura per no fer descarrilar la petició original).
"""
import logging

from flask import request

from app import db
from app.models import AuditLog

LOG = logging.getLogger(__name__)

# Camps sensibles que mai s'han d'emmagatzemar en clar al snapshot
SECRET_KEYS = {'password', 'password_hash', 'client_secret', 'secret', 'token'}


def _sanititzar(data):
    """Substitueix valors sensibles per '***' en un dict o nested dict."""
    if isinstance(data, dict):
        return {k: ('***' if k in SECRET_KEYS else _sanititzar(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanititzar(x) for x in data]
    return data


def registrar(accio, entitat, entitat_id=None, abans=None, despres=None):
    """Crea una entrada a audit_log i fa flush (no commit; deixa el commit a la ruta).

    Si quelcom falla, es captura silenciosament — auditar no ha de bloquejar la
    petició principal. Es loguega l'error.
    """
    try:
        usuari = ''
        try:
            usuari = (request.usuari.get('email') or '') if hasattr(request, 'usuari') else ''
        except Exception:
            usuari = ''
        entry = AuditLog(
            usuari=usuari,
            accio=accio,
            entitat=entitat,
            entitat_id=entitat_id,
            abans=_sanititzar(abans) if abans is not None else None,
            despres=_sanititzar(despres) if despres is not None else None,
        )
        db.session.add(entry)
    except Exception as e:
        LOG.exception('[AUDIT] No s\'ha pogut registrar (%s %s %s): %s', accio, entitat, entitat_id, e)
