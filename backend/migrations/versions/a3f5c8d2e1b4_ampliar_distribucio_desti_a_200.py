"""ampliar distribucio.desti de VARCHAR(20) a VARCHAR(200)

Revision ID: a3f5c8d2e1b4
Revises: f7a91c4e3b2d
Create Date: 2026-05-29 08:00:00.000000

Motiu: els destins de distribucio guarden el nom del DestiDistribucio
(p. ex. 'SharePoint Comercials') i no el tipus tecnic. Amb VARCHAR(20)
qualsevol nom de mes de 20 caracters trenca l'INSERT amb
StringDataRightTruncation i la peticio retorna 500.

El model (Distribucio.desti) ja declara String(200); aquesta migracio
nomes alinea la columna fisica de PostgreSQL.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f5c8d2e1b4'
down_revision = 'f7a91c4e3b2d'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'distribucio',
        'desti',
        existing_type=sa.String(length=20),
        type_=sa.String(length=200),
        existing_nullable=False,
    )


def downgrade():
    # Atencio: si hi ha valors > 20 chars, el downgrade fallara per truncament.
    op.alter_column(
        'distribucio',
        'desti',
        existing_type=sa.String(length=200),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
