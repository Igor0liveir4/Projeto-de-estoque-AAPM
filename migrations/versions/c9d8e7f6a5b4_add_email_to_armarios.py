"""Adicionar coluna email na tabela armarios

Revision ID: c9d8e7f6a5b4
Revises: f1a2b3c4d5e6
Create Date: 2026-08-18 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d8e7f6a5b4'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ajuste para bancos já criados antes da correção do schema
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('armarios')]

    if 'email' not in columns:
        op.add_column('armarios', sa.Column('email', sa.String(length=120), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('armarios')]

    if 'email' in columns:
        op.drop_column('armarios', 'email')
