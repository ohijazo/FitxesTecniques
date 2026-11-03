"""idioma a distribucio i enviament_email_item

Revision ID: d4b9e6f8a013
Revises: c3a8d5e7f912
Create Date: 2026-11-03 15:00:00.000000

Additiva: dues columnes opcionals. NULL = PDF principal ({art_codi}.pdf), així
tot l'historial existent continua sent vàlid sense tocar-lo.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4b9e6f8a013'
down_revision = 'c3a8d5e7f912'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('distribucio', sa.Column('idioma', sa.String(length=5), nullable=True))
    op.add_column('enviament_email_item', sa.Column('idioma', sa.String(length=5), nullable=True))


def downgrade():
    # ATENCIÓ: es perd quin idioma era cada distribució/adjunt d'idioma
    # (els registres es mantenen, però semblaran del PDF principal).
    op.drop_column('enviament_email_item', 'idioma')
    op.drop_column('distribucio', 'idioma')
