from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import random 
import httpx

from app.controllers import auth_controller, admin_controller, categoria_controller, produto_controller, movimentacao_controller, pdv_controller, cliente_controller
from app.auth import get_usuario_opcional
from app.database import get_db
from app.models.produto import Produto
from app.models.categoria import Categoria
from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.venda import Venda
from app.models.movimentacao import Movimentacao

app = FastAPI(title="Gestão de Estoque - AAPM")

# Configurar o fastapi para servir os arquivos CSS, JS, IMG
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configura para renderizar os templates HTML
templates = Jinja2Templates(directory="app/templates")

# ── ROTA API DE CARROS (Para o 404.html) ──
@app.get("/api/get-carro")
async def api_get_carro():
    # COLE AQUI A SUA ACCESS KEY QUE VOCÊ COPIOU DO PORTAL DE DESENVOLVEDOR
    ACCESS_KEY = "g3abxxBep3Jfs-Ve9FMl3gYZ4g4BFuFJT5jM2ir-4VE" 
    url = f"https://api.unsplash.com/photos/random?query=supercar&client_id={ACCESS_KEY}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                data = response.json()
                return {
                    "modelo": data.get("alt_description") or "Super Car",
                    "url": data["urls"]["regular"],
                    "fotografo": data["user"]["name"]
                }
        except Exception as e:
            print(f"Erro na API: {e}")
            
    # Fallback caso a API falhe ou a chave esteja errada
    return {
        "modelo": "Mustang GT", 
        "url": "https://images.unsplash.com/photo-1584345604476-8aa5e58b943d?w=800",
        "fotografo": "Unsplash"
    }

@app.exception_handler(StarletteHTTPException)
async def erro_404_customizado(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(request, "404.html", {"request": request}, status_code=404)
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)

# Inclui os routers dos controllers
app.include_router(auth_controller.router) 
app.include_router(admin_controller.router) 
app.include_router(categoria_controller.router)
app.include_router(produto_controller.router)
app.include_router(movimentacao_controller.router)
app.include_router(pdv_controller.router)
app.include_router(cliente_controller.router)

@app.get("/")
def tela_home(request: Request, usuario = Depends(get_usuario_opcional), db: Session = Depends(get_db)):
    if usuario is None:
        produtos_db = db.query(Produto).filter(Produto.ativo == True).order_by(Produto.id.desc()).limit(8).all()
        produtos = [{"nome": p.nome, "preco_venda": p.preco, "quantidade": p.estoque_atual, "categoria": p.categoria, "imagem_url": p.imagem_url if p.imagem_path else None} for p in produtos_db]
        return templates.TemplateResponse(request, "index.html", {"request": request, "usuario": None, "produtos": produtos})
    
    # Dashboard (logado)
    total_produtos = db.query(Produto).count()
    total_categorias = db.query(Categoria).count()
    total_usuarios = db.query(Usuario).count()
    total_clientes = db.query(Cliente).count()
    total_vendas = db.query(Venda).count()
    total_movimentacoes = db.query(Movimentacao).count()
    
    total_estoque = int(db.query(func.coalesce(func.sum(Produto.estoque_atual), 0)).scalar())
    
    # Charts... (simplifiquei aqui para ficar visualmente limpo, mantenha sua lógica original)
    return templates.TemplateResponse(request, "home.html", {
        "request": request, "usuario": usuario, "total_produtos": total_produtos,
        "total_categorias": total_categorias, "total_usuarios": total_usuarios,
        "total_clientes": total_clientes, "total_vendas": total_vendas,
        "total_movimentacoes": total_movimentacoes, "total_estoque": total_estoque
    })

@app.get("/contato", response_class=HTMLResponse)
def tela_contato(request: Request):
    return templates.TemplateResponse(request, "contato.html", {"request": request})