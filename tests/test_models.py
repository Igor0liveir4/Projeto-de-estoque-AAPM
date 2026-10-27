import pytest

from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.movimentacao import Movimentacao, Tipo_de_movimentacao
from app.models.produto import Produto
from app.models.variacoes import Variacao
from app.models.venda import ItemVenda, Venda


def test_produto_calcula_estoque_e_url_de_imagem():
    produto = Produto(nome="Camiseta", preco=25.0, imagem_path="uploads/camiseta.jpg")
    produto.variacoes = [
        Variacao(tamanho="P", cor="Azul", estoque_atual=3),
        Variacao(tamanho="M", cor="Azul", estoque_atual=4),
    ]

    assert produto.estoque_total == 7
    assert produto.imagem_url == "/static/uploads/camiseta.jpg"


def test_produto_cria_variacao_padrao_ao_adicionar_estoque():
    produto = Produto(nome="Caneca", preco=12.0)

    produto.adicionar_estoque(5)

    assert produto.estoque_total == 5
    assert len(produto.variacoes) == 1


def test_produto_nao_aceita_entrada_de_estoque_invalida():
    produto = Produto(nome="Caneca", preco=12.0)

    with pytest.raises(ValueError):
        produto.adicionar_estoque(0)


def test_produto_nao_permite_saida_acima_do_estoque():
    produto = Produto(nome="Caneca", preco=12.0)
    produto.variacoes = [Variacao(tamanho="ÚNICO", cor="Padrão", estoque_atual=2)]

    with pytest.raises(ValueError):
        produto.retirar_estoque(3)


def test_variacao_normaliza_tamanho():
    variacao = Variacao(tamanho=" m ", cor="Verde", estoque_atual=1)

    assert variacao.tamanho == "M"


def test_item_de_venda_calcula_subtotal_e_venda_desconto():
    item = ItemVenda(produto_nome="Lápis", quantidade=3, preco_unitario=2.5)
    venda = Venda(total_bruto=7.5, total_liquido=6.75)

    assert item.subtotal == 7.5
    assert venda.desconto_valor == 0.75


def test_movimentacao_calcula_valor_total():
    movimento = Movimentacao(
        tipo=Tipo_de_movimentacao.ENTRADA,
        quantidade=4,
        preco_unitario=3.25,
        produto_id=1,
        usuario_id=1,
    )

    assert movimento.valor_total == 13.0


def test_categoria_e_cliente_aceitam_dados_basicos():
    categoria = Categoria(nome="Uniformes")
    cliente = Cliente(nome="João", is_associado=True)

    assert str(categoria) == "Uniformes"
    assert cliente.is_associado is True
