"""Adicionar constraint única composta numero+localizacao

Revision ID: f1a2b3c4d5e6
Revises: c52d1e8f9a34
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c52d1e8f9a34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        # SQLite: recreate table with the new unique constraint
        op.create_table(
            'armarios_new',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('numero', sa.String(length=20), nullable=False),
            sa.Column('localizacao', sa.String(length=100), nullable=True),
            sa.Column('status', sa.Enum('DISPONIVEL', 'ALUGADO', 'INATIVO', name='statusarmario'), nullable=False),
            sa.Column('locatario_nome', sa.String(length=150), nullable=True),
            sa.Column('nome_curso', sa.String(length=100), nullable=True),
            sa.Column('turma', sa.String(length=50), nullable=True),
            sa.Column('email', sa.String(length=120), nullable=True),
            sa.Column('observacao', sa.String(length=255), nullable=True),
            sa.Column('ativo', sa.Boolean(), nullable=True),
            sa.Column('alugado_em', sa.DateTime(), nullable=True),
            sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.UniqueConstraint('numero', 'localizacao', name='uix_numero_localizacao')
        )

        # Copy data from old table to new table
        op.execute(
            """
            INSERT INTO armarios_new (id, numero, localizacao, status, locatario_nome, nome_curso, turma, email, observacao, ativo, alugado_em, criado_em, atualizado_em)
            SELECT id, numero, localizacao, status, locatario_nome, nome_curso, turma, email, observacao, ativo, alugado_em, criado_em, atualizado_em FROM armarios
            """
        )

        # Drop old table and rename new
        op.drop_table('armarios')
        op.rename_table('armarios_new', 'armarios')

        # Recreate index if needed
        op.create_index(op.f('ix_armarios_id'), 'armarios', ['id'], unique=False)

    else:
        # For other DBs: drop the existing unique on 'numero' (best-effort) and add the composite unique
        try:
            op.drop_constraint('uq_armarios_numero', 'armarios', type_='unique')
        except Exception:
            # try a generic name used in earlier revision
            try:
                op.drop_constraint('armarios_numero_key', 'armarios', type_='unique')
            except Exception:
                # If constraint name is unknown, autogenerate may be required.
                pass

        op.create_unique_constraint('uix_numero_localizacao', 'armarios', ['numero', 'localizacao'])


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        # Recreate previous table with unique(numero)
        op.create_table(
            'armarios_old',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('numero', sa.String(length=20), nullable=False),
            sa.Column('localizacao', sa.String(length=100), nullable=True),
            sa.Column('status', sa.Enum('DISPONIVEL', 'ALUGADO', 'INATIVO', name='statusarmario'), nullable=False),
            sa.Column('locatario_nome', sa.String(length=150), nullable=True),
            sa.Column('nome_curso', sa.String(length=100), nullable=True),
            sa.Column('turma', sa.String(length=50), nullable=True),
            sa.Column('email', sa.String(length=120), nullable=True),
            sa.Column('observacao', sa.String(length=255), nullable=True),
            sa.Column('ativo', sa.Boolean(), nullable=True),
            sa.Column('alugado_em', sa.DateTime(), nullable=True),
            sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.UniqueConstraint('numero')
        )

        op.execute(
            """
            INSERT INTO armarios_old (id, numero, localizacao, status, locatario_nome, nome_curso, turma, email, observacao, ativo, alugado_em, criado_em, atualizado_em)
            SELECT id, numero, localizacao, status, locatario_nome, nome_curso, turma, email, observacao, ativo, alugado_em, criado_em, atualizado_em FROM armarios
            """
        )

        op.drop_table('armarios')
        op.rename_table('armarios_old', 'armarios')
        op.create_index(op.f('ix_armarios_id'), 'armarios', ['id'], unique=False)

    else:
        # Remove composite unique and restore single-column unique
        try:
            op.drop_constraint('uix_numero_localizacao', 'armarios', type_='unique')
        except Exception:
            pass
        op.create_unique_constraint(None, 'armarios', ['numero'])
