"""adiciona campo formas_pagamento em vendas

Revision ID: f8d3b16c1a4e
Revises: dbd900df15de
Create Date: 2026-10-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8d3b16c1a4e"
down_revision: Union[str, Sequence[str], None] = "dbd900df15de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("vendas") as batch_op:
        batch_op.add_column(sa.Column("formas_pagamento", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("vendas") as batch_op:
        batch_op.drop_column("formas_pagamento")
