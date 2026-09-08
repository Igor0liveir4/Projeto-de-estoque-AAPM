# Rotas acessíveis apenas por admin
# controllers/admin_controller.py

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.movimentacao import Movimentacao
from app.models.usuario import Usuario
from app.models.venda import Venda
from app.auth import get_admin, hash_password
from app.pagination import paginar


router = APIRouter(prefix="/usuarios", tags=["Usuários"])

templates = Jinja2Templates(directory="app/templates")


# Exibir os usuarios do sistema
@router.get("/")
def listar_usuarios(
    request: Request,
    pagina: int = 1,
    por_pagina: int = 10,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    resultado = paginar(db.query(Usuario).order_by(Usuario.nome), pagina, por_pagina)

    return templates.TemplateResponse(
        request,
        "usuarios/index.html",
        {
            "request": request,
            "usuario": admin,   # ← era "admin", corrigido para "usuario"
            "usuarios": resultado.itens,
            "pagina": resultado.atual,
            "por_pagina": resultado.por_pagina,
            "total_paginas": resultado.total_paginas,
            "total_usuarios": resultado.total_itens,
        }
    )


# CADASTRO

@router.get("/novo")
def form_novo_usuario(
    request: Request,
    admin = Depends(get_admin)
):
    return templates.TemplateResponse(
        request,
        "usuarios/form.html",
        {
            "request": request,
            "usuario": admin,
            "editando": None
        }
    )


@router.post("/novo")
def criar_usuario(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    existente = db.query(Usuario).filter(
        Usuario.email == email
    ).first()

    if existente:
        return templates.TemplateResponse(
            request,
            "usuarios/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": None,
                "erro": "Este e-mail já está cadastrado.",
                "valores": {"nome": nome, "email": email, "role": role}
            },
            status_code=400
        )

    if role not in ("admin", "user"):
        return templates.TemplateResponse(
            request,
            "usuarios/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": None,
                "erro": "Perfil de acesso inválido.",
                "valores": {"nome": nome, "email": email, "role": role}
            },
            status_code=400
        )

    novo = Usuario(
        nome=nome,
        email=email,
        senha_hash=hash_password(senha),
        role=role,
    )

    db.add(novo)
    db.commit()

    return RedirectResponse(url="/usuarios?criado=ok", status_code=302)


# EDIÇÃO

@router.get("/{usuario_id}/editar")
def form_editar_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    editando = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not editando:
        return RedirectResponse(url="/usuarios", status_code=302)

    return templates.TemplateResponse(
        request,
        "usuarios/form.html",
        {
            "request": request,
            "usuario": admin,
            "editando": editando
        }
    )


@router.post("/{usuario_id}/editar")
def editar_usuario(
    usuario_id: int,
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    senha: str = Form(""),
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    editando = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not editando:
        return RedirectResponse(url="/usuarios", status_code=302)

    conflito = db.query(Usuario).filter(
        Usuario.email == email,
        Usuario.id != usuario_id
    ).first()

    if conflito:
        return templates.TemplateResponse(
            request,
            "usuarios/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": editando,
                "erro": "Este e-mail já está em uso por outro usuário.",
            },
            status_code=400
        )

    if role not in ("admin", "user"):
        return templates.TemplateResponse(
            request,
            "usuarios/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": editando,
                "erro": "Perfil de acesso inválido.",
            },
            status_code=400
        )

    editando.nome = nome
    editando.email = email
    editando.role = role

    if senha.strip():
        editando.senha_hash = hash_password(senha)

    db.commit()

    return RedirectResponse(url="/usuarios?editado=ok", status_code=302)


# EXCLUSÃO

@router.post("/{usuario_id}/excluir")
def excluir_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """Exclui um usuário somente quando não há históricos vinculados."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        return RedirectResponse(url="/usuarios", status_code=302)

    if usuario.email == admin.get("sub"):
        return RedirectResponse(
            url="/usuarios?erro=autoproprio_exclusao",
            status_code=302
        )

    possui_movimentacao = db.query(Movimentacao.id).filter(
        Movimentacao.usuario_id == usuario_id
    ).first()
    possui_venda = db.query(Venda.id).filter(
        Venda.usuario_id == usuario_id
    ).first()

    if possui_movimentacao or possui_venda:
        query = urlencode({
            "erro": "registros_impedem_exclusao",
            "usuario": usuario.nome,
        })
        return RedirectResponse(url=f"/usuarios?{query}", status_code=302)

    db.delete(usuario)
    db.commit()

    return RedirectResponse(url="/usuarios?excluido=ok", status_code=302)


# ATIVAR / DESATIVAR

@router.post("/{usuario_id}/toggle-ativo")
def toggle_ativo(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        return RedirectResponse(url="/usuarios", status_code=302)

    if usuario.email == admin.get("sub"):
        return RedirectResponse(
            url="/usuarios?erro=autoproprio",
            status_code=302
        )

    usuario.ativo = not usuario.ativo
    db.commit()

    return RedirectResponse(url="/usuarios", status_code=302)
