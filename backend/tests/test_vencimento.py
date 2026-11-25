"""B4 – depois do vencimento a aplicação para de render e ganha status 'vencido'."""
import re
from datetime import date, timedelta

import pytest

from app.services import analytics

PALAVRAS_DE_RECOMENDACAO = re.compile(r"\b(resgat\w*|reaplic\w*|reinvist\w*|invista|compre|venda|vender|comprar|mantenha|manter)\b", re.IGNORECASE)


@pytest.fixture
def rdc_vencido(series):
    cdi, ipca = series
    hoje = date.today()
    vencimento = hoje - timedelta(days=100)
    ativo = {"id": "rdc", "type": "renda_fixa", "name": "RDC CrediAlta", "invested": 1000,
             "start_date": (hoje - timedelta(days=500)).isoformat(), "indexer": "cdi", "rate": 100,
             "maturity": vencimento.isoformat()}
    return ativo, cdi, ipca, hoje, vencimento


def test_valor_congela_na_data_do_vencimento(rdc_vencido):
    ativo, cdi, ipca, hoje, vencimento = rdc_vencido
    hoje_ = analytics.value_asset(ativo, cdi, ipca, None, hoje)
    no_vencimento = analytics.value_asset(ativo, cdi, ipca, None, vencimento)
    assert hoje_["current"] == no_vencimento["current"]
    assert hoje_["cdi_period_pct"] == no_vencimento["cdi_period_pct"]  # comparação no mesmo período


def test_ipca_mais_tambem_para_no_vencimento(rdc_vencido):
    ativo, cdi, ipca, hoje, vencimento = rdc_vencido
    ativo = {**ativo, "indexer": "ipca", "rate": 6}
    assert analytics.value_asset(ativo, cdi, ipca, None, hoje)["current"] == \
        analytics.value_asset(ativo, cdi, ipca, None, vencimento)["current"]


def test_status_e_alerta_proprio_de_vencido(rdc_vencido):
    ativo, cdi, ipca, hoje, _ = rdc_vencido
    d = analytics.build_dashboard([ativo], cdi, ipca, {}, hoje)
    assert d["ativos"][0]["status"] == "vencido"
    alerta = [a for a in d["alertas"] if a["kind"] == "vencido"]
    assert len(alerta) == 1
    texto = " ".join([alerta[0]["title"], alerta[0]["text"], alerta[0]["why"]])
    assert not PALAVRAS_DE_RECOMENDACAO.search(texto), texto  # educativo: não diz o que fazer
    assert not [a for a in d["alertas"] if a["kind"] == "vencimento"]  # não é "vence em N dias"


def test_ativo_ativo_continua_com_status_ativo(series):
    cdi, ipca = series
    hoje = date.today()
    ativo = {"id": "x", "type": "renda_fixa", "name": "LCA", "invested": 1000, "start_date": (hoje - timedelta(days=30)).isoformat(),
             "indexer": "cdi", "rate": 90, "maturity": (hoje + timedelta(days=300)).isoformat()}
    assert analytics.build_dashboard([ativo], cdi, ipca, {}, hoje)["ativos"][0]["status"] == "ativo"
