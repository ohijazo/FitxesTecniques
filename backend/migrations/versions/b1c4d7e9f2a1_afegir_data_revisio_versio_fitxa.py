"""afegir data_revisio a versio_fitxa

Revision ID: b1c4d7e9f2a1
Revises: 88b8888d9e19
Create Date: 2026-06-04 09:00:00.000000

Afegim data_revisio com a columna pròpia (fins ara es guardava dins
del JSONB `contingut`). NULL permès per a fitxes antigues -- el PDF
generator fa fallback a `created_at`.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c4d7e9f2a1'
down_revision = '88b8888d9e19'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('versio_fitxa', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_revisio', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('versio_fitxa', schema=None) as batch_op:
        batch_op.drop_column('data_revisio')
