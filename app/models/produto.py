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
    def estoque_total(self) -> int:
        """Saldo consolidado de todas as variações do produto."""
        return sum(variacao.estoque_atual for variacao in self.variacoes)

    def adicionar_estoque(self, quantidade: int) -> None:
        """Adiciona saldo à variação padrão, criada quando necessário."""
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        variacao_padrao = next(
            (v for v in self.variacoes if v.tamanho == "Único" and v.cor == "Padrão"),
            None,
        )
        if variacao_padrao is None:
            from app.models.variacoes import Variacao
            variacao_padrao = Variacao(tamanho="Único", cor="Padrão", estoque_atual=0)
            self.variacoes.append(variacao_padrao)
        variacao_padrao.estoque_atual += quantidade

    def retirar_estoque(self, quantidade: int) -> None:
        """Baixa saldo das variações, sem permitir estoque negativo."""
        if quantidade <= 0 or quantidade > self.estoque_total:
            raise ValueError("Estoque insuficiente.")

        restante = quantidade
        for variacao in sorted(self.variacoes, key=lambda v: v.id or 0):
            baixa = min(variacao.estoque_atual, restante)
            variacao.estoque_atual -= baixa
            restante -= baixa
            if restante == 0:
                break
        
