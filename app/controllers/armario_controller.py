# ============================================================
# controllers/armario_controller.py
# ============================================================
# Admin: gerencia tudo (criar, alugar, liberar, desativar).
# Qualquer logado: visualiza o mapa de disponibilidade.
# ============================================================

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.armario import Armario, StatusArmario
from app.auth import get_usuario_logado, get_admin

router = APIRouter(prefix="/armarios", tags=["Armários"])

templates = Jinja2Templates(directory="app/templates")


# ============================================================
# MAPA DE ARMÁRIOS — visível para todos os logados
# ============================================================

@router.get("/")
def listar_armarios(
    request: Request,
    status: str = "",           # filtra por status
    localizacao: str = "",      # filtra por localização
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """
    Exibe o mapa de armários agrupado por status.
    Qualquer usuário logado pode ver a disponibilidade.
    """
    query = db.query(Armario).filter(Armario.ativo == True)

    if status in ("disponivel", "alugado", "inativo"):
        query = query.filter(Armario.status == status)

    if localizacao:
        query = query.filter(Armario.localizacao.ilike(f"%{localizacao}%"))

    armarios = query.order_by(Armario.numero).all()

    # Contadores para o resumo no topo da página
    todos     = db.query(Armario).filter(Armario.ativo == True).all()
    disponiveis = sum(1 for a in todos if a.status == StatusArmario.DISPONIVEL)
    alugados    = sum(1 for a in todos if a.status == StatusArmario.ALUGADO)

    # Lista de localizações únicas para o filtro
    localizacoes = sorted(set(
        a.localizacao for a in todos if a.localizacao
    ))

    return templates.TemplateResponse(
        request,
        "armarios/index.html",
        {
            "request":      request,
            "usuario":      usuario,
            "armarios":     armarios,
            "disponiveis":  disponiveis,
            "alugados":     alugados,
            "total":        len(todos),
            "status":       status,
            "localizacao":  localizacao,
            "localizacoes": localizacoes,
            "StatusArmario": StatusArmario,
        }
    )


# ============================================================
# CADASTRO DE ARMÁRIO — somente admin
# ============================================================

@router.get("/novo")
def form_novo_armario(
    request: Request,
    admin = Depends(get_admin)
):
    return templates.TemplateResponse(
        request,
        "armarios/form.html",
        {
            "request":  request,
            "usuario":  admin,
            "editando": None,
        }
    )


@router.post("/novo")
def criar_armario(
    request: Request,
    numero: str      = Form(...),
    localizacao: str = Form(""),
    observacao: str  = Form(""),
    db: Session      = Depends(get_db),
    admin            = Depends(get_admin)
):
    # Número do armário deve ser único
    existente = db.query(Armario).filter(
        Armario.numero == numero.strip().upper()
    ).first()

    if existente:
        return templates.TemplateResponse(
            request,
            "armarios/form.html",
            {
                "request":  request,
                "usuario":  admin,
                "editando": None,
                "erro":     f"Armário {numero.upper()} já está cadastrado.",
                "valores":  {
                    "numero": numero,
                    "localizacao": localizacao,
                    "observacao": observacao,
                },
            },
            status_code=400
        )

    db.add(Armario(
        numero      = numero.strip().upper(),
        localizacao = localizacao.strip() or None,
        observacao  = observacao.strip() or None,
    ))
    db.commit()

    return RedirectResponse(url="/armarios?criado=ok", status_code=302)


# ============================================================
# DETALHE DO ARMÁRIO
# ============================================================

@router.get("/{armario_id}")
def detalhe_armario(
    armario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    armario = db.query(Armario).filter(Armario.id == armario_id).first()

    if not armario:
        return RedirectResponse(url="/armarios", status_code=302)

    return templates.TemplateResponse(
        request,
        "armarios/detalhe.html",
        {
            "request": request,
            "usuario": usuario,
            "armario": armario,
        }
    )


# ============================================================
# EDITAR DADOS DO ARMÁRIO (número, localização) — admin
# ============================================================

@router.get("/{armario_id}/editar")
def form_editar_armario(
    armario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    editando = db.query(Armario).filter(Armario.id == armario_id).first()

    if not editando:
        return RedirectResponse(url="/armarios", status_code=302)

    return templates.TemplateResponse(
        request,
        "armarios/form.html",
        {
            "request":  request,
            "usuario":  admin,
            "editando": editando,
        }
    )


@router.post("/{armario_id}/editar")
def editar_armario(
    armario_id: int,
    numero: str      = Form(...),
    localizacao: str = Form(""),
    observacao: str  = Form(""),
    db: Session      = Depends(get_db),
    admin            = Depends(get_admin)
):
    editando = db.query(Armario).filter(Armario.id == armario_id).first()

    if not editando:
        return RedirectResponse(url="/armarios", status_code=302)

    # Verifica conflito de número com outro armário
    conflito = db.query(Armario).filter(
        Armario.numero == numero.strip().upper(),
        Armario.id != armario_id
    ).first()

    if conflito:
        return templates.TemplateResponse(
            request,
            "armarios/form.html",
            {
                "request":  None,
                "usuario":  admin,
                "editando": editando,
                "erro":     f"Armário {numero.upper()} já existe.",
            },
            status_code=400
        )

    editando.numero      = numero.strip().upper()
    editando.localizacao = localizacao.strip() or None
    editando.observacao  = observacao.strip() or None
    db.commit()

    return RedirectResponse(url=f"/armarios/{armario_id}?editado=ok", status_code=302)


# ============================================================
# ALUGAR ARMÁRIO — admin preenche o nome do locatário
# ============================================================

@router.get("/{armario_id}/alugar")
def form_alugar(
    armario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """Exibe o formulário para vincular um locatário ao armário."""
    armario = db.query(Armario).filter(Armario.id == armario_id).first()

    if not armario or armario.status != StatusArmario.DISPONIVEL:
        return RedirectResponse(url="/armarios", status_code=302)

    return templates.TemplateResponse(
        request,
        "armarios/form_alugar.html",
        {
            "request": request,
            "usuario": admin,
            "armario": armario,
        }
    )


@router.post("/{armario_id}/alugar")
def alugar(
    armario_id: int,
    locatario_nome: str = Form(...),
    semestre: str       = Form(...),
    observacao: str     = Form(""),
    db: Session         = Depends(get_db),
    admin               = Depends(get_admin)
):
    """
    Vincula o locatário ao armário e muda o status para ALUGADO.
    O semestre é fixo durante toda a vigência do contrato.
    """
    armario = db.query(Armario).filter(
        Armario.id == armario_id
    ).with_for_update().first()

    # Dupla verificação: garante que não foi alugado entre o GET e o POST
    if not armario or armario.status != StatusArmario.DISPONIVEL:
        return RedirectResponse(
            url="/armarios?erro=ja_alugado",
            status_code=302
        )

    armario.status         = StatusArmario.ALUGADO
    armario.locatario_nome = locatario_nome.strip()
    armario.semestre       = semestre.strip()
    armario.observacao     = observacao.strip() or armario.observacao
    armario.alugado_em     = datetime.now(timezone.utc)

    db.commit()

    return RedirectResponse(
        url=f"/armarios/{armario_id}?alugado=ok",
        status_code=302
    )


# ============================================================
# LIBERAR ARMÁRIO — remove o locatário e volta a disponível
# ============================================================

@router.post("/{armario_id}/liberar")
def liberar(
    armario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """
    Remove o locatário e deixa o armário disponível novamente.
    Os dados do locatário anterior são apagados — não há histórico
    de locações nesta versão (pode ser adicionado futuramente).
    """
    armario = db.query(Armario).filter(Armario.id == armario_id).first()

    if not armario:
        return RedirectResponse(url="/armarios", status_code=302)

    armario.status         = StatusArmario.DISPONIVEL
    armario.locatario_nome = None
    armario.semestre       = None
    armario.alugado_em     = None

    db.commit()

    return RedirectResponse(
        url=f"/armarios/{armario_id}?liberado=ok",
        status_code=302
    )


# ============================================================
# TOGGLE ATIVO — ativa ou desativa o armário
# ============================================================

@router.post("/{armario_id}/toggle-ativo")
def toggle_ativo(
    armario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """
    Desativa o armário removendo-o do mapa.
    Bloqueia se estiver alugado — libere antes de desativar.
    """
    armario = db.query(Armario).filter(Armario.id == armario_id).first()

    if not armario:
        return RedirectResponse(url="/armarios", status_code=302)

    if armario.status == StatusArmario.ALUGADO:
        return RedirectResponse(
            url="/armarios?erro=desativar_alugado",
            status_code=302
        )

    armario.ativo = not armario.ativo
    # Se estava inativo e está reativando, volta como disponível
    if armario.ativo:
        armario.status = StatusArmario.DISPONIVEL

    db.commit()

    return RedirectResponse(url="/armarios", status_code=302)