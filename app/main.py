from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from app.controllers import auth_controller

from app.auth import get_usuario_opcional

app = FastAPI(title="Sistema de Estoque - AAPM")

# Configurar o fastapi para servir os arquivos CSS, JS, IMG
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configura para renderizar os templates HTML
templates = Jinja2Templates(directory="app/templates")

# Inclui os routeres do controller
app.include_router(auth_controller.router) 

@app.get("/")
def tela_home(
    request: Request,
    usuario = Depends(get_usuario_opcional)
):
    # Não logado - exibe a tela index
    if usuario is None:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"request": request, "usuario": None}
        )
    
    # Logado - exibe a tela home
    return templates.TemplateResponse(
            request,
            "home.html",
            {"request": request, "usuario": usuario}
        )