import os
import shutil
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.produto import Produto
from app.models.variacoes import Variacao
from app.models.categoria import Categoria
from app.auth import get_usuario_logado, get_admin
from app.pagination import paginar

router = APIRouter(prefix="/produtos", tags=["Produtos"])

templates = Jinja2Templates(directory="app/templates")

# Pasta onde as imagens serão salvas dentro de /static
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # cria a pasta se não existir


PALAVRAS_ROUPA = {
    "roupa", "camisa", "camiseta", "blusa", "calca", "calça",
    "bermuda", "short", "vestido", "jaqueta", "casaco",
    "tênis", "tenis", "uniforme", "moletom", "calcinha", "cueca"
}


def _parse_item_variacao(
    tamanho: Optional[str],
    cor: Optional[str],
    estoque_raw: Optional[str]
) -> tuple[Optional[Variacao], Optional[str]]:
    t, c, e = (tamanho or "").strip(), (cor or "").strip(), (estoque_raw or "").strip()

    if not (t or c or e):
        return None, None  # Linha em branco ignorada

    if not (t and c):
        return None, "Cada variação precisa ter tamanho e cor preenchidos."

    if not e:
        return None, "Cada variação precisa ter quantidade de estoque."

    try:
        qtd = int(e)
        if qtd < 0:
            return None, "A quantidade de estoque não pode ser negativa."
    except ValueError:
        return None, "A quantidade de estoque deve ser um número inteiro."

    return Variacao(tamanho=t, cor=c, estoque_atual=qtd), None


def _parse_variacoes(
    tamanhos: Optional[List[str]],
    cores: Optional[List[str]],
    estoques: Optional[List[str]],
) -> tuple[list[Variacao], Optional[str]]:
    if not (tamanhos and cores and estoques):
        return [], None

    variacoes: list[Variacao] = []
    for t, c, e in zip(tamanhos, cores, estoques):
        variacao, erro = _parse_item_variacao(t, c, e)
        if erro:
            return [], erro
        if variacao:
            variacoes.append(variacao)

    return variacoes, None
# ============================================================
# LISTAGEM
# ============================================================

@router.get("/")
def listar_produtos(
    request: Request,
    busca: str = "",
    categoria_id: int = 0,
    pagina: int = 1,
    por_pagina: int = 10,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    query = db.query(Produto).filter(Produto.ativo == True)

    if busca:
        query = query.filter(Produto.nome.ilike(f"%{busca}%"))

    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)

    resultado = paginar(query.order_by(Produto.nome), pagina, por_pagina)

    # Os cards resumem todo o estoque ativo, e não somente os produtos
    # carregados na página atual da listagem.
    total_estoque = (
        db.query(func.coalesce(func.sum(Variacao.estoque_atual), 0))
        .join(Produto, Variacao.produto_id == Produto.id)
        .filter(Produto.ativo == True)
        .scalar()
    )
    total_esgotados = (
        db.query(Produto.id)
        .outerjoin(Variacao)
        .filter(Produto.ativo == True)
        .group_by(Produto.id)
        .having(func.coalesce(func.sum(Variacao.estoque_atual), 0) == 0)
        .count()
    )

    categorias = db.query(Categoria).filter(Categoria.ativa == True).all()

    return templates.TemplateResponse(
        request,
        "produtos/index.html",
        {
            "request":      request,
            "usuario":      usuario,
            "produtos":     resultado.itens,
            "categorias":   categorias,
            "busca":        busca,
            "categoria_id": categoria_id,
            "pagina":       resultado.atual,
            "por_pagina":   resultado.por_pagina,
            "total_paginas": resultado.total_paginas,
            "total_produtos": resultado.total_itens,
            "total_estoque": int(total_estoque),
            "total_esgotados": total_esgotados,
        }
    )


# ============================================================
# CADASTRO
# ============================================================

