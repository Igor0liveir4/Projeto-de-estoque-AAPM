# admin
# Popular o banco de dados com usuários admin

from app.database import Session
from app.models.usuario import Usuario
from app.auth import hash_password

USUARIOS = [
    {
        "nome": "Admin",
        "email": "adminlocal@gmail.com",
        "senha": "aapm@senai",
        "role": "admin",
    },
    {
        "nome": "teste",
        "email": "teste@gmail.com",
        "senha": "123456",
        "role": "admin"
    }
]

def criar_usuarios():
    db = Session()
    try:
        for user in USUARIOS:
            existente = db.query(Usuario).filter_by(email=user["email"]).first()
            if existente:
                print(f"Esse e-mail {user["email"]} já está cadastrado no db.")
            else:
                novo_usuario = Usuario(
                    nome=user["nome"],
                    email=user["email"],
                    senha_hash=hash_password(user["senha"]),
                    role=user["role"]
                )
                db.add(novo_usuario)
                print(f"Usuário {user["nome"]} criado com sucesso.")
        db.commit()
    
    except Exception as erro:
        db.rollback()
        print(f"Erro")
    finally:
        db.close()

criar_usuarios()