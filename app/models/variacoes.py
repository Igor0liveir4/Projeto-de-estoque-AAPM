from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from app.database import Base

class Variacao(Base):
    __tablename__ = "variacoes"
    __table_args__ = (
        UniqueConstraint("produto_id", "tamanho", "cor", name="uq_variacao_produto_tamanho_cor"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Relacionamento obrigatório com o Produto Base
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False)
    
    # Atributos da variação
    tamanho = Column(String(10), nullable=False)  # Ex: 'P', 'M', 'G', 'GG'
    cor = Column(String(50), nullable=False)      # Ex: 'Azul', 'Preto'
    
    # O estoque sai do Produto e vem para cá!
    estoque_atual = Column(Integer, nullable=False, default=0)

    # Relacionamento de volta para o Produto
    produto = relationship("Produto", back_populates="variacoes")

    @validates("tamanho")
    def normalizar_tamanho(self, _chave, tamanho: str) -> str:
        # Impede que "m" e "M" virem opções diferentes no PDV.
        return tamanho.strip().upper()
