"""afegir tipus_producte a fitxa_tecnica

Revision ID: a1b2c3d4e5f6
Revises: c2d8e5a3b1f0
Create Date: 2026-07-20 15:30:00.000000

Nova columna `tipus_producte` per distingir fitxes elaborades (per defecte,
comportament actual) de fitxes de producte comercialitzat (PDF-only, es puja
el PDF del proveïdor sense contingut estructurat).

Migració additiva: totes les fitxes existents queden 'elaborat'.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'c2d8e5a3b1f0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'fitxa_tecnica',
        sa.Column('tipus_producte', sa.String(length=20),
                  nullable=False, server_default='elaborat'),
    )


def downgrade():
    op.drop_column('fitxa_tecnica', 'tipus_producte')
