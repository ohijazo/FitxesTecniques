"""afegir taules enviament_email i enviament_email_item

Revision ID: b7e3f1a9c2d4
Revises: e4d7b2a91c50
Create Date: 2026-10-15 12:00:00.000000

Nomes afegeix taules noves: no toca dades existents.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e3f1a9c2d4'
down_revision = 'e4d7b2a91c50'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'enviament_email',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('remitent', sa.String(length=200), nullable=False),
        sa.Column('per_a', sa.Text(), nullable=False),
        sa.Column('cc', sa.Text(), nullable=True),
        sa.Column('assumpte', sa.String(length=500), nullable=False),
        sa.Column('cos', sa.Text(), nullable=True),
        sa.Column('estat', sa.String(length=20), nullable=False),
        sa.Column('missatge_error', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('executat_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'enviament_email_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enviament_id', sa.Integer(), nullable=False),
        sa.Column('fitxa_id', sa.Integer(), nullable=False),
        sa.Column('versio_id', sa.Integer(), nullable=False),
        sa.Column('art_codi', sa.String(length=50), nullable=False),
        sa.Column('num_versio', sa.Integer(), nullable=False),
        sa.Column('nom_fitxer', sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(['enviament_id'], ['enviament_email.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_enviament_email_item_enviament_id', 'enviament_email_item', ['enviament_id'])
    op.create_index('ix_enviament_email_item_fitxa_id', 'enviament_email_item', ['fitxa_id'])


def downgrade():
    op.drop_index('ix_enviament_email_item_fitxa_id', table_name='enviament_email_item')
    op.drop_index('ix_enviament_email_item_enviament_id', table_name='enviament_email_item')
    op.drop_table('enviament_email_item')
    op.drop_table('enviament_email')
