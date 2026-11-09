import io
import os
import re
from dataclasses import dataclass
from html import escape

import httpx
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

load_dotenv()


class WhatsappConfigurationError(ValueError):
    pass


class WhatsappSendError(RuntimeError):
    pass


@dataclass(frozen=True)
class WhatsappConfig:
    access_token: str
    phone_number_id: str
    api_version: str
    template_name: str
    template_language: str


def _configuracao() -> WhatsappConfig:
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    api_version = os.getenv("WHATSAPP_API_VERSION", "v27.0").strip()
    template_name = os.getenv("WHATSAPP_TEMPLATE_NAME", "comprovante_venda").strip()
    template_language = os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "pt_BR").strip()

    if not access_token or not phone_number_id:
        raise WhatsappConfigurationError(
            "Configure WHATSAPP_ACCESS_TOKEN e WHATSAPP_PHONE_NUMBER_ID no .env."
        )
    if not re.fullmatch(r"\d+", phone_number_id):
        raise WhatsappConfigurationError("O ID do número WhatsApp deve conter apenas dígitos.")
    if not re.fullmatch(r"v\d+\.\d+", api_version):
        raise WhatsappConfigurationError("A versão da API WhatsApp configurada é inválida.")
    if not re.fullmatch(r"[a-z0-9_]{1,512}", template_name):
        raise WhatsappConfigurationError("O nome do modelo WhatsApp configurado é inválido.")
    if not re.fullmatch(r"[a-z]{2}_[A-Z]{2}", template_language):
        raise WhatsappConfigurationError("O idioma do modelo WhatsApp configurado é inválido.")

    return WhatsappConfig(
        access_token=access_token,
        phone_number_id=phone_number_id,
        api_version=api_version,
        template_name=template_name,
        template_language=template_language,
    )


def _normalizar_telefone(telefone: str) -> str:
    telefone = telefone.strip()
    if telefone.startswith("+") and not telefone.startswith("+55"):
        raise ValueError("Digite um telefone brasileiro válido com DDD.")
    digitos = re.sub(r"\D", "", telefone)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        numero = digitos
    elif len(digitos) in (10, 11):
        numero = f"55{digitos}"
    else:
        raise ValueError("Digite um telefone brasileiro válido com DDD.")
    return numero


def gerar_pdf_comprovante(venda) -> tuple[bytes, str]:
    buffer = io.BytesIO()
    numero_venda = f"{venda.id:04d}"
    nome_arquivo = f"comprovante-venda-{numero_venda}.pdf"
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Comprovante da venda #{numero_venda}",
        author="AAPM - Ponto de Venda",
    )
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(
        name="ReceiptTitle",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#12345a"),
        alignment=TA_CENTER,
        spaceAfter=4,
    ))
    estilos.add(ParagraphStyle(
        name="ReceiptSubtitle",
        parent=estilos["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#526174"),
        alignment=TA_CENTER,
        spaceAfter=16,
    ))
    estilos.add(ParagraphStyle(
        name="ReceiptSection",
        parent=estilos["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#12345a"),
        spaceBefore=12,
        spaceAfter=6,
    ))
    estilos.add(ParagraphStyle(
        name="ReceiptCell",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        splitLongWords=True,
    ))
    estilos.add(ParagraphStyle(
        name="ReceiptCellRight",
        parent=estilos["ReceiptCell"],
        alignment=TA_RIGHT,
    ))

    story = [
        Paragraph("AAPM - Ponto de Venda", estilos["ReceiptTitle"]),
        Paragraph(f"Comprovante de venda #{numero_venda}", estilos["ReceiptSubtitle"]),
    ]
    criado_em = venda.criado_em.strftime("%d/%m/%Y %H:%M") if venda.criado_em else "—"
    cliente = escape(venda.cliente.nome) if venda.cliente else "Não identificado"
    operador = escape(venda.usuario.nome) if venda.usuario else "—"
    detalhes = [
        ["Data / Hora", criado_em, "Cliente", cliente],
        ["Operador", operador, "", ""],
    ]
    tabela_detalhes = Table(
        detalhes,
        colWidths=[25 * mm, 48 * mm, 22 * mm, 59 * mm],
    )
    tabela_detalhes.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#526174")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#526174")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([tabela_detalhes, Paragraph("Itens", estilos["ReceiptSection"])])

    linhas_itens = [[
        Paragraph("<b>Produto</b>", estilos["ReceiptCell"]),
        Paragraph("<b>Qtd.</b>", estilos["ReceiptCellRight"]),
        Paragraph("<b>Unitário</b>", estilos["ReceiptCellRight"]),
        Paragraph("<b>Subtotal</b>", estilos["ReceiptCellRight"]),
    ]]
    for item in venda.itens:
        linhas_itens.append([
            Paragraph(escape(item.produto_nome), estilos["ReceiptCell"]),
            Paragraph(str(item.quantidade), estilos["ReceiptCellRight"]),
            Paragraph(f"R$ {item.preco_unitario:.2f}", estilos["ReceiptCellRight"]),
            Paragraph(f"R$ {item.subtotal:.2f}", estilos["ReceiptCellRight"]),
        ])
    tabela_itens = Table(
        linhas_itens,
        colWidths=[91 * mm, 14 * mm, 27 * mm, 28 * mm],
        repeatRows=1,
    )
    tabela_itens.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf1f8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5deea")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabela_itens)

    story.append(Paragraph("Totais", estilos["ReceiptSection"]))
    linhas_totais = []
    if venda.desconto_percentual and venda.desconto_percentual > 0:
        linhas_totais.append(["Subtotal bruto", f"R$ {venda.total_bruto:.2f}"])
        linhas_totais.append([
            f"Desconto de associado ({venda.desconto_percentual:g}%)",
            f"- R$ {venda.desconto_valor:.2f}",
        ])
    linhas_totais.append(["TOTAL", f"R$ {venda.total_liquido:.2f}"])
    tabela_totais = Table(linhas_totais, colWidths=[120 * mm, 40 * mm], hAlign="RIGHT")
    tabela_totais.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#12345a")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#9aabc0")),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
    ]))
    story.extend([tabela_totais, Paragraph("Formas de pagamento", estilos["ReceiptSection"])])

    linhas_pagamentos = []
    for pagamento in venda.pagamentos:
        descricao = escape(pagamento["tipo"])
        if pagamento.get("parcelas"):
            descricao += f" ({pagamento['parcelas']}x)"
        if pagamento.get("txid"):
            descricao += f" - Ref. Pix: {escape(pagamento['txid'])}"
        if pagamento.get("confirmado_manualmente"):
            descricao += " - Confirmado manualmente pelo operador"
        linhas_pagamentos.append(
            f"{descricao}: R$ {pagamento['valor']:.2f}"
        )
        if pagamento.get("troco", 0) > 0:
            linhas_pagamentos.append(
                f"Recebido: R$ {pagamento['recebido']:.2f} - "
                f"Troco: R$ {pagamento['troco']:.2f}"
            )
    story.append(Paragraph("<br/>".join(linhas_pagamentos) or "Não informado", estilos["ReceiptCell"]))
    if venda.observacao:
        story.extend([
            Paragraph("Observação", estilos["ReceiptSection"]),
            Paragraph(escape(venda.observacao), estilos["ReceiptCell"]),
        ])
    story.extend([
        Spacer(1, 14),
        Paragraph("Obrigado pela preferência!", estilos["ReceiptSubtitle"]),
    ])
    documento.build(story)
    return buffer.getvalue(), nome_arquivo


