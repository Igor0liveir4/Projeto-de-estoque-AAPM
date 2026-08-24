from dataclasses import dataclass
from math import ceil


TAMANHOS_DE_PAGINA = (16, 32, 64)


@dataclass(frozen=True)
class Pagina:
    itens: list
    atual: int
    por_pagina: int
    total_itens: int
    total_paginas: int


def paginar(query, pagina: int = 1, por_pagina: int = 16) -> Pagina:
    """Aplica uma paginação segura e padronizada a uma query SQLAlchemy."""
    por_pagina = por_pagina if por_pagina in TAMANHOS_DE_PAGINA else 16
    total_itens = query.order_by(None).count()
    total_paginas = max(ceil(total_itens / por_pagina), 1)
    atual = min(max(pagina, 1), total_paginas)

    return Pagina(
        itens=query.offset((atual - 1) * por_pagina).limit(por_pagina).all(),
        atual=atual,
        por_pagina=por_pagina,
        total_itens=total_itens,
        total_paginas=total_paginas,
    )
