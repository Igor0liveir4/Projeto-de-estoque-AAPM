# O PDV funciona assim:
# 1. GET /pdv        → tela com produtos + campo de cliente
# 2. O carrinho vive inteiro no JavaScript (sessionStorage)
# 3. POST /pdv/finalizar → recebe um JSON com os itens
#                          cria Venda + ItensVenda + baixa estoque
# ============================================================

import json
import hashlib
import math
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError, jwt

from app.database import get_db
from app.models.venda import Venda, ItemVenda
from app.models.produto import Produto
from app.models.variacoes import Variacao
from app.models.cliente import Cliente
from app.auth import ALGORITHM, SECRET_KEY, get_usuario_logado
from app.pagination import paginar
from app.pix import gerar_payload_pix, gerar_qr_pix_data_uri, validar_chave_pix_cpf

router = APIRouter(prefix="/pdv", tags=["PDV"])
templates = Jinja2Templates(directory="app/templates")

DESCONTO_ASSOCIADO = 10.0  # percentual fixo


def _hash_form_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pix_configurado() -> bool:
    try:
        validar_chave_pix_cpf(os.getenv("PIX_KEY", ""))
    except ValueError:
        return False
    return True


@router.get("/")
def tela_pdv(
    request: Request,
    busca: str = "",
    pagina: int = 1,
    por_pagina: int = 16,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """
    Carrega a tela do PDV com todos os produtos ativos
    e a lista de clientes para o campo de busca.
    """
    query_produtos = (
        db.query(Produto)
        .join(Produto.variacoes)
        .filter(Produto.ativo == True)
        .group_by(Produto.id)
        .having(func.sum(Variacao.estoque_atual) > 0)
    )

    if busca:
        query_produtos = query_produtos.filter(Produto.nome.ilike(f"%{busca}%"))

    resultado = paginar(query_produtos.order_by(Produto.nome), pagina, por_pagina)
    clientes  = (
        db.query(Cliente)
        .filter(Cliente.ativo == True)
        .order_by(Cliente.nome)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "pdv/index.html",
        {
            "request":             request,
            "usuario":             usuario,
            "produtos":            resultado.itens,
            "clientes":            clientes,
            "desconto_associado":  DESCONTO_ASSOCIADO,
            "busca":               busca,
            "pagina":              resultado.atual,
            "por_pagina":          resultado.por_pagina,
            "total_paginas":       resultado.total_paginas,
            "total_produtos":      resultado.total_itens,
            "pix_configurado":     _pix_configurado(),
        }
    )


@router.post("/pix")
def gerar_pix_venda(
    pagamentos_json: str = Form(...),
    carrinho_json: str = Form(...),
    usuario=Depends(get_usuario_logado),
):
    chave_pix = os.getenv("PIX_KEY", "")
    if not chave_pix:
        raise HTTPException(status_code=503, detail="A chave Pix não está configurada.")
    if not SECRET_KEY or not ALGORITHM:
        raise HTTPException(status_code=503, detail="A assinatura segura do pagamento não está configurada.")

    try:
        pagamentos = json.loads(pagamentos_json)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Dados de pagamento inválidos.")

    if not isinstance(pagamentos, list):
        raise HTTPException(status_code=400, detail="Dados de pagamento inválidos.")

    valor_pix_centavos = 0
    txid_pix = f"PEDIDO{secrets.token_hex(5).upper()}"
    try:
        for pagamento in pagamentos:
            if not isinstance(pagamento, dict) or pagamento.get("tipo") != "Pix":
                continue
            valor = float(pagamento.get("valor") or 0)
            if not math.isfinite(valor) or valor <= 0:
                raise ValueError
            valor_pix_centavos += round(valor * 100)
        payload = gerar_payload_pix(chave_pix, valor_pix_centavos, txid_pix)
        qr_data_uri = gerar_qr_pix_data_uri(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    token = jwt.encode({
        "purpose": "pdv_pix_confirmation",
        "sub": str(usuario.get("sub", "")),
        "cart_hash": _hash_form_value(carrinho_json),
        "payments_hash": _hash_form_value(pagamentos_json),
        "pix_centavos": valor_pix_centavos,
        "txid": txid_pix,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }, SECRET_KEY, algorithm=ALGORITHM)

    return JSONResponse(
        {
            "payload": payload,
            "qr_code": qr_data_uri,
            "valor_centavos": valor_pix_centavos,
            "txid": txid_pix,
            "confirmacao_token": token,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.post("/finalizar")
def finalizar_venda(
    request: Request,
    carrinho_json: str = Form(...),  # JSON serializado pelo JS
    cliente_id: int    = Form(0),    # 0 = sem cliente identificado
    observacao: str    = Form(""),
    pagamentos_json: str = Form("[]"),
    pix_confirmacao_token: str = Form(""),
    pix_txid: str = Form(""),
    db: Session        = Depends(get_db),
    usuario            = Depends(get_usuario_logado)
):
    """
    Recebe o carrinho como JSON, valida e persiste a venda.

    Formato esperado do carrinho_json:
    [
        {"produto_id": 1, "variacao_id": 3, "quantidade": 2}
    ]
    """
    try:
        itens = json.loads(carrinho_json)
    except (json.JSONDecodeError, ValueError):
        return RedirectResponse(url="/pdv?erro=json", status_code=302)

    try:
        pagamentos = json.loads(pagamentos_json or "[]")
    except (json.JSONDecodeError, ValueError):
        return RedirectResponse(url="/pdv?erro=json", status_code=302)

    if not itens:
        return RedirectResponse(url="/pdv?erro=vazio", status_code=302)

    if not isinstance(pagamentos, list):
        return RedirectResponse(url="/pdv?erro=pagamento", status_code=302)

    tipos_pagamento = {
        "Cartão",
        "Cartão de Crédito",
        "Cartão de Débito",
        "Pix",
        "Dinheiro",
        "Transferência",
    }
    pagamentos_recebidos = []
    for pagamento in pagamentos:
        if not isinstance(pagamento, dict):
            continue
        try:
            tipo = str(pagamento.get("tipo", "")).strip()
            valor = float(pagamento.get("valor") or 0)
        except (TypeError, ValueError):
            return RedirectResponse(url="/pdv?erro=pagamento", status_code=302)
        if not tipo or valor <= 0:
            continue
        if tipo not in tipos_pagamento or not math.isfinite(valor):
            return RedirectResponse(url="/pdv?erro=pagamento", status_code=302)

        registro = {"tipo": tipo, "valor": round(valor, 2)}
        if tipo == "Cartão de Crédito":
            try:
                parcelas = int(pagamento.get("parcelas") or 1)
            except (TypeError, ValueError):
                return RedirectResponse(url="/pdv?erro=pagamento", status_code=302)
            if not 1 <= parcelas <= 12:
                return RedirectResponse(url="/pdv?erro=pagamento", status_code=302)
            registro["parcelas"] = parcelas
        pagamentos_recebidos.append(registro)

    valor_pix_centavos = sum(
        round(pagamento["valor"] * 100)
        for pagamento in pagamentos_recebidos
        if pagamento["tipo"] == "Pix"
    )
    if valor_pix_centavos:
        try:
            confirmacao = jwt.decode(
                pix_confirmacao_token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
            )
        except (JWTError, TypeError):
            return RedirectResponse(url="/pdv?erro=pix_confirmacao", status_code=302)

        if (
            confirmacao.get("purpose") != "pdv_pix_confirmation"
            or confirmacao.get("sub") != str(usuario.get("sub", ""))
            or confirmacao.get("pix_centavos") != valor_pix_centavos
            or confirmacao.get("txid") != pix_txid
            or confirmacao.get("cart_hash") != _hash_form_value(carrinho_json)
            or confirmacao.get("payments_hash") != _hash_form_value(pagamentos_json)
        ):
            return RedirectResponse(url="/pdv?erro=pix_confirmacao", status_code=302)

    # Busca o cliente e verifica se é associado
    cliente             = None
    desconto_percentual = 0.0

    if cliente_id:
        cliente = db.query(Cliente).filter(
            Cliente.id == cliente_id,
            Cliente.ativo == True
        ).first()

        if cliente and cliente.is_associado:
            desconto_percentual = DESCONTO_ASSOCIADO

    # ── Valida estoque e calcula totais ──────────────────────
    total_bruto = 0.0
    itens_validados = []
    itens_normalizados = {}

    for item in itens:
        try:
            produto_id = int(item["produto_id"])
            variacao_id = int(item["variacao_id"])
            qtd = int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            return RedirectResponse(url="/pdv?erro=json", status_code=302)

        chave = (produto_id, variacao_id)
        itens_normalizados[chave] = itens_normalizados.get(chave, 0) + qtd

    for (produto_id, variacao_id), qtd in itens_normalizados.items():
        produto = db.query(Produto).filter(
            Produto.id == produto_id,
            Produto.ativo == True
        ).first()

        if not produto:
            return RedirectResponse(
                url=f"/pdv?erro=produto_inexistente&id={produto_id}",
                status_code=302
            )

        variacao = db.query(Variacao).filter(
            Variacao.id == variacao_id,
            Variacao.produto_id == produto.id
        ).with_for_update().first()

        if not variacao:
            return RedirectResponse(
                url="/pdv?erro=variacao_inexistente",
                status_code=302
            )

        if qtd <= 0:
            return RedirectResponse(url="/pdv?erro=quantidade", status_code=302)

        if variacao.estoque_atual < qtd:
            return RedirectResponse(
                url=f"/pdv?erro=estoque&produto={produto.nome}",
                status_code=302
            )

        subtotal    = produto.preco * qtd
        total_bruto += subtotal

        itens_validados.append({
            "produto":       produto,
            "variacao":      variacao,
            "quantidade":    qtd,
            "preco":         produto.preco,
            "produto_nome":  f"{produto.nome} — {variacao.tamanho} / {variacao.cor}",
        })

    # ── Calcula desconto e total final
    desconto_valor = total_bruto * (desconto_percentual / 100)
    total_liquido  = total_bruto - desconto_valor
    restante = round(total_liquido, 2)
    pagamentos_validos = []
    for pagamento in pagamentos_recebidos:
        valor_recebido = pagamento["valor"]
        valor_aplicado = round(min(valor_recebido, restante), 2)
        excedente = round(valor_recebido - valor_aplicado, 2)
        if excedente > 0 and pagamento["tipo"] != "Dinheiro":
            return RedirectResponse(url="/pdv?erro=pagamento", status_code=302)

        registro = {
            "tipo": pagamento["tipo"],
            "valor": valor_aplicado,
            "recebido": valor_recebido,
            "troco": excedente,
        }
        if "parcelas" in pagamento:
            registro["parcelas"] = pagamento["parcelas"]
        if pagamento["tipo"] == "Pix":
            registro["txid"] = pix_txid
            registro["confirmado_manualmente"] = True
        pagamentos_validos.append(registro)
        restante = round(restante - valor_aplicado, 2)

    if restante > 0:
        return RedirectResponse(url="/pdv?erro=pagamento", status_code=302)

    # ── Persiste tudo em uma única transação
    venda = Venda(
        cliente_id          = cliente_id or None,
        usuario_id          = usuario.get("id"),
        desconto_percentual = desconto_percentual,
        total_bruto         = round(total_bruto, 2),
        total_liquido       = round(total_liquido, 2),
        observacao          = observacao or None,
        formas_pagamento    = json.dumps(pagamentos_validos, ensure_ascii=False),
    )
    db.add(venda)
    db.flush()  # gera o venda.id sem commitar ainda

    for item in itens_validados:
        db.add(ItemVenda(
            venda_id       = venda.id,
            produto_id     = item["produto"].id,
            produto_nome   = item["produto_nome"],
            quantidade     = item["quantidade"],
            preco_unitario = item["preco"],
        ))
        # Baixa somente o estoque da variação vendida
        item["variacao"].estoque_atual -= item["quantidade"]

    db.commit()

    return RedirectResponse(
        url=f"/pdv/venda/{venda.id}?sucesso=ok",
        status_code=302
    )


@router.get("/venda/{venda_id}")
def detalhe_venda(
    venda_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """Comprovante da venda — exibido imediatamente após finalizar."""
    venda = db.query(Venda).filter(Venda.id == venda_id).first()

    if not venda:
        return RedirectResponse(url="/pdv", status_code=302)

    return templates.TemplateResponse(
        request,
        "pdv/comprovante.html",
        {
            "request": request,
            "usuario": usuario,
            "venda": venda,
            "cliente_telefone": venda.cliente.telefone if venda.cliente else "",
        }
    )


@router.get("/historico")
def historico_vendas(
    request: Request,
    pagina: int = 1,
    por_pagina: int = 16,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """Histórico de todas as vendas."""
    resultado = paginar(
        db.query(Venda).order_by(Venda.criado_em.desc()), pagina, por_pagina
    )
    return templates.TemplateResponse(
        request,
        "pdv/historico.html",
        {
            "request": request,
            "usuario": usuario,
            "vendas": resultado.itens,
            "pagina": resultado.atual,
            "por_pagina": resultado.por_pagina,
            "total_paginas": resultado.total_paginas,
            "total_vendas": resultado.total_itens,
        }
    )
