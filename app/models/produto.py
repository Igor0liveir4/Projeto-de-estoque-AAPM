# Tabela de produtos
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(String(150), nullable=False, index=True)
    preco = Column(Float, nullable=False, default=0.0)
    estoque_atual = Column(Float, nullable=False, default=0)
    ativo = Column(Boolean, default=True)

    imagem_path = Column(String(255), nullable=True)

    # Chave estrangeira para categoria
    categoria_id = Column(Integer, ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)

    # Relacionamento com categoria
    categoria = relationship("Categoria", back_populates="produtos")

    @property
    def imagem_url(self):
        if self.imagem_path:
            return f"/static/{self.imagem_path}"
        else:
            return "/static/img/produto-placeholder.png"
        