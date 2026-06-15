from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.controllers import auth_controller
from app.controllers import admin_controller
from app.controllers import categoria_controller
from app.controllers import produto_controller
from app.controllers import movimentacao_controller
from app.controllers import pdv_controller
from app.controllers import cliente_controller

from app.auth import get_usuario_opcional
from app.database import get_db
from app.models.produto import Produto
from app.models.categoria import Categoria
from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.venda import Venda, ItemVenda
from app.models.movimentacao import Movimentacao, Tipo_de_movimentacao

app = FastAPI(title="Gestão de Estoque - AAPM")

# Configurar o fastapi para servir os arquivos CSS, JS, IMG
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configura para renderizar os templates HTML
templates = Jinja2Templates(directory="app/templates")

@app.exception_handler(StarletteHTTPException)
async def erro_404_customizado(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request,
            "404.html", 
            {"request": request}, 
            status_code=404
        )
    # Se for outro tipo de erro HTTP (ex: 403, 500), mantém o padrão do sistema
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)

# Inclui os routeres do controller
app.include_router(auth_controller.router) 
app.include_router(admin_controller.router) 
app.include_router(categoria_controller.router)
app.include_router(produto_controller.router)
app.include_router(movimentacao_controller.router)
app.include_router(pdv_controller.router)
app.include_router(cliente_controller.router)

@app.get("/")
def tela_home(
    request: Request,
    usuario = Depends(get_usuario_opcional),
    db: Session = Depends(get_db)
):
    # ── CASO 1: USUÁRIO NÃO LOGADO (CLIENTE/VISITANTE) ──
    if usuario is None:
        # Busca apenas 8 produtos do banco de dados para ilustração na vitrine
        produtos_db = db.query(Produto).order_by(Produto.id.desc()).limit(8).all()
        
        produtos = []
        for p in produtos_db:
            # Tenta capturar o campo de imagem do seu modelo (ajuste se for 'foto', 'url', etc.)
            imagem_produto = getattr(p, 'imagem', getattr(p, 'foto', None))
            
            produtos.append({
                "nome": p.nome,
                "preco_venda": getattr(p, 'preco_venda', getattr(p, 'preco', 0.0)),
                "quantidade": getattr(p, 'estoque_atual', 0),
                "categoria": p.categoria if hasattr(p, 'categoria') else None,
                "imagem": imagem_produto
            })

        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "request": request, 
                "usuario": None,
                "produtos": produtos
            }
        )
    
    # ── CASO 2: USUÁRIO LOGADO (MENSURAÇÃO DO DASHBOARD) ──
    # Contar totais
    total_produtos = db.query(Produto).count()
    total_categorias = db.query(Categoria).count()
    total_usuarios = db.query(Usuario).count()
    total_clientes = db.query(Cliente).count()
    total_vendas = db.query(Venda).count()
    total_movimentacoes = db.query(Movimentacao).count()
    
    # Total estoque
    total_estoque_result = db.query(Produto).with_entities(
        func.coalesce(func.sum(Produto.estoque_atual), 0)
    ).scalar()
    total_estoque = int(total_estoque_result) if total_estoque_result else 0
    
    # Dados para gráfico de categorias
    categorias = db.query(
        Categoria.nome,
        func.count(Produto.id).label('count')
    ).outerjoin(Produto).group_by(Categoria.id).all()
    
    categorias_chart = {
        "labels": [cat[0] for cat in categorias],
        "data": [cat[1] for cat in categorias]
    }
    
    # Dados para top 5 produtos
    top_produtos = db.query(
        Produto.nome,
        Produto.estoque_atual
    ).order_by(Produto.estoque_atual.desc()).limit(5).all()
    
    produtos_chart = {
        "labels": [prod[0] for prod in top_produtos],
        "data": [prod[1] for prod in top_produtos]
    }
    
    # Dados para valor em estoque por categoria
    valor_categorias = db.query(
        Categoria.nome,
        func.sum(Produto.preco * Produto.estoque_atual).label('valor_total')
    ).outerjoin(Produto).group_by(Categoria.id).all()
    
    valor_chart = {
        "labels": [cat[0] for cat in valor_categorias],
        "data": [round(float(cat[1]) if cat[1] else 0, 2) for cat in valor_categorias]
    }
    
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "usuario": usuario,
            "total_produtos": total_produtos,
            "total_categorias": total_categorias,
            "total_usuarios": total_usuarios,
            "total_clientes": total_clientes,
            "total_vendas": total_vendas,
            "total_movimentacoes": total_movimentacoes,
            "total_estoque": total_estoque,
            "categorias_chart": json.dumps(categorias_chart),
            "produtos_chart": json.dumps(produtos_chart),
            "valor_chart": json.dumps(valor_chart)
        }
    )

@app.get("/contato", response_class=HTMLResponse)
def tela_contato(request: Request):
    return templates.TemplateResponse(
        request,
        "contato.html",
        {"request": request}
    )