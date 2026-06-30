"""Afegir taula audit_log per traçabilitat de canvis administratius

Revision ID: e4f1a2b3c5d6
Revises: c2d8e5a3b1f0
Create Date: 2026-06-04 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4f1a2b3c5d6'
down_revision = 'c2d8e5a3b1f0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuari', sa.String(length=200), nullable=False),
        sa.Column('accio', sa.String(length=50), nullable=False),
        sa.Column('entitat', sa.String(length=50), nullable=False),
        sa.Column('entitat_id', sa.Integer(), nullable=True),
        sa.Column('abans', sa.JSON(), nullable=True),
        sa.Column('despres', sa.JSON(), nullable=True),
        sa.Column('at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_audit_log_usuari', 'audit_log', ['usuari'])
    op.create_index('ix_audit_log_accio', 'audit_log', ['accio'])
    op.create_index('ix_audit_log_entitat', 'audit_log', ['entitat'])
    op.create_index('ix_audit_log_at', 'audit_log', ['at'])


def downgrade():
    op.drop_index('ix_audit_log_at', table_name='audit_log')
    op.drop_index('ix_audit_log_entitat', table_name='audit_log')
    op.drop_index('ix_audit_log_accio', table_name='audit_log')
    op.drop_index('ix_audit_log_usuari', table_name='audit_log')
    op.drop_table('audit_log')
