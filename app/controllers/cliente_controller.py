from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cliente import Cliente
from app.auth import get_admin

router = APIRouter(prefix="/cliente", tags=["Cliente"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def listar_clientes(
    request: Request,
    busca: str = "",
    apenas_associados: bool = False,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    query = db.query(Cliente)

    if busca:
        query = query.filter(
            Cliente.nome.ilike(f"%{busca}%") |
            Cliente.email.ilike(f"%{busca}%")
        )

    if apenas_associados:
        query = query.filter(Cliente.is_associado == True)

    clientes = query.order_by(Cliente.nome).all()

    total_associados = db.query(Cliente).filter(
        Cliente.is_associado == True,
        Cliente.ativo == True
    ).count()

    return templates.TemplateResponse(
        request,
        "cliente/index.html",
        {
            "request":           request,
            "usuario":           admin,
            "clientes":          clientes,
            "busca":             busca,
            "apenas_associados": apenas_associados,
            "total_associados":  total_associados,
        }
    )


@router.get("/novo")
def form_novo(request: Request, admin = Depends(get_admin)):
    return templates.TemplateResponse(
        request,
        "cliente/form.html",
        {"request": request, "usuario": admin, "editando": None}
    )


@router.post("/novo")
def criar(
    request: Request,
    nome: str          = Form(...),
    email: str         = Form(""),
    telefone: str      = Form(""),
    is_associado: bool = Form(False),
    db: Session        = Depends(get_db),
    admin              = Depends(get_admin)
):
    db.add(Cliente(
        nome         = nome.strip(),
        email        = email.strip() or None,
        telefone     = telefone.strip() or None,
        is_associado = is_associado,
    ))
    db.commit()

    return RedirectResponse(url="/cliente?criado=ok", status_code=302)


@router.get("/{cliente_id}/editar")
def form_editar(
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    editando = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not editando:
        return RedirectResponse(url="/cliente", status_code=302)

    return templates.TemplateResponse(
        request,
        "cliente/form.html",
        {"request": request, "usuario": admin, "editando": editando}
    )


@router.post("/{cliente_id}/editar")
def editar(
    cliente_id: int,
    nome: str          = Form(...),
    email: str         = Form(""),
    telefone: str      = Form(""),
    is_associado: bool = Form(False),
    db: Session        = Depends(get_db),
    admin              = Depends(get_admin)
):
    editando = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not editando:
        return RedirectResponse(url="/cliente", status_code=302)

    editando.nome         = nome.strip()
    editando.email        = email.strip() or None
    editando.telefone     = telefone.strip() or None
    editando.is_associado = is_associado
    db.commit()

    return RedirectResponse(url="/cliente?editado=ok", status_code=302)


@router.post("/{cliente_id}/toggle-ativo")
def toggle_ativo(
    cliente_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if cliente:
        cliente.ativo = not cliente.ativo
        db.commit()
    return RedirectResponse(url="/clientes", status_code=302)