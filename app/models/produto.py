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
        """Quantidade disponível, calculada a partir das variações do produto."""
        return sum(variacao.estoque_atual or 0 for variacao in self.variacoes)

    @estoque_total.setter
    def estoque_total(self, novo_total):
        """Ajusta o saldo pela variação padrão usada nos produtos sem opções."""
        novo_total = int(novo_total)
        if novo_total < 0:
            raise ValueError("O estoque não pode ser negativo.")

        variacao_padrao = next(
            (
                variacao for variacao in self.variacoes
                if variacao.tamanho == "Único" and variacao.cor == "Padrão"
            ),
            None,
        )

        if variacao_padrao is None:
            from app.models.variacoes import Variacao
            variacao_padrao = Variacao(tamanho="Único", cor="Padrão", estoque_atual=0)
            self.variacoes.append(variacao_padrao)

        variacao_padrao.estoque_atual += novo_total - self.estoque_total
