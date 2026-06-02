# Gerar as migrations
# python -m alembic revision --autogenerate -m "Criando tabelas de venda"
# python -m alembic upgrade head

from app.models import categoria
from app.models  import produto
from app.models import usuario
from app.models import movimentacao
from app.models import cliente
from app.models import venda