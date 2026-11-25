"""B9 – a data do sistema é a de Brasília, não a do servidor (UTC)."""
from datetime import date, datetime, timezone

import pytest

# 10/03/2027 às 22:54 em Brasília = 11/03/2027 às 01:54 em UTC
RELOGIO_UTC = datetime(2027, 3, 11, 1, 54, tzinfo=timezone.utc)


@pytest.fixture
def relogio_fixo(monkeypatch):
    from app import clock

    monkeypatch.setattr(clock, "_now", lambda: RELOGIO_UTC)
    return clock


def test_today_br_as_22h54_de_brasilia(relogio_fixo):
    assert relogio_fixo.today_br() == date(2027, 3, 10)


def test_importacao_usa_o_dia_de_brasilia(client, auth, relogio_fixo):
    """A data é injetada nos serviços a partir de today_br(), nunca de date.today()."""
    csv = "Código de Negociação;Quantidade;Preço de Fechamento\nPETR4;10;38,00\n"
    r = client.post("/portfolio/import-csv", headers=auth, files={"file": ("p.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200
    ativos = client.get("/portfolio", headers=auth).json()["assets"]
    assert ativos[0]["start_date"] == "2027-03-10"