def enviar_comprovante_whatsapp(venda, telefone: str) -> str:
    config = _configuracao()
    destinatario = _normalizar_telefone(telefone)
    pdf, nome_arquivo = gerar_pdf_comprovante(venda)
    base_url = (
        f"https://graph.facebook.com/{config.api_version}/"
        f"{config.phone_number_id}"
    )
    headers = {"Authorization": f"Bearer {config.access_token}"}

    try:
        with httpx.Client(timeout=30) as cliente:
            resposta_upload = cliente.post(
                f"{base_url}/media",
                headers=headers,
                data={"messaging_product": "whatsapp"},
                files={"file": (nome_arquivo, pdf, "application/pdf")},
            )
            dados_upload = _ler_resposta_meta(resposta_upload, "upload do PDF")
            media_id = dados_upload.get("id")
            if not isinstance(media_id, str) or not media_id:
                raise WhatsappSendError("A Meta não retornou o identificador do PDF enviado.")

            corpo = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": destinatario,
                "type": "template",
                "template": {
                    "name": config.template_name,
                    "language": {"code": config.template_language},
                    "components": [
                        {
                            "type": "header",
                            "parameters": [
                                {
                                    "type": "document",
                                    "document": {
                                        "id": media_id,
                                        "filename": nome_arquivo,
                                    },
                                }
                            ],
                        },
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": f"#{venda.id:04d}"},
                                {"type": "text", "text": f"R$ {venda.total_liquido:.2f}"},
                            ],
                        },
                    ],
                },
            }
            resposta_envio = cliente.post(
                f"{base_url}/messages",
                headers={**headers, "Content-Type": "application/json"},
                json=corpo,
            )
            dados_envio = _ler_resposta_meta(resposta_envio, "envio da mensagem")
    except httpx.TimeoutException as exc:
        raise WhatsappSendError(
            "A Meta demorou para responder. Verifique o WhatsApp antes de tentar novamente."
        ) from exc
    except httpx.HTTPError as exc:
        raise WhatsappSendError(
            "Não foi possível conectar à API do WhatsApp. Tente novamente."
        ) from exc

    mensagens = dados_envio.get("messages")
    if not isinstance(mensagens, list) or not mensagens or not mensagens[0].get("id"):
        raise WhatsappSendError("A Meta não confirmou o recebimento da mensagem.")
    return str(mensagens[0]["id"])


def _ler_resposta_meta(resposta: httpx.Response, etapa: str) -> dict:
    try:
        dados = resposta.json()
    except ValueError as exc:
        raise WhatsappSendError(
            f"A API do WhatsApp retornou uma resposta inválida durante {etapa}."
        ) from exc

    if resposta.is_error:
        erro = dados.get("error", {}) if isinstance(dados, dict) else {}
        mensagem = erro.get("message") if isinstance(erro, dict) else None
        if isinstance(mensagem, str) and mensagem:
            raise WhatsappSendError(f"A Meta recusou {etapa}: {mensagem[:300]}")
        raise WhatsappSendError(f"A Meta recusou {etapa} (HTTP {resposta.status_code}).")
    if not isinstance(dados, dict):
        raise WhatsappSendError(f"A API do WhatsApp retornou uma resposta inválida durante {etapa}.")
    return dados