@router.get("/novo")
def form_novo_produto(
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    categorias = db.query(Categoria).filter(Categoria.ativa == True).all()

    return templates.TemplateResponse(
        request,
        "produtos/form.html",
        {
            "request":    request,
            "usuario":    admin,
            "editando":   None,
            "categorias": categorias
        }
    )


@router.post("/novo")
async def criar_produto(
    request: Request,
    nome: str                     = Form(...),
    preco: float                  = Form(...),
    estoque_atual: int            = Form(...),
    categoria_id: int             = Form(0),   # 0 = sem categoria
    imagem: UploadFile            = File(None), # None = campo opcional
    ativo: Optional[str]          = Form(None),
    variacoes_tamanho: Optional[List[str]] = Form(None),
    variacoes_cor: Optional[List[str]]    = Form(None),
    variacoes_estoque: Optional[List[str]] = Form(None),
    db: Session                   = Depends(get_db),
    admin: object                 = Depends(get_admin)
):
    categorias = db.query(Categoria).filter(Categoria.ativa == True).all()

    # Verifica duplicidade de nome
    # ilike() para comparação case-insensitive, evitando produtos "Camiseta" e "camiseta".
    if db.query(Produto).filter(Produto.nome.ilike(nome)).first():
        return templates.TemplateResponse(
            request,
            "produtos/form.html",
            {
                "request":    request,
                "usuario":    admin,
                "editando":   None,
                "categorias": categorias,
                "erro":       "Já existe um produto com este nome.",
                "valores":    {"nome": nome, "preco": preco,
                               "estoque_atual": estoque_atual,
                               "categoria_id": categoria_id,
                               "ativo": ativo is not None}
            },
            status_code=400
        )

    variacoes, variacoes_erro = _parse_variacoes(
        variacoes_tamanho, variacoes_cor, variacoes_estoque
    )

    if variacoes_erro:
        return templates.TemplateResponse(
            request,
            "produtos/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": None,
                "categorias": categorias,
                "erro": variacoes_erro,
                "valores": {
                    "nome": nome,
                    "preco": preco,
                    "categoria_id": categoria_id,
                    "ativo": ativo is not None,
                },
                "variacoes_valores": [{
                    "tamanho": (variacoes_tamanho or [""])[i] if i < len(variacoes_tamanho or []) else "",
                    "cor": (variacoes_cor or [""])[i] if i < len(variacoes_cor or []) else "",
                    "estoque": (variacoes_estoque or [""])[i] if i < len(variacoes_estoque or []) else "",
                } for i in range(max(len(variacoes_tamanho or []), len(variacoes_cor or []), len(variacoes_estoque or [])))],
            },
            status_code=400,
        )

    # Processa o upload da imagem
    imagem_path = await _salvar_imagem(imagem)

    produto = Produto(
        nome          = nome,
        preco         = preco,
        categoria_id  = categoria_id or None,  # 0 vira NULL no banco
        imagem_path   = imagem_path,
        ativo         = ativo is not None,
    )

    if variacoes:
        produto.variacoes.extend(variacoes)
    else:
        produto.variacoes.append(
            Variacao(tamanho="Único", cor="Padrão", estoque_atual=estoque_atual)
        )

    db.add(produto)
    db.commit()

    return RedirectResponse(url="/produtos?criado=ok", status_code=302)


