# 1. Hash e verificação de senha com bcrypt
# 2. Geração de token JWT
# 3. Leitura e validação do token vindo do cokie

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")

# CryptContext - configura o bcrypt como algoritmo de hash
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Função de senha
def hash_password(password: str):
    return pwd_context.hash(password)

def verificar_senha(senha: str, senha_hash: str):
    return pwd_context.verify(senha, senha_hash)

# Função do token - JWT
def criar_token(data: dict):
    payload = data.copy()

    # Define o tempo de expiração do token
    expira = datetime.now(timezone.utc) + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    payload

    # Criar o token JWT
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def decodificar_token(token: str):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload

# Dependências do FastAPI
def get_usuario_logado(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido"
        )

    try:
        payload = decodificar_token(token)
        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
def get_usuario_opcional(request: Request):
    try:
        return get_usuario_logado(request)
    except HTTPException:
        return None
    
# Quando um usuario é admin
def get_admin(request: Request):
    usuario = get_usuario_logado(request)

    if usuario.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Admins apenas"
        )
    else:
        return usuario