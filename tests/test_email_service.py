from datetime import datetime

import pytest

from app.email_service import (
    EmailConfigurationError,
    _validar_endereco_email,
    enviar_comprovante_email,
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


def test_envia_email_com_pdf_anexado(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "loja@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "senha-teste")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "loja@example.test")
    chamadas = {}

    class ServidorFalso:
        def __init__(self, host, port, timeout):
            chamadas["conexao"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ehlo(self):
            chamadas["ehlo"] = chamadas.get("ehlo", 0) + 1

        def starttls(self, context):
            chamadas["tls"] = context

        def login(self, usuario, senha):
            chamadas["login"] = (usuario, senha)

        def send_message(self, mensagem):
            chamadas["mensagem"] = mensagem

    monkeypatch.setattr("app.email_service.smtplib.SMTP", ServidorFalso)

    enviar_comprovante_email(_venda_teste(), "cliente@example.test")

    assert chamadas["conexao"] == ("smtp.example.test", 587, 30)
    assert chamadas["login"] == ("loja@example.test", "senha-teste")
    mensagem = chamadas["mensagem"]
    assert mensagem["To"] == "cliente@example.test"
    assert mensagem["Subject"] == "Comprovante da venda #0013 — AAPM"
    anexos = list(mensagem.iter_attachments())
    assert len(anexos) == 1
    assert anexos[0].get_content_type() == "application/pdf"
    assert anexos[0].get_filename() == "comprovante-venda-0013.pdf"
    assert anexos[0].get_payload(decode=True).startswith(b"%PDF-")


def test_rejeita_configuracao_smtp_ausente(monkeypatch):
    for nome in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"):
        monkeypatch.delenv(nome, raising=False)

    with pytest.raises(EmailConfigurationError):
        enviar_comprovante_email(_venda_teste(), "cliente@example.test")


@pytest.mark.parametrize("endereco", ["invalido", "cliente@", "cliente@example.test\nBcc:spam@example.test"])
def test_rejeita_endereco_de_email_invalido(endereco):
    with pytest.raises(ValueError, match="endereço de e-mail válido"):
        _validar_endereco_email(endereco)


def test_rota_email_envia_comprovante(client, db_session, monkeypatch):
    from datetime import timedelta, timezone

    from jose import jwt

    from app.auth import ALGORITHM, SECRET_KEY
    from app.models.venda import Venda

    venda = Venda(total_bruto=10, total_liquido=10, formas_pagamento="[]")
    db_session.add(venda)
    db_session.commit()
    token_sessao = jwt.encode({
        "sub": "operador@example.test",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }, SECRET_KEY, algorithm=ALGORITHM)
    client.cookies.set("access_token", token_sessao)
    chamadas = []
    monkeypatch.setattr(
        "app.controllers.pdv_controller.enviar_comprovante_email",
        lambda venda, destinatario: chamadas.append((venda.id, destinatario)),
    )

    resposta = client.post(
        f"/pdv/venda/{venda.id}/enviar-email",
        json={"destinatario": "cliente@example.test"},
    )

    assert resposta.status_code == 200
    assert chamadas == [(venda.id, "cliente@example.test")]
