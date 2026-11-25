"""B3 – séries do Banco Central desde a aplicação mais antiga, em janelas aceitas pelo SGS."""
from datetime import date, timedelta

import httpx
import pytest

from app.clock import today_br
from app.services import bcb

GET_SERIES_REAL = bcb.get_series  # guardado antes de o conftest substituir no fixture `client`
HOJE = today_br()
TAXA_DIA = 0.0005  # 0,05% ao dia, constante, para o valor de referência ser exato
LIMITE_SGS_DIAS = 3653  # o SGS recusa (HTTP 406) janelas acima de 10 anos em séries diárias


def _serie_sintetica(ini: date, fim: date):
    d, out = ini, []
    while d <= fim:
        out.append((d, TAXA_DIA * 100))
        d += timedelta(days=1)
    return out


class FakeSGS:
    """Imita o SGS: devolve o recorte pedido e recusa janelas diárias acima de 10 anos."""

    def __init__(self):
        self.chamadas = []
        self.fora_do_ar = False
        self.cdi = _serie_sintetica(HOJE - timedelta(days=365 * 15), HOJE)

    def __call__(self, name, start, end, client=None):
        self.chamadas.append((name, start, end))
        if self.fora_do_ar:
            raise httpx.ConnectError("SGS fora do ar")
        if name == "cdi" and (end - start).days > LIMITE_SGS_DIAS:
            raise httpx.HTTPStatusError("406", request=None, response=None)
        if name == "cdi":
            return [(d, v) for d, v in self.cdi if start <= d <= end]
        return [(date(y, m, 1), 0.4) for y in range(start.year, end.year + 1) for m in range(1, 13)
                if start <= date(y, m, 1) <= end]


@pytest.fixture
def sgs(client, monkeypatch):
    fake = FakeSGS()
    monkeypatch.setattr(bcb, "get_series", GET_SERIES_REAL)
    monkeypatch.setattr(bcb, "fetch_series", fake)
    return fake


def _rdc(anos):
    return {"type": "renda_fixa", "name": f"RDC {anos} anos", "invested": 1000,
            "start_date": (HOJE - timedelta(days=round(365.25 * anos))).isoformat(), "indexer": "cdi", "rate": 100}


def test_renda_fixa_de_5_anos_bate_com_a_referencia(client, auth, sgs):
    corpo = _rdc(5)
    assert client.post("/portfolio/assets", json=corpo, headers=auth).status_code == 201
    inicio = date.fromisoformat(corpo["start_date"])
    dias = (HOJE - inicio).days  # dias da série no intervalo (inicio, hoje]
    referencia_pct = ((1 + TAXA_DIA) ** dias - 1) * 100

    d = client.get("/dashboard", headers=auth).json()
    ativo = d["ativos"][0]
    assert abs(ativo["return_pct"] - referencia_pct) <= 0.01, (ativo["return_pct"], referencia_pct)
    assert abs(ativo["cdi_period_pct"] - referencia_pct) <= 0.01


def test_busca_em_janelas_aceitas_pelo_sgs(client, auth, sgs):
    """Aplicação de 12 anos: o histórico é buscado em mais de uma consulta, cada uma dentro do limite."""
    assert client.post("/portfolio/assets", json=_rdc(12), headers=auth).status_code == 201
    r = client.get("/dashboard", headers=auth)
    assert r.status_code == 200
    cdi = [c for c in sgs.chamadas if c[0] == "cdi"]
    assert len(cdi) >= 2
    assert all((fim - ini).days <= LIMITE_SGS_DIAS for _, ini, fim in cdi)
    assert min(ini for _, ini, _ in cdi) <= HOJE - timedelta(days=round(365.25 * 12))


def test_cache_cobre_a_faixa_e_nao_busca_de_novo(client, auth, sgs):
    client.post("/portfolio/assets", json=_rdc(5), headers=auth)
    client.get("/dashboard", headers=auth)
    antes = len(sgs.chamadas)
    client.get("/dashboard", headers=auth)
    assert len(sgs.chamadas) == antes  # faixa já coberta e cache recente


def test_api_fora_do_ar_usa_cache_antigo_e_avisa(client, auth, sgs):
    from app.db import get_db

    client.post("/portfolio/assets", json=_rdc(2), headers=auth)
    client.get("/dashboard", headers=auth)
    get_db().indicators.update_many({}, {"$set": {"updated_at": bcb.utcnow() - timedelta(days=3)}})  # cache vencido
    sgs.fora_do_ar = True
    r = client.get("/dashboard", headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["indicadores_desatualizados"] is True
    assert any(a["kind"] == "indicadores" for a in d["alertas"])
