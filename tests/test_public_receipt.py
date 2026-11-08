from datetime import datetime, timedelta, timezone

from jose import jwt

from app.auth import ALGORITHM, SECRET_KEY
from app.models.cliente import Cliente
from app.models.venda import ItemVenda, Venda


def _criar_venda_compartilhavel(db_session):
    cliente = Cliente(nome="Cliente Privado", email="privado@example.test")
    venda = Venda(
        cliente=cliente,
        total_bruto=25,
        total_liquido=25,
        formas_pagamento="[]",
        itens=[
            ItemVenda(
                produto_nome="Produto de Teste",
                quantidade=1,
                preco_unitario=25,
            )
        ],
    )
    db_session.add(venda)
    db_session.commit()
    return venda


def _token_venda(venda_id):
    return jwt.encode({
        "purpose": "public_sale_receipt",
        "sale_id": venda_id,
        "jti": "token-de-teste",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }, SECRET_KEY, algorithm=ALGORITHM)


def test_comprovante_publico_abre_sem_login_e_esconde_dados_do_cliente(client, db_session):
    venda = _criar_venda_compartilhavel(db_session)

    resposta = client.get(
        f"/pdv/comprovante-publico/{venda.id}",
        params={"token": _token_venda(venda.id)},
    )

    assert resposta.status_code == 200
    assert "Produto de Teste" in resposta.text
    assert "Cliente Privado" not in resposta.text
    assert "privado@example.test" not in resposta.text
    assert resposta.headers["cache-control"] == "private, no-store"
    assert resposta.headers["x-robots-tag"] == "noindex, nofollow"


def test_comprovante_publico_rejeita_token_de_outra_venda(client, db_session):
    venda = _criar_venda_compartilhavel(db_session)
    token = _token_venda(venda.id + 1)

    resposta = client.get(
        f"/pdv/comprovante-publico/{venda.id}",
        params={"token": token},
    )

    assert resposta.status_code == 404


def test_comprovante_publico_rejeita_token_expirado(client, db_session):
    venda = _criar_venda_compartilhavel(db_session)
    token = jwt.encode({
        "purpose": "public_sale_receipt",
        "sale_id": venda.id,
        "jti": "token-expirado",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }, SECRET_KEY, algorithm=ALGORITHM)

    resposta = client.get(
        f"/pdv/comprovante-publico/{venda.id}",
        params={"token": token},
    )

    assert resposta.status_code == 404


def test_comprovante_autenticado_inclui_link_publico_com_dominio_configurado(
    client, db_session, monkeypatch
):
    venda = _criar_venda_compartilhavel(db_session)
    sessao = jwt.encode({
        "sub": "operador@example.test",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }, SECRET_KEY, algorithm=ALGORITHM)
    client.cookies.set("access_token", sessao)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://loja.example.test")

    resposta = client.get(f"/pdv/venda/{venda.id}")

    assert resposta.status_code == 200
    assert "https://loja.example.test/pdv/comprovante-publico/" in resposta.text
