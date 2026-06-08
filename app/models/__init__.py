# Gerar as migrations
# python -m alembic revision --autogenerate -m "Criando tabelas de venda"
# python -m alembic upgrade head

from app.models import categoria
from app.models  import produto
from app.models import usuario
from app.models import movimentacao
from app.models import cliente
from app.models import venda

# ...existing code...
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

app = FastAPI()
# ...existing code (inclua routers e mounts antes desta rota) ...

@app.get("/{full_path:path}")
async def catch_all(full_path: str, request: Request):
    return RedirectResponse(url="/")
# ...existing code...