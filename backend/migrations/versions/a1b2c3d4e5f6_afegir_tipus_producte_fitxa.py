"""Afegir columna tipus_producte a fitxa_tecnica

Revision ID: a1b2c3d4e5f6
Revises: f5g2b3c4d6e7
Create Date: 2026-06-30 13:30:00.000000

Distingeix les fitxes 'elaborat' (productes propis amb contingut estructurat
i PDF generat) de les 'comercialitzat' (productes revenuts on només es puja
el PDF rebut del proveidor). Per defecte 'elaborat' per preservar el
comportament existent.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f5g2b3c4d6e7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'fitxa_tecnica',
        sa.Column(
            'tipus_producte',
            sa.String(length=20),
            nullable=False,
            server_default='elaborat',
        ),
    )


def downgrade():
    op.drop_column('fitxa_tecnica', 'tipus_producte')
