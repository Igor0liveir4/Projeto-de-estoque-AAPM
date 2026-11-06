import base64
import json

import pytest
from jose import jwt

from app.auth import ALGORITHM, SECRET_KEY
from app.controllers.pdv_controller import gerar_pix_venda
from app.pix import crc16_ccitt, gerar_payload_pix, gerar_qr_pix_data_uri


def test_payload_pix_inclui_valor_e_crc():
    payload = gerar_payload_pix("529.982.247-25", 6075)

    assert "540560.75" in payload
    assert "5802BR" in payload
    assert payload[-8:-4] == "6304"
    assert payload[-4:] == crc16_ccitt(payload[:-4])


def test_gerador_qr_pix_retorna_svg_data_uri():
    payload = gerar_payload_pix("52998224725", 6075)

    data_uri = gerar_qr_pix_data_uri(payload)

    assert data_uri.startswith("data:image/svg+xml;base64,")
    svg = base64.b64decode(data_uri.split(",", 1)[1])
    assert b"<svg " in svg[:100]


def test_rota_pix_gera_qr_local_e_token_vinculado_aos_dados(monkeypatch):
    monkeypatch.setenv("PIX_KEY", "52998224725")
    pagamentos_json = '[{"tipo":"Pix","valor":60.75}]'
    carrinho_json = '[{"produto_id":1,"variacao_id":2,"quantidade":1}]'

    resposta = gerar_pix_venda(
        pagamentos_json=pagamentos_json,
        carrinho_json=carrinho_json,
        usuario={"sub": "operador@example.test"},
    )
    dados = json.loads(resposta.body)
    token = jwt.decode(
        dados["confirmacao_token"],
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    assert resposta.headers["cache-control"] == "no-store"
    assert dados["valor_centavos"] == 6075
    assert dados["qr_code"].startswith("data:image/svg+xml;base64,")
    assert dados["txid"].startswith("PEDIDO")
    assert dados["txid"] in dados["payload"]
    assert token["purpose"] == "pdv_pix_confirmation"
    assert token["sub"] == "operador@example.test"
    assert token["pix_centavos"] == 6075
    assert token["txid"] == dados["txid"]


@pytest.mark.parametrize(
    ("chave", "valor_centavos"),
    [("123", 100), ("52998224725", 0), ("52998224725", -1)],
)
def test_gerador_pix_rejeita_chave_ou_valor_invalido(chave, valor_centavos):
    with pytest.raises(ValueError):
        gerar_payload_pix(chave, valor_centavos)
