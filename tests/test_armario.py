from datetime import datetime, timedelta, timezone

from app.models.armario import Armario, StatusArmario


def test_armario_novo_fica_disponivel(db_session):
    armario = Armario(numero="A01")
    db_session.add(armario)
    db_session.flush()

    assert armario.disponivel
    assert not armario.acesso_ativo
    assert armario.dias_aluguel == 0


def test_armario_alugado_tem_acesso_ativo_antes_de_30_dias():
    armario = Armario(
        numero="A02",
        status=StatusArmario.ALUGADO,
        alugado_em=datetime.now(timezone.utc) - timedelta(days=10),
    )

    assert armario.acesso_ativo
    assert armario.dias_aluguel == 10


def test_armario_alugado_expira_apos_30_dias():
    armario = Armario(
        numero="A03",
        status=StatusArmario.ALUGADO,
        alugado_em=datetime.now(timezone.utc) - timedelta(days=31),
    )

    assert not armario.acesso_ativo
    assert armario.prazo_vencimento == armario._to_utc(armario.alugado_em) + timedelta(days=30)


def test_armario_inativo_nao_tem_acesso_ativo():
    armario = Armario(
        numero="A04",
        status=StatusArmario.INATIVO,
        alugado_em=datetime.now(timezone.utc),
    )

    assert not armario.acesso_ativo
