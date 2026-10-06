"""Cria uma variação padrão para produtos já existentes.

Revision ID: c7f4a1d9e2b0
Revises: b4b3aaf0d58f
Create Date: 2026-07-28 16:20:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c7f4a1d9e2b0"
down_revision: Union[str, Sequence[str], None] = "b4b3aaf0d58f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # O estoque antigo não existe mais em produtos. Esta variação padrão permite
    # que os itens antigos recebam saldo pelo fluxo atual de edição/movimentação.
    op.execute(
        """
        INSERT INTO variacoes (produto_id, tamanho, cor, estoque_atual)
        SELECT produtos.id, 'Único', 'Padrão', 0
        FROM produtos
        WHERE NOT EXISTS (
            SELECT 1
            FROM variacoes
            WHERE variacoes.produto_id = produtos.id
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM variacoes
        WHERE tamanho = 'Único' AND cor = 'Padrão' AND estoque_atual = 0
        """
    )
