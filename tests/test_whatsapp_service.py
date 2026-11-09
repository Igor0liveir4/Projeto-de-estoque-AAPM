from datetime import datetime
from datetime import timedelta, timezone

import pytest
from jose import jwt

from app.auth import ALGORITHM, SECRET_KEY
from app.models.venda import Venda
from app.whatsapp_service import (
    WhatsappConfigurationError,
    _normalizar_telefone,
    enviar_comprovante_whatsapp,
    gerar_pdf_comprovante,
)


def _venda_teste():
    return type("VendaTeste", (), {
        "id": 13,
        "criado_em": datetime(2026, 11, 6, 3, 54),
        "cliente": type("ClienteTeste", (), {"nome": "Cliente de Teste"})(),
        "usuario": type("UsuarioTeste", (), {"nome": "Operador"})(),
        "itens": [
            type("ItemTeste", (), {
                "produto_nome": "Camiseta azul",
                "quantidade": 2,
                "preco_unitario": 28.0,
                "subtotal": 56.0,
            })()
        ],
        "pagamentos": [
            {"tipo": "Cartão de Débito", "valor": 56.0, "recebido": 56.0, "troco": 0.0}
        ],
        "total_bruto": 56.0,
        "total_liquido": 56.0,
        "desconto_percentual": 0,
        "desconto_valor": 0,
        "observacao": None,
    })()


def test_gera_pdf_do_comprovante():
    pdf, nome = gerar_pdf_comprovante(_venda_teste())

    assert nome == "comprovante-venda-0013.pdf"
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 500


def test_envia_pdf_anexado_com_modelo_meta(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token-teste")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1234567890")
    chamadas = []

    class Resposta:
        is_error = False
        status_code = 200

        def __init__(self, dados):
            self.dados = dados

        def json(self):
            return self.dados

    class ClienteFalso:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, **kwargs):
            chamadas.append((url, kwargs))
            if url.endswith("/media"):
                return Resposta({"id": "media-123"})
            return Resposta({"messages": [{"id": "wamid.123"}]})

    monkeypatch.setattr(
        "app.whatsapp_service.httpx.Client",
        lambda **kwargs: ClienteFalso(),
    )

    message_id = enviar_comprovante_whatsapp(_venda_teste(), "(11) 99999-9999")

    assert message_id == "wamid.123"
    assert len(chamadas) == 2
    upload_url, upload_args = chamadas[0]
    assert upload_url.endswith("/v27.0/1234567890/media")
    assert upload_args["headers"]["Authorization"] == "Bearer token-teste"
    assert upload_args["data"] == {"messaging_product": "whatsapp"}
    nome, conteudo, mime = upload_args["files"]["file"]
    assert nome == "comprovante-venda-0013.pdf"
    assert conteudo.startswith(b"%PDF-")
    assert mime == "application/pdf"

    envio_url, envio_args = chamadas[1]
    assert envio_url.endswith("/v27.0/1234567890/messages")
    corpo = envio_args["json"]
    assert corpo["to"] == "5511999999999"
    assert corpo["template"]["name"] == "comprovante_venda"
    assert corpo["template"]["components"][0]["parameters"][0]["document"]["id"] == "media-123"
    assert corpo["template"]["components"][1]["parameters"][0]["text"] == "#0013"


def test_rejeita_configuracao_ausente(monkeypatch):
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)

    with pytest.raises(WhatsappConfigurationError):
        enviar_comprovante_whatsapp(_venda_teste(), "11999999999")


@pytest.mark.parametrize("telefone", ["123", "119999999999", "+1 415 555 2671"])
def test_rejeita_telefone_invalido(telefone):
    with pytest.raises(ValueError, match="telefone brasileiro válido"):
        _normalizar_telefone(telefone)


def test_rota_whatsapp_exige_autorizacao_do_cliente(client, db_session, monkeypatch):
    venda = Venda(total_bruto=10, total_liquido=10, formas_pagamento="[]")
    db_session.add(venda)
    db_session.commit()
    token_sessao = jwt.encode({
        "sub": "operador@example.test",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }, SECRET_KEY, algorithm=ALGORITHM)
    client.cookies.set("access_token", token_sessao)
    chamada = []
    monkeypatch.setattr(
        "app.controllers.pdv_controller.enviar_comprovante_whatsapp",
        lambda venda, telefone: chamada.append((venda.id, telefone)) or "wamid.teste",
    )

    resposta = client.post(
        f"/pdv/venda/{venda.id}/enviar-whatsapp",
        json={"telefone": "(11) 99999-9999", "cliente_autorizou": False},
    )

    assert resposta.status_code == 400
    assert chamada == []


def test_rota_whatsapp_envia_comprovante_com_autorizacao(
    client, db_session, monkeypatch
):
    venda = Venda(total_bruto=10, total_liquido=10, formas_pagamento="[]")
    db_session.add(venda)
    db_session.commit()
    token_sessao = jwt.encode({
        "sub": "operador@example.test",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }, SECRET_KEY, algorithm=ALGORITHM)
    client.cookies.set("access_token", token_sessao)
    monkeypatch.setattr(
        "app.controllers.pdv_controller.enviar_comprovante_whatsapp",
        lambda venda, telefone: "wamid.teste",
    )

    resposta = client.post(
        f"/pdv/venda/{venda.id}/enviar-whatsapp",
        json={"telefone": "11999999999", "cliente_autorizou": True},
    )

    assert resposta.status_code == 200
    assert resposta.json()["message_id"] == "wamid.teste"
