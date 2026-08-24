"""impede variacoes duplicadas

Revision ID: d7e4f2a1c9b8
Revises: b4b3aaf0d58f
Create Date: 2026-08-24
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d7e4f2a1c9b8"
down_revision: Union[str, Sequence[str], None] = "c52d1e8f9a34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Padroniza registros já existentes, evitando que "m" e "M" apareçam
    # como tamanhos distintos no PDV.
    op.execute("UPDATE variacoes SET tamanho = UPPER(TRIM(tamanho))")

    # SQLite recria a tabela por meio do batch_alter_table para adicionar a
    # restrição única; outros bancos executam a alteração normalmente.
    with op.batch_alter_table("variacoes") as batch_op:
        batch_op.create_unique_constraint(
            "uq_variacao_produto_tamanho_cor",
            ["produto_id", "tamanho", "cor"],
        )


def downgrade() -> None:
    with op.batch_alter_table("variacoes") as batch_op:
        batch_op.drop_constraint("uq_variacao_produto_tamanho_cor", type_="unique")
