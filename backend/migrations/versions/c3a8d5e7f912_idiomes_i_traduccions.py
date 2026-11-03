"""idiomes per fitxa i taula traduccio_versio

Revision ID: c3a8d5e7f912
Revises: b7e3f1a9c2d4
Create Date: 2026-11-03 12:00:00.000000

Additiva: afegeix la columna fitxa_tecnica.idiomes (per defecte '[]') i la
taula nova traduccio_versio. No modifica cap dada existent.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3a8d5e7f912'
down_revision = 'b7e3f1a9c2d4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('fitxa_tecnica', sa.Column(
        'idiomes', sa.JSON(), nullable=False, server_default='[]'))
    op.create_table(
        'traduccio_versio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('versio_id', sa.Integer(), nullable=False),
        sa.Column('idioma', sa.String(length=5), nullable=False),
        sa.Column('contingut', sa.JSON(), nullable=False),
        sa.Column('estat', sa.String(length=20), nullable=False),
        sa.Column('origen', sa.String(length=20), nullable=True),
        sa.Column('camps_canviats', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('revisat_at', sa.DateTime(), nullable=True),
        sa.Column('revisat_by', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['versio_id'], ['versio_fitxa.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('versio_id', 'idioma', name='uq_traduccio_versio_idioma'),
    )
    op.create_index('ix_traduccio_versio_versio_id', 'traduccio_versio', ['versio_id'])


def downgrade():
    # ATENCIÓ: el downgrade esborra totes les traduccions desades.
    op.drop_index('ix_traduccio_versio_versio_id', table_name='traduccio_versio')
    op.drop_table('traduccio_versio')
    op.drop_column('fitxa_tecnica', 'idiomes')
