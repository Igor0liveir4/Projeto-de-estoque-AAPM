# Projeto-de-estoque-AAPM
Temos que criar um site de gerenciamento de para AAPM do senai

Nome: Igor Oliveira
 
função: Desenvolvedor Back-end

Contribuição: funções do site regra de negócio

Nome: Enzo Rodrigues Leal
 
Função: Desenvolvedor Front-end

Contribuição: Organização do repositorio

Nome: Gleidson Brian Muniz Lira

Função: Desenvolvedor Front-End

Contribuição: Estilizar o Front-End do site

# instalar o requirements.txt

```bash
pip install -r requirements.txt
```

# Inicializar o alembic
```bash 
python -m alembic init migrations
```

# Aplicar a migration
```bash
python -m alembic upgrade head
```

# rodar o código 
```bash
python -m uvicorn app.main:app --reload
```