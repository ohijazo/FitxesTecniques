"""historial de traduccions

Revision ID: e5c1a7b3d924
Revises: d4b9e6f8a013
Create Date: 2026-11-03 16:00:00.000000

Additiva: taula nova traduccio_historial i columna opcional
traduccio_historial_id a distribucio i enviament_email_item. No modifica cap
dada existent (els registres anteriors queden sense còpia associada).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5c1a7b3d924'
down_revision = 'd4b9e6f8a013'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'traduccio_historial',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('traduccio_id', sa.Integer(), nullable=False),
        sa.Column('versio_id', sa.Integer(), nullable=False),
        sa.Column('idioma', sa.String(length=5), nullable=False),
        sa.Column('contingut', sa.JSON(), nullable=False),
        sa.Column('estat', sa.String(length=20), nullable=False),
        sa.Column('origen', sa.String(length=20), nullable=True),
        sa.Column('accio', sa.String(length=20), nullable=False),
        sa.Column('camps_canviats', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_traduccio_historial_traduccio_id', 'traduccio_historial', ['traduccio_id'])
    op.create_index('ix_traduccio_historial_versio_id', 'traduccio_historial', ['versio_id'])
    op.add_column('distribucio', sa.Column('traduccio_historial_id', sa.Integer(), nullable=True))
    op.add_column('enviament_email_item', sa.Column('traduccio_historial_id', sa.Integer(), nullable=True))


def downgrade():
    # ATENCIÓ: esborra tot l'historial de traduccions
    op.drop_column('enviament_email_item', 'traduccio_historial_id')
    op.drop_column('distribucio', 'traduccio_historial_id')
    op.drop_index('ix_traduccio_historial_versio_id', table_name='traduccio_historial')
    op.drop_index('ix_traduccio_historial_traduccio_id', table_name='traduccio_historial')
    op.drop_table('traduccio_historial')
