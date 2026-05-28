"""afegir taula registre_eliminacio

Revision ID: f7a91c4e3b2d
Revises: 080e91f28f8a
Create Date: 2026-05-11 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7a91c4e3b2d'
down_revision = '080e91f28f8a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'registre_eliminacio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('art_codi', sa.String(length=50), nullable=False),
        sa.Column('nom_producte', sa.String(length=200), nullable=False),
        sa.Column('num_versions', sa.Integer(), nullable=True),
        sa.Column('ultima_versio', sa.Integer(), nullable=True),
        sa.Column('motiu', sa.Text(), nullable=False),
        sa.Column('esborrat_ftp', sa.Boolean(), nullable=True),
        sa.Column('eliminat_per', sa.String(length=200), nullable=False),
        sa.Column('eliminat_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('registre_eliminacio')
