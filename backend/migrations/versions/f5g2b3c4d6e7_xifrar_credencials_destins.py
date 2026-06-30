"""Xifrar credencials sensibles dels destins (idempotent)

Revision ID: f5g2b3c4d6e7
Revises: e4f1a2b3c5d6
Create Date: 2026-06-04 14:00:00.000000

Aquesta migració:
- NO modifica l'esquema (no DDL).
- Si ENCRYPTION_KEY està definida, xifra els camps 'password' i 'client_secret'
  dins de `desti_distribucio.configuracio` que encara no estiguin xifrats.
- Si ENCRYPTION_KEY no està definida, deixa els valors tal qual i registra un avís.

Downgrade:
- Desxifra els valors (sempre que la clau hi sigui). Si la clau no està, no fa res.
"""
import json
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import MetaData, Table


revision = 'f5g2b3c4d6e7'
down_revision = 'e4f1a2b3c5d6'
branch_labels = None
depends_on = None

LOG = logging.getLogger(__name__)


def _iter_destins(conn):
    meta = MetaData()
    destins = Table('desti_distribucio', meta, autoload_with=conn)
    return destins, conn.execute(sa.select(destins.c.id, destins.c.configuracio)).fetchall()


def upgrade():
    from app.services.crypto import _get_fernet, encrypt_value, PREFIX, SENSITIVE_KEYS
    conn = op.get_bind()

    if _get_fernet() is None:
        LOG.warning(
            "[MIGRATION f5g2b3c4d6e7] ENCRYPTION_KEY no definida — credencials NO xifrades. "
            "Definiu ENCRYPTION_KEY a .env i torneu a executar aquesta migració per xifrar-les."
        )
        return

    destins, rows = _iter_destins(conn)
    actualitzats = 0
    for row in rows:
        config = row.configuracio or {}
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                continue
        canviat = False
        nou = dict(config)
        for k in SENSITIVE_KEYS:
            v = nou.get(k)
            if isinstance(v, str) and v and not v.startswith(PREFIX):
                nou[k] = encrypt_value(v)
                canviat = True
        if canviat:
            conn.execute(
                destins.update().where(destins.c.id == row.id).values(configuracio=nou)
            )
            actualitzats += 1

    LOG.info('[MIGRATION f5g2b3c4d6e7] Destins re-xifrats: %d', actualitzats)


def downgrade():
    from app.services.crypto import _get_fernet, decrypt_value, PREFIX, SENSITIVE_KEYS
    conn = op.get_bind()

    if _get_fernet() is None:
        LOG.warning("[MIGRATION f5g2b3c4d6e7 downgrade] ENCRYPTION_KEY no disponible — no es pot desxifrar.")
        return

    destins, rows = _iter_destins(conn)
    actualitzats = 0
    for row in rows:
        config = row.configuracio or {}
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                continue
        canviat = False
        nou = dict(config)
        for k in SENSITIVE_KEYS:
            v = nou.get(k)
            if isinstance(v, str) and v.startswith(PREFIX):
                nou[k] = decrypt_value(v)
                canviat = True
        if canviat:
            conn.execute(
                destins.update().where(destins.c.id == row.id).values(configuracio=nou)
            )
            actualitzats += 1

    LOG.info('[MIGRATION f5g2b3c4d6e7 downgrade] Destins desxifrats: %d', actualitzats)
