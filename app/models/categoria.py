# Tabelas de categorias de produtos
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), unique=True, nullable=False)
    descricao = Column(String(255), nullable=True)
    ativa = Column(Boolean, default=True)

    produtos = relationship("Produto", back_populates="categoria")

    def __str__(self):
        return self.nome