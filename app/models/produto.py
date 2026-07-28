# Tabela de produtos
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(String(150), nullable=False, index=True, unique=True)
    preco = Column(Float, nullable=False, default=0.0)
    ativo = Column(Boolean, default=True)

    imagem_path = Column(String(255), nullable=True)

    # Chave estrangeira para categoria
    categoria_id = Column(Integer, ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)

    # Relacionamento com categoria
    categoria = relationship("Categoria", back_populates="produtos")

    # Relacionamento com variações
    variacoes = relationship("Variacao", back_populates="produto", cascade="all, delete-orphan")

    @property
    def imagem_url(self):
        if self.imagem_path:
            return f"/static/{self.imagem_path}"
        else:
            return "/static/img/produto-placeholder.png"
        
    @property
    def estoque_total(self):
        return sum(variacao for variacao in self.variacoes)
        