from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.auth import hash_password, verificar_senha, criar_token

# APIROUTER agrupa as rotas desse arquivo com prefixo /auth
router = APIRouter(prefix="/auth", tags=["Autentificação"])

# Configura para renderizar os templates HTML
templates = Jinja2Templates(directory="app/templates")

# Rota para tela de cadastro
@router.get("/cadastro")
def tela_cadastro(request: Request):
    return templates.TemplateResponse(
        request,
        "auth/cadastro.html",
        {"request": request}
        )

@router.get("/login")
def tela_login(request: Request):
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"request": request}
        )

# Rota para criar um novo usuário no banco de dados
@router.post("/cadastro")
def fazer_cadastro(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)   
):
    # Verificar o email do usuario
    usuario_existente = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario_existente:
        return templates.TemplateResponse(
            request,
            "auth/cadastro.html",
            {
                "request": request,
                "erro": "Email já cadastrado"
            }
        )
    
    # Criar o usuário
    novo_usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=hash_password(senha)
    )
    db.add(novo_usuario)
    db.commit()

    # Redirecionar para a tela de login após cadastro bem-sucedido
    return RedirectResponse(url="/auth/login?cadastro=ok", status_code=302)

@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Processa o login e define o cookie JWT.

    Fluxo:
    1. Busca o usuário pelo email
    2. Verifica a senha com bcrypt
    3. Gera o token JWT
    4. Salva o token em um cookie HttpOnly
    5. Redireciona para a página principal
    """

    # Busca o usuário no banco pelo email
    usuario = db.query(Usuario).filter(
        Usuario.email == email
    ).first()

    # Verifica usuário E senha em passos separados para evitar
    # "timing attacks" (atacante deduz se o email existe pelo tempo de resposta)
    senha_correta = (
        usuario is not None and
        verificar_senha(senha, usuario.senha_hash)
    )

    if not senha_correta:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "request": request,
                "erro": "E-mail ou senha incorretos."
            },
            status_code=401
        )

    if not usuario.ativo:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "request": request,
                "erro": "Usuário inativo. Contate o administrador."
            },
            status_code=403
        )

    # Dados que ficarão no payload do JWT
    # "sub" (subject) é a convenção JWT para identificar o usuário
    token_data = {
        "sub": usuario.email,
        "nome": usuario.nome,
        "role": usuario.role,
        "id": usuario.id
    }

    token = criar_token(token_data)

    # Cria a resposta de redirecionamento
    response = RedirectResponse(url="/", status_code=302)

    # Define o cookie com o token JWT
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,    # JavaScript NÃO pode ler este cookie (proteção XSS)
        max_age=3600,     # expira em 1 hora (em segundos)
        samesite="lax",   # proteção básica contra CSRF
        # secure=True     # ativar em produção (exige HTTPS)
    )

    return response

# Rota para sair
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response