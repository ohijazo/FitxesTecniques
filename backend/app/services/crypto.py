"""Encriptació opcional de valors sensibles (credencials destins).

Comportament:
- Si la variable d'entorn `ENCRYPTION_KEY` no està definida, encrypt/decrypt són
  no-op: els valors passen tal qual. Permet desplegar el codi sense activar
  l'encriptació immediatament.
- Si està definida, els valors es xifren amb Fernet i es prefixen amb 'enc:'.
  Els valors antics sense prefix es deixen com a plain (compat retro), però la
  migració els xifra en córrer-la.

Clau:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
i posar la sortida a `.env` com:
    ENCRYPTION_KEY=<la-clau>

⚠️ Si la clau es perd, les credencials xifrades NO es poden recuperar.
Cal fer-ne còpia de seguretat a un gestor de secrets (no a Git).
"""
import logging
import os

LOG = logging.getLogger(__name__)

PREFIX = 'enc:'
SENSITIVE_KEYS = {'password', 'client_secret', 'secret', 'token'}


def _get_fernet():
    """Retorna un Fernet o None si la clau no està disponible / és invàlida."""
    key = os.environ.get('ENCRYPTION_KEY', '').strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode())
    except Exception as e:
        LOG.error('[CRYPTO] ENCRYPTION_KEY invàlida: %s', e)
        return None


def encrypt_value(value):
    """Xifra un string. Idempotent (no re-xifra valors ja xifrats)."""
    if not value or not isinstance(value, str):
        return value
    if value.startswith(PREFIX):
        return value
    f = _get_fernet()
    if not f:
        return value
    return PREFIX + f.encrypt(value.encode()).decode()


def decrypt_value(value):
    """Desxifra si té prefix. Si la clau no està o falla, retorna el valor tal qual."""
    if not value or not isinstance(value, str) or not value.startswith(PREFIX):
        return value
    f = _get_fernet()
    if not f:
        LOG.warning('[CRYPTO] Valor xifrat trobat però ENCRYPTION_KEY no definida')
        return value
    try:
        return f.decrypt(value[len(PREFIX):].encode()).decode()
    except Exception as e:
        LOG.exception('[CRYPTO] Error desxifrant: %s', e)
        return value


def encrypt_config(config):
    """Retorna una còpia del dict de configuració amb camps sensibles xifrats."""
    if not isinstance(config, dict):
        return config
    return {k: (encrypt_value(v) if k in SENSITIVE_KEYS and isinstance(v, str) else v)
            for k, v in config.items()}


def decrypt_config(config):
    """Retorna una còpia del dict amb camps sensibles desxifrats."""
    if not isinstance(config, dict):
        return config
    return {k: (decrypt_value(v) if k in SENSITIVE_KEYS and isinstance(v, str) else v)
            for k, v in config.items()}
