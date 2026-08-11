import os
import shutil
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.produto import Produto
from app.models.variacoes import Variacao
from app.models.categoria import Categoria
from app.auth import get_usuario_logado, get_admin

router = APIRouter(prefix="/produtos", tags=["Produtos"])

templates = Jinja2Templates(directory="app/templates")

# Pasta onde as imagens serão salvas dentro de /static
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # cria a pasta se não existir


def _eh_produto_roupa(nome: str, categoria_nome: Optional[str]) -> bool:
    nome = (nome or "").strip().lower()
    categoria_nome = (categoria_nome or "").strip().lower()
    palavras_roupa = [
        "roupa", "camisa", "camiseta", "blusa", "calca", "calça",
        "bermuda", "short", "vestido", "jaqueta", "casaco", "calça",
        "tênis", "tenis", "uniforme", "moletom", "calcinha", "cueca"
    ]
    return any(palavra in nome for palavra in palavras_roupa) or any(
        palavra in categoria_nome for palavra in palavras_roupa
    )


def _parse_variacoes(
    tamanhos: Optional[List[str]],
    cores: Optional[List[str]],
    estoques: Optional[List[str]],
) -> tuple[list[Variacao], Optional[str]]:
    variacoes: list[Variacao] = []
    if not tamanhos or not cores or not estoques:
        return variacoes, None

    for tamanho, cor, estoque in zip(tamanhos, cores, estoques):
        tamanho = (tamanho or "").strip()
        cor = (cor or "").strip()
        estoque_raw = (estoque or "").strip()

        if not tamanho and not cor and not estoque_raw:
            continue

        if not tamanho or not cor:
            return [], "Cada variação precisa ter tamanho e cor preenchidos."

        if estoque_raw == "":
            return [], "Cada variação precisa ter quantidade de estoque."

        try:
            quantidade = int(estoque_raw)
        except ValueError:
            return [], "A quantidade de estoque deve ser um número inteiro."

        if quantidade < 0:
            return [], "A quantidade de estoque não pode ser negativa."

        variacoes.append(
            Variacao(tamanho=tamanho, cor=cor, estoque_atual=quantidade)
        )

    return variacoes, None


def _validar_variacoes_roupa(variacoes: list[Variacao]) -> Optional[str]:
    """
    Valida se as variações fazem sentido para um produto de roupa.
    Retorna mensagem de erro se há inconsistências.
    """
    if not variacoes:
        return None

    tem_variacao_padrao = any(
        v.tamanho.lower() == "único" and v.cor.lower() == "padrão"
        for v in variacoes
    )
    
    if len(variacoes) == 1 and tem_variacao_padrao:
        return "Produtos de roupa não podem usar a variação padrão. Defina tamanho e cor específicos para este item."

    return None


# ============================================================
# LISTAGEM
# ============================================================

@router.get("/")
def listar_produtos(
    request: Request,
    busca: str = "",
    categoria_id: int = 0,       # 0 = todas as categorias
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    query = db.query(Produto).filter(Produto.ativo == True)

    if busca:
        query = query.filter(Produto.nome.ilike(f"%{busca}%"))

    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)

    produtos    = query.order_by(Produto.nome).all()
    categorias  = db.query(Categoria).filter(Categoria.ativa == True).all()

    return templates.TemplateResponse(
        request,
        "produtos/index.html",
        {
            "request":      request,
            "usuario":      usuario,
            "produtos":     produtos,
            "categorias":   categorias,
            "busca":        busca,
            "categoria_id": categoria_id,
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

    categoria_obj = None
    if categoria_id:
        categoria_obj = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    eh_roupa = _eh_produto_roupa(nome, categoria_obj.nome if categoria_obj else None)

    variacoes_valores = []
    if variacoes_tamanho or variacoes_cor or variacoes_estoque:
        for tamanho, cor, estoque in zip(
            variacoes_tamanho or [],
            variacoes_cor or [],
            variacoes_estoque or []
        ):
            variacoes_valores.append({
                "tamanho": tamanho or "",
                "cor": cor or "",
                "estoque": estoque or ""
            })

    variacoes, variacoes_erro = _parse_variacoes(
        variacoes_tamanho, variacoes_cor, variacoes_estoque
    )

    if eh_roupa and not variacoes:
        return templates.TemplateResponse(
            request,
            "produtos/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": None,
                "categorias": categorias,
                "erro": variacoes_erro or "Produtos de roupa precisam ter pelo menos uma variação com tamanho, cor e quantidade.",
                "valores": {
                    "nome": nome,
                    "preco": preco,
                    "categoria_id": categoria_id,
                    "ativo": ativo is not None,
                },
                "variacoes_valores": variacoes_valores,
            },
            status_code=400,
        )

    if eh_roupa and variacoes:
        variacoes_erro_roupa = _validar_variacoes_roupa(variacoes)
        if variacoes_erro_roupa:
            return templates.TemplateResponse(
                request,
                "produtos/form.html",
                {
                    "request": request,
                    "usuario": admin,
                    "editando": None,
                    "categorias": categorias,
                    "erro": variacoes_erro_roupa,
                    "valores": {
                        "nome": nome,
                        "preco": preco,
                        "categoria_id": categoria_id,
                        "ativo": ativo is not None,
                    },
                    "variacoes_valores": variacoes_valores,
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
    produto = db.query(Produto).filter(
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

    categoria_obj = None
    if categoria_id:
        categoria_obj = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    eh_roupa = _eh_produto_roupa(nome, categoria_obj.nome if categoria_obj else None)

    variacoes_valores = []
    if variacoes_tamanho or variacoes_cor or variacoes_estoque:
        for tamanho, cor, estoque in zip(
            variacoes_tamanho or [],
            variacoes_cor or [],
            variacoes_estoque or []
        ):
            variacoes_valores.append({
                "tamanho": tamanho or "",
                "cor": cor or "",
                "estoque": estoque or ""
            })

    variacoes, variacoes_erro = _parse_variacoes(
        variacoes_tamanho, variacoes_cor, variacoes_estoque
    )

    if eh_roupa and not variacoes:
        return templates.TemplateResponse(
            request,
            "produtos/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": editando,
                "categorias": categorias,
                "erro": variacoes_erro or "Produtos de roupa precisam ter pelo menos uma variação com tamanho, cor e quantidade.",
                "valores": {
                    "nome": nome,
                    "preco": preco,
                    "categoria_id": categoria_id,
                    "ativo": ativo is not None,
                },
                "variacoes_valores": variacoes_valores,
            },
            status_code=400,
        )

    if eh_roupa and variacoes:
        variacoes_erro_roupa = _validar_variacoes_roupa(variacoes)
        if variacoes_erro_roupa:
            return templates.TemplateResponse(
                request,
                "produtos/form.html",
                {
                    "request": request,
                    "usuario": admin,
                    "editando": editando,
                    "categorias": categorias,
                    "erro": variacoes_erro_roupa,
                    "valores": {
                        "nome": nome,
                        "preco": preco,
                        "categoria_id": categoria_id,
                        "ativo": ativo is not None,
                    },
                    "variacoes_valores": variacoes_valores,
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
