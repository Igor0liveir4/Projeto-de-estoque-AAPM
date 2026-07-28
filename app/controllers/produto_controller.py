import os
import shutil
import uuid
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.produto import Produto
from app.models.categoria import Categoria
from app.models.variacoes import Variacao
from app.auth import get_usuario_logado, get_admin

router = APIRouter(prefix="/produtos", tags=["Produtos"])

templates = Jinja2Templates(directory="app/templates")

# Pasta onde as imagens serão salvas dentro de /static
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # cria a pasta se não existir


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
    nome: str          = Form(...),
    preco: float       = Form(...),
    categoria_id: int  = Form(0),   # 0 = sem categoria
    imagem: UploadFile = File(None), # None = campo opcional
    db: Session        = Depends(get_db),
    admin              = Depends(get_admin)
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
                               "categoria_id": categoria_id}
            },
            status_code=400
        )

    # Processa o upload da imagem
    imagem_path = await _salvar_imagem(imagem)

    produto = Produto(
        nome          = nome,
        preco         = preco,
        categoria_id  = categoria_id or None,  # 0 vira NULL no banco
        imagem_path   = imagem_path,
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


from typing import Optional # Certifique-se de ter esse import no topo

@router.post("/{produto_id}/editar")
async def editar_produto(
    produto_id: int,
    request: Request,
    nome: str              = Form(...),
    preco: float           = Form(...),
    # 1. Permitimos que o campo venha vazio (None)
    estoque_atual: Optional[int] = Form(None),
    categoria_id: int      = Form(0),
    imagem: UploadFile     = File(None),
    db: Session            = Depends(get_db),
    admin                  = Depends(get_admin)
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

    # 2. A MÁGICA AQUI: Se o estoque_atual veio preenchido, usamos o novo valor.
    # Se veio em branco (None), mantemos o valor que já estava salvo antes (editando).
    if estoque_atual is not None:
        editando = estoque_atual

    editando.nome          = nome
    editando.preco         = preco
    editando.categoria_id  = categoria_id or None

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

# ============================================================
# GERENCIAMENTO DE VARIAÇÕES (SKUs)
# ============================================================

@router.post("/{produto_id}/variacoes/nova")
def adicionar_variacao(
    produto_id: int,
    request: Request,
    tamanho: str = Form(...),
    cor: str = Form(...),
    estoque_atual: int = Form(0),
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """Cria um novo tamanho/cor para um produto existente"""
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    
    if not produto:
        return RedirectResponse(url="/produtos", status_code=404)

    nova_variacao = Variacao(
        produto_id=produto.id,
        tamanho=tamanho,
        cor=cor,
        estoque_atual=estoque_atual
    )

    db.add(nova_variacao)
    db.commit()

    # Redireciona de volta para a página do produto após adicionar
    return RedirectResponse(url=f"/produtos/{produto_id}?variacao_adicionada=ok", status_code=302)


@router.post("/variacoes/{variacao_id}/excluir")
def excluir_variacao(
    variacao_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """Remove uma variação específica"""
    variacao = db.query(Variacao).filter(Variacao.id == variacao_id).first()
    
    if not variacao:
        return RedirectResponse(url="/produtos", status_code=404)

    # Guarda o ID do produto para poder redirecionar de volta à página certa
    produto_id = variacao.produto_id
    
    db.delete(variacao)
    db.commit()

    return RedirectResponse(url=f"/produtos/{produto_id}?variacao_removida=ok", status_code=302)