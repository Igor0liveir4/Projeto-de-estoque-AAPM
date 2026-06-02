from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.controllers import auth_controller
from app.controllers import admin_controller
from app.controllers import categoria_controller
from app.controllers import produto_controller

from app.auth import get_usuario_opcional
from app.database import get_db
from app.models.produto import Produto
from app.models.categoria import Categoria
from app.models.usuario import Usuario

app = FastAPI(title="Gestão de Estoque - AAPM")

# Configurar o fastapi para servir os arquivos CSS, JS, IMG
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configura para renderizar os templates HTML
templates = Jinja2Templates(directory="app/templates")

# Inclui os routeres do controller
app.include_router(auth_controller.router) 
app.include_router(admin_controller.router)
app.include_router(categoria_controller.router)
app.include_router(produto_controller.router)

@app.get("/")
def tela_home(
    request: Request,
    usuario = Depends(get_usuario_opcional),
    db: Session = Depends(get_db)
):
    # Não logado - exibe a tela de login/cadastro
    if usuario is None:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"request": request, "usuario": None}
        )
    
    # Logado - exibe o dashboard com estatísticas
    # Contar totais
    total_produtos = db.query(Produto).count()
    total_categorias = db.query(Categoria).count()
    total_usuarios = db.query(Usuario).count()
    
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
            "total_estoque": total_estoque,
            "categorias_chart": json.dumps(categorias_chart),
            "produtos_chart": json.dumps(produtos_chart),
            "valor_chart": json.dumps(valor_chart)
        }
    )