"""afegir taula estat_fitxa

Revision ID: c2d8e5a3b1f0
Revises: b1c4d7e9f2a1
Create Date: 2026-06-04 11:00:00.000000

Catàleg d'estats configurable per gestionar des de la pantalla
/admin/estats. Inclou seed dels 4 estats que abans estaven
hardcoded al codi: esborrany, publicada, obsoleta, inactiva.
Els 4 estats inicials es marquen com `protegit=True` per
prevenir-ne l'eliminació accidental.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2d8e5a3b1f0'
down_revision = 'b1c4d7e9f2a1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'estat_fitxa',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codi', sa.String(length=30), nullable=False),
        sa.Column('nom', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('color_text', sa.String(length=20), nullable=True),
        sa.Column('accio', sa.String(length=40), nullable=True),
        sa.Column('protegit', sa.Boolean(), nullable=True),
        sa.Column('ordre', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codi'),
    )

    # Seed amb els 4 estats existents (mateixos colors que el CSS antic)
    estat_fitxa = sa.table(
        'estat_fitxa',
        sa.column('codi', sa.String),
        sa.column('nom', sa.String),
        sa.column('color', sa.String),
        sa.column('color_text', sa.String),
        sa.column('accio', sa.String),
        sa.column('protegit', sa.Boolean),
        sa.column('ordre', sa.Integer),
    )
    op.bulk_insert(estat_fitxa, [
        {'codi': 'esborrany', 'nom': 'Esborrany', 'color': '#fef3c7',
         'color_text': '#92400e', 'accio': 'cap', 'protegit': True, 'ordre': 1},
        {'codi': 'publicada', 'nom': 'Publicada', 'color': '#d1fae5',
         'color_text': '#065f46', 'accio': 'cap', 'protegit': True, 'ordre': 2},
        {'codi': 'obsoleta', 'nom': 'Obsoleta', 'color': '#fee2e2',
         'color_text': '#991b1b', 'accio': 'cap', 'protegit': True, 'ordre': 3},
        {'codi': 'inactiva', 'nom': 'Inactiva', 'color': '#e5e7eb',
         'color_text': '#374151', 'accio': 'esborrar_destins', 'protegit': True, 'ordre': 4},
    ])


def downgrade():
    op.drop_table('estat_fitxa')
