"""merge migration branches

Revision ID: a91c2d7e4b60
Revises: c7f4a1d9e2b0, f8d3b16c1a4e
Create Date: 2026-11-03 00:00:00.000000
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "a91c2d7e4b60"
down_revision: Union[str, Sequence[str], None] = (
    "c7f4a1d9e2b0",
    "f8d3b16c1a4e",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
