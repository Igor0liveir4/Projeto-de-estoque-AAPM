from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import JWTError, jwt
from starlette.requests import Request

from app import auth


def test_hash_e_verificacao_de_senha():
    senha_hash = auth.hash_password("Senha-forte-123")

    assert senha_hash != "Senha-forte-123"
    assert auth.verificar_senha("Senha-forte-123", senha_hash)
    assert not auth.verificar_senha("senha-incorreta", senha_hash)


def test_token_preserva_dados_do_usuario():
    token = auth.criar_token({"sub": "aluno@example.com", "role": "user"})

    assert auth.decodificar_token(token)["sub"] == "aluno@example.com"
    assert auth.decodificar_token(token)["role"] == "user"


def test_token_expirado_e_rejeitado():
    token = jwt.encode(
        {"sub": "aluno@example.com", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )

    with pytest.raises(JWTError):
        auth.decodificar_token(token)


def test_usuario_sem_cookie_nao_autenticado():
    request = Request({"type": "http", "headers": [], "cookies": {}})

    with pytest.raises(HTTPException) as erro:
        auth.get_usuario_logado(request)

    assert erro.value.status_code == 401


def test_usuario_opcional_retorna_none_sem_sessao():
    request = Request({"type": "http", "headers": [], "cookies": {}})

    assert auth.get_usuario_opcional(request) is None
