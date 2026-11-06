from app.pagination import paginar


class FakeQuery:
    def __init__(self, values):
        self.values = values
        self.offset_value = 0
        self.limit_value = len(values)

    def order_by(self, *_args):
        return self

    def count(self):
        return len(self.values)

    def offset(self, value):
        self.offset_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        return self.values[self.offset_value:self.offset_value + self.limit_value]


def test_paginacao_seleciona_itens_e_total_de_paginas():
    resultado = paginar(FakeQuery(list(range(20))), pagina=2, por_pagina=16)

    assert resultado.itens == [16, 17, 18, 19]
    assert resultado.atual == 2
    assert resultado.total_itens == 20
    assert resultado.total_paginas == 2


def test_paginacao_corrige_pagina_fora_do_intervalo_e_tamanho_invalido():
    resultado = paginar(FakeQuery(["a", "b"]), pagina=0, por_pagina=5)

    assert resultado.atual == 1
    assert resultado.por_pagina == 16
    assert resultado.itens == ["a", "b"]