# DETALHE
@router.get("/{produto_id}")
def detalhe_produto(
    produto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    produto = db.query(Produto).options(joinedload(Produto.variacoes)).filter(
        Produto.id == produto_id,
        Produto.ativo == True
    ).first()

    if not produto:
        return RedirectResponse(url="/produtos", status_code=302)

    return templates.TemplateResponse(
        request,
        "produtos/detalhe.html",
        {"request": request, "usuario": usuario, "produto": produto}
    )



# EDIÇÃO
@router.get("/{produto_id}/editar")
def form_editar_produto(
    produto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    editando   = db.query(Produto).filter(Produto.id == produto_id).first()
    categorias = db.query(Categoria).filter(Categoria.ativa == True).all()

    if not editando:
        return RedirectResponse(url="/produtos", status_code=302)

    return templates.TemplateResponse(
        request,
        "produtos/form.html",
        {
            "request":    request,
            "usuario":    admin,
            "editando":   editando,
            "categorias": categorias
        }
    )


@router.post("/{produto_id}/editar")
async def editar_produto(
    produto_id: int,
    request: Request,
    nome: str                        = Form(...),
    preco: float                     = Form(...),
    # 1. Permitimos que o campo venha vazio (None)
    estoque_atual: Optional[int]     = Form(None),
    categoria_id: int                = Form(0),
    imagem: UploadFile               = File(None),
    ativo: Optional[str]             = Form(None),
    variacoes_tamanho: Optional[List[str]] = Form(None),
    variacoes_cor: Optional[List[str]]    = Form(None),
    variacoes_estoque: Optional[List[str]] = Form(None),
    db: Session                      = Depends(get_db),
    admin: object                    = Depends(get_admin)
):
    editando   = db.query(Produto).filter(Produto.id == produto_id).first()
    categorias = db.query(Categoria).filter(Categoria.ativa == True).all()

    if not editando:
        return RedirectResponse(url="/produtos", status_code=302)

    # Verifica conflito de nome com outro produto
    conflito = db.query(Produto).filter(
        Produto.nome.ilike(nome),
        Produto.id != produto_id
    ).first()

    if conflito:
        return templates.TemplateResponse(
            request,
            "produtos/form.html",
            {
                "request":    request,
                "usuario":    admin,
                "editando":   editando,
                "categorias": categorias,
                "erro":       "Já existe outro produto com este nome.",
            },
            status_code=400
        )

    # Processa nova imagem — só substitui se um arquivo foi enviado
    nova_imagem_path = await _salvar_imagem(imagem)
    if nova_imagem_path:
        _remover_imagem(editando.imagem_path)
        editando.imagem_path = nova_imagem_path

    variacoes, variacoes_erro = _parse_variacoes(
        variacoes_tamanho, variacoes_cor, variacoes_estoque
    )

    if variacoes_erro:
        return templates.TemplateResponse(
            request,
            "produtos/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": editando,
                "categorias": categorias,
                "erro": variacoes_erro,
                "valores": {
                    "nome": nome,
                    "preco": preco,
                    "categoria_id": categoria_id,
                    "ativo": ativo is not None,
                },
                "variacoes_valores": [{
                    "tamanho": (variacoes_tamanho or [""])[i] if i < len(variacoes_tamanho or []) else "",
                    "cor": (variacoes_cor or [""])[i] if i < len(variacoes_cor or []) else "",
                    "estoque": (variacoes_estoque or [""])[i] if i < len(variacoes_estoque or []) else "",
                } for i in range(max(len(variacoes_tamanho or []), len(variacoes_cor or []), len(variacoes_estoque or [])))],
            },
            status_code=400,
        )

    if variacoes:
        editando.variacoes[:] = []
        editando.variacoes.extend(variacoes)
    elif estoque_atual is not None:
        # Ajusta o total quando não há variações explícitas
        diferenca = estoque_atual - editando.estoque_total
        if diferenca > 0:
            editando.adicionar_estoque(diferenca)
        elif diferenca < 0:
            editando.retirar_estoque(-diferenca)

    editando.nome          = nome
    editando.preco         = preco
    editando.categoria_id  = categoria_id or None
    editando.ativo         = ativo is not None

    db.commit()

    return RedirectResponse(url=f"/produtos/{produto_id}?editado=ok", status_code=302)

# ============================================================
# DESATIVAR
# ============================================================

@router.post("/{produto_id}/desativar")
def desativar_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()

    if produto:
        produto.ativo = False
        db.commit()

    return RedirectResponse(url="/produtos?desativado=ok", status_code=302)


# ============================================================
# FUNÇÕES AUXILIARES DE IMAGEM
# ============================================================

async def _salvar_imagem(imagem: UploadFile | None):
    """
    Salva o arquivo enviado em /static/uploads/ e retorna
    o path relativo para guardar no banco.

    Retorna None se nenhum arquivo foi enviado ou se o
    arquivo enviado estiver vazio (campo deixado em branco).
    """
    # UploadFile com filename vazio = campo não preenchido
    if not imagem or not imagem.filename:
        return None

    # Valida a extensão — aceita apenas imagens
    extensoes_permitidas = {".jpg", ".jpeg", ".png", ".webp"}
    _, ext = os.path.splitext(imagem.filename.lower())

    if ext not in extensoes_permitidas:
        return None  # ignora silenciosamente — pode virar erro em produção

    # Garante nome de arquivo único usando o nome original
    # Em produção: use uuid4() para evitar colisões e exposição de nomes
    # nome_arquivo = f"{imagem.filename}"
    nome_arquivo = f"{uuid.uuid4()}{ext}"
    caminho_completo = os.path.join(UPLOAD_DIR, nome_arquivo)

    # Salva o arquivo no disco
    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(imagem.file, buffer)

    # Retorna o path relativo ao /static (para montar a URL)
    return f"uploads/{nome_arquivo}"


def _remover_imagem(imagem_path: str | None) -> None:
    """Remove o arquivo de imagem do disco se ele existir."""
    if not imagem_path:
        return

    caminho = os.path.join("app/static", imagem_path)

    if os.path.exists(caminho):
        os.remove(caminho)
