from app.auth import hash_password
from app.models.usuario import Usuario


def test_home_publica_exibe_pagina_inicial(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_area_protegida_redireciona_visitante(client):
    response = client.get("/produtos/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_contato_publico(client):
    response = client.get("/contato")

    assert response.status_code == 200


def test_rota_inexistente_retorna_pagina_404(client):
    response = client.get("/rota-que-nao-existe")

    assert response.status_code == 404


def test_login_valido_define_cookie_de_sessao(client, db_session):
    db_session.add(
        Usuario(
            nome="Operador",
            email="operador@example.com",
            senha_hash=hash_password("senha-segura"),
        )
    )
    db_session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "operador@example.com", "senha": "senha-segura"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/"
    assert "access_token" in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()


def test_login_com_senha_incorreta_e_recusado(client, db_session):
    db_session.add(
        Usuario(
            nome="Operador",
            email="operador@example.com",
            senha_hash=hash_password("senha-segura"),
        )
    )
    db_session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "operador@example.com", "senha": "errada"},
    )

    assert response.status_code == 401
