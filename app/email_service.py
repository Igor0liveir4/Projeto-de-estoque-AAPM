import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from dotenv import load_dotenv

from app.whatsapp_service import gerar_pdf_comprovante

load_dotenv()


class EmailConfigurationError(ValueError):
    pass


class EmailSendError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailConfig:
    host: str
    port: int
    username: str
    password: str
    sender: str


def _configuracao() -> EmailConfig:
    host = os.getenv("SMTP_HOST", "").strip()
    port_text = os.getenv("SMTP_PORT", "587").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM_EMAIL", username).strip()

    try:
        port = int(port_text)
    except ValueError as exc:
        raise EmailConfigurationError("A porta SMTP configurada é inválida.") from exc

    if not host or not username or not password or not sender:
        raise EmailConfigurationError(
            "Configure SMTP_HOST, SMTP_USERNAME e SMTP_PASSWORD no .env."
        )
    if not 1 <= port <= 65535:
        raise EmailConfigurationError("A porta SMTP configurada é inválida.")
    _validar_endereco_email(sender)

    return EmailConfig(host, port, username, password, sender)


def _validar_endereco_email(endereco: str) -> None:
    padrao = r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
    if not re.fullmatch(padrao, endereco):
        raise ValueError("Digite um endereço de e-mail válido.")


def enviar_comprovante_email(venda, destinatario: str) -> None:
    destinatario = destinatario.strip()
    _validar_endereco_email(destinatario)
    config = _configuracao()
    pdf, nome_arquivo = gerar_pdf_comprovante(venda)

    assunto = f"Comprovante da venda #{venda.id:04d} — AAPM"
    data_venda = venda.criado_em.strftime("%d/%m/%Y %H:%M") if venda.criado_em else "—"
    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = config.sender
    mensagem["To"] = destinatario
    mensagem.set_content(
        f"Comprovante da venda #{venda.id:04d}\n"
        f"AAPM — Ponto de Venda\n"
        f"Data: {data_venda}\n"
        f"Total: R$ {venda.total_liquido:.2f}\n\n"
        "O comprovante completo está anexado a este e-mail.\n"
        "Obrigado pela compra!"
    )
    mensagem.add_attachment(
        pdf,
        maintype="application",
        subtype="pdf",
        filename=nome_arquivo,
    )

    try:
        with smtplib.SMTP(config.host, config.port, timeout=30) as servidor:
            servidor.ehlo()
            servidor.starttls(context=ssl.create_default_context())
            servidor.ehlo()
            servidor.login(config.username, config.password)
            servidor.send_message(mensagem)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailSendError(
            "Não foi possível enviar o e-mail. Verifique a conexão e as configurações SMTP."
        ) from exc
