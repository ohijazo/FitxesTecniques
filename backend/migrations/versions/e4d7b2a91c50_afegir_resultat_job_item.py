"""Afegir job_item.resultat (JSON) per guardar el detall de les comprovacions

Migracio additiva i retrocompatible: columna nullable sense default, per tant
les files existents queden a NULL i cap codi anterior la llegeix. A PostgreSQL
un ADD COLUMN sense default no reescriu la taula.

Revision ID: e4d7b2a91c50
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa


revision = 'e4d7b2a91c50'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('job_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resultat', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('job_item', schema=None) as batch_op:
        batch_op.drop_column('resultat')
