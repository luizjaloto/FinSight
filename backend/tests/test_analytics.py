"""Testes dos cálculos (T07, T08)."""
from datetime import date, timedelta

import pytest

from app.services import analytics, bcb


def test_cdi_105_rende_mais_que_cdi(series):
    cdi, ipca = series
    today = date.today()
    start = today - timedelta(days=365)
    a = {"id": "1", "type": "renda_fixa", "name": "RDC", "invested": 10000, "start_date": start.isoformat(), "indexer": "cdi", "rate": 105}
    v = analytics.value_asset(a, cdi, ipca, None, today)
    cdi_acc = bcb.accumulated(cdi, start, today)
    esperado = 10000 * (1 + bcb.accumulated(cdi, start, today, factor=1.05))
    assert v["current"] == pytest.approx(esperado, abs=0.01)
    assert v["return_pct"] > round(cdi_acc * 100, 2)


def test_precisao_contra_calculo_manual(series):
    """T07: diferença ≤ 0,1 p.p. em relação ao cálculo de conferência (juros compostos diários)."""
    cdi, ipca = series
    today = date.today()
    start = today - timedelta(days=100)
    a = {"id": "1", "type": "renda_fixa", "name": "RDC", "invested": 1000, "start_date": start.isoformat(), "indexer": "cdi", "rate": 100}
    v = analytics.value_asset(a, cdi, ipca, None, today)
    manual = ((1 + 0.0004) ** 100 - 1) * 100
    assert abs(v["return_pct"] - manual) <= 0.1


def test_hhi_e_faixas():
    assert analytics.hhi([1.0]) == 1.0
    assert analytics.diversification([1.0])["band"] == "baixa"
    assert analytics.diversification([0.25] * 4)["score"] == 75
    assert analytics.diversification([0.25] * 4)["band"] == "boa"
    assert analytics.diversification([0.5, 0.3, 0.2])["band"] == "média"


@pytest.mark.parametrize("peso,deve_alertar", [(0.20, False), (0.25, False), (0.26, True), (0.60, True)])
def test_alerta_concentracao(peso, deve_alertar):
    """T08: alerta quando um ativo passa de 25% da carteira."""
    total = 1000
    items = [{"name": "A", "ticker": "PETR4", "current": peso * total, "maturity": None},
             {"name": "B", "ticker": None, "current": (1 - peso) * total / 4, "maturity": None}]
    out = [x for x in analytics.alerts(items, total, date.today(), 0.25, 30) if x["kind"] == "concentracao" and "PETR4" in x["title"]]
    assert bool(out) is deve_alertar
    if out:
        assert "não uma recomendação" in out[0]["why"]


def test_alerta_vencimento():
    today = date.today()
    items = [{"name": "RDC", "ticker": None, "current": 100, "maturity": (today + timedelta(days=10)).isoformat()},
             {"name": "LCA", "ticker": None, "current": 100, "maturity": (today + timedelta(days=90)).isoformat()}]
    out = [x for x in analytics.alerts(items, 1000, today, 0.25, 30) if x["kind"] == "vencimento"]
    assert len(out) == 1 and "10 dia" in out[0]["title"]


def test_dashboard_compara_com_cdi(series):
    cdi, ipca = series
    today = date.today()
    start = (today - timedelta(days=200)).isoformat()
    assets = [
        {"id": "1", "type": "renda_fixa", "name": "RDC", "invested": 5000, "start_date": start, "indexer": "cdi", "rate": 110},
        {"id": "2", "type": "acao", "name": "Petrobras", "ticker": "PETR4", "quantity": 100, "avg_price": 30, "invested": 3000, "start_date": start},
    ]
    d = analytics.build_dashboard(assets, cdi, ipca, {"PETR4": 33.0}, today)
    assert d["patrimonio"] > d["investido"]
    assert d["superou_cdi"] is True
    assert sum(x["pct"] for x in d["alocacao"]) == pytest.approx(100, abs=0.2)
    assert d["diversificacao"]["band"] in {"baixa", "média", "boa"}
