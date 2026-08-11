# ============================================================
# models/armario.py — Tabela de armários
# ============================================================

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum


class StatusArmario(str, enum.Enum):
    DISPONIVEL = "disponivel"
    ALUGADO    = "alugado"
    INATIVO    = "inativo"


class Armario(Base):
    __tablename__ = "armarios"

    id     = Column(Integer, primary_key=True, index=True)

    # Número visível na porta do armário — ex: "A01", "B12", "42"
    numero = Column(String(20), nullable=False, unique=True)

    # Localização opcional — ex: "Bloco A - Térreo"
    localizacao = Column(String(100), nullable=True)

    status = Column(
        Enum(StatusArmario),
        nullable=False,
        default=StatusArmario.DISPONIVEL
    )

    # ----------------------------------------------------------
    # Dados do locatário atual — preenchidos pelo admin.
    # Ficam NULL quando o armário está disponível ou inativo.
    # ----------------------------------------------------------

    # Nome do aluno/cliente que alugou
    locatario_nome = Column(String(150), nullable=True)

    # Semestre fixo do contrato — ex: "2025.1", "2025.2"
    # O admin define manualmente — não calculamos por data.
    semestre = Column(String(10), nullable=True)

    # Observação livre — ex: "Chave reserva com portaria"
    observacao = Column(String(255), nullable=True)

    ativo = Column(Boolean, default=True)

    # Data em que o aluguel atual começou
    alugado_em     = Column(DateTime, nullable=True)
    criado_em      = Column(DateTime, server_default=func.now())
    atualizado_em  = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Armario numero={self.numero} status={self.status}>"

    @property
    def disponivel(self) -> bool:
        return self.status == StatusArmario.DISPONIVEL