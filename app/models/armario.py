# ============================================================
# models/armario.py — Tabela de armários
# ============================================================

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime, timedelta, timezone
import enum


class StatusArmario(str, enum.Enum):
    DISPONIVEL = "disponivel"
    ALUGADO    = "alugado"
    INATIVO    = "inativo"


class Armario(Base):
    __tablename__ = "armarios"
    __table_args__ = (
        UniqueConstraint('numero', 'localizacao', name='uix_numero_localizacao'),
    )

    id     = Column(Integer, primary_key=True, index=True)

    # Número visível na porta do armário — ex: "A01", "B12", "42"
    numero = Column(String(20), nullable=False)

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

    # Nome do curso — ex: "Engenharia de Software"
    nome_curso = Column(String(100), nullable=True)

    # Turma — ex: "Seduc - Dev", "2026-A"
    turma = Column(String(50), nullable=True)

    # Email para avisos de pagamento
    email = Column(String(120), nullable=True)

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

    @property
    def dias_aluguel(self) -> int:
        """Retorna quantos dias o armário está alugado."""
        if not self.alugado_em:
            return 0
        delta = datetime.now(timezone.utc) - self.alugado_em
        return delta.days

    @property
    def acesso_ativo(self) -> bool:
        """Retorna True se o aluguel ainda está válido (< 30 dias)."""
        if self.status != StatusArmario.ALUGADO or not self.alugado_em:
            return False
        return self.dias_aluguel < 30

    @property
    def prazo_vencimento(self) -> datetime:
        """Retorna a data de vencimento (30 dias após aluguel)."""
        if not self.alugado_em:
            return None
        return self.alugado_em + timedelta(days=30)
