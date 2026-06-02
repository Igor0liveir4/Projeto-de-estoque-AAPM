# Tabela de movimentação de estoque

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy import func
from app.database import Base
import enum

class Tipo_de_movimentacao(str, enum.Enum):
    ENTRADA = "Entrada"
    SAIDA = "Saída"

class Movimentacao(Base):
    __tablename__ = 'movimentacoes'

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    tipo = Column(Enum(Tipo_de_movimentacao), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False, default=0.0)
    observacao = Column(String(255), nullable=True)
    criado_em = Column(DateTime, server_default=func.now())

    produto_id = Column(Integer, ForeignKey('produtos.id', ondelete="CASCADE"), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete="SET NULL"), nullable=True)

    # Relacionamentos
    produto = relationship("Produto", backref="movimentacoes")
    usuario = relationship("Usuario", backref="movimentacoes")