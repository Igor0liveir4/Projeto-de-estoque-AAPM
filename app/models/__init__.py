# Gerar as migrations
# python -m alembic revision --autogenerate -m "Criando tabelas de movimentação"
# python -m alembic upgrade head

from app.models import categoria
from app.models  import produto
from app.models import usuario
from app.models import movimentacao