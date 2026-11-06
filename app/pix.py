import base64
from io import BytesIO

import segno


PIX_RECEBEDOR = "IGOR OLIVEIRA"
PIX_CIDADE = "SAO PAULO"


def campo_pix(identificador: str, valor: str) -> str:
    return f"{identificador}{len(valor):02d}{valor}"


def crc16_ccitt(texto: str) -> str:
    crc = 0xFFFF
    for byte in texto.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def validar_chave_pix_cpf(chave: str) -> str:
    chave_normalizada = "".join(caractere for caractere in chave if caractere.isdigit())
    if len(chave_normalizada) != 11:
        raise ValueError("A chave Pix deve ser um CPF com 11 dígitos.")
    return chave_normalizada


def gerar_payload_pix(chave: str, valor_centavos: int, identificador: str = "***") -> str:
    if valor_centavos <= 0:
        raise ValueError("O valor do Pix deve ser maior que zero.")

    chave = validar_chave_pix_cpf(chave)
    identificador = identificador[:25] or "***"
    dados_conta = campo_pix("00", "br.gov.bcb.pix") + campo_pix("01", chave)
    dados_adicionais = campo_pix("05", identificador)
    valor = f"{valor_centavos // 100}.{valor_centavos % 100:02d}"

    payload = "".join((
        campo_pix("00", "01"),
        campo_pix("01", "12"),
        campo_pix("26", dados_conta),
        campo_pix("52", "0000"),
        campo_pix("53", "986"),
        campo_pix("54", valor),
        campo_pix("58", "BR"),
        campo_pix("59", PIX_RECEBEDOR),
        campo_pix("60", PIX_CIDADE),
        campo_pix("62", dados_adicionais),
        "6304",
    ))
    return payload + crc16_ccitt(payload)


def gerar_qr_pix_data_uri(payload: str) -> str:
    qr = segno.make(payload, error="M")
    imagem = BytesIO()
    qr.save(imagem, kind="svg", scale=6, border=2, dark="#111827", light="#ffffff")
    encoded = base64.b64encode(imagem.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
