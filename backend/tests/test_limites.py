"""B2 – valores extremos nunca geram erro 500; um ativo ruim não derruba o painel."""
from datetime import timedelta

import pytest

from app.clock import today_br

HOJE = today_br()
INICIO = (HOJE - timedelta(days=120)).isoformat()
AMANHA = (HOJE + timedelta(days=1)).isoformat()

RF = {"type": "renda_fixa", "name": "RDC", "invested": 1000, "start_date": INICIO, "indexer": "cdi", "rate": 100}
ACAO = {"type": "acao", "name": "Petrobras", "ticker": "PETR4", "quantity": 10, "avg_price": 30, "invested": 300, "start_date": INICIO}

INVALIDOS = [
    ("ipca_taxa_-150", {**RF, "indexer": "ipca", "rate": -150}),
    ("ipca_taxa_51", {**RF, "indexer": "ipca", "rate": 51}),
    ("cdi_taxa_1e308", {**RF, "rate": 1e308}),
    ("cdi_taxa_501", {**RF, "rate": 501}),
    ("cdi_taxa_zero", {**RF, "rate": 0}),
    ("cdi_taxa_negativa", {**RF, "rate": -5}),
    ("valor_1e308", {**RF, "invested": 1e308}),
    ("valor_zero", {**RF, "invested": 0}),
    ("valor_acima_do_teto", {**RF, "invested": 100_000_001}),
    ("quantidade_1e12", {**ACAO, "quantity": 1e12}),
    ("preco_1e9", {**ACAO, "avg_price": 1e9}),
    ("data_no_futuro", {**RF, "start_date": AMANHA}),
    ("vencimento_antes_da_aplicacao", {**RF, "maturity": (HOJE - timedelta(days=200)).isoformat()}),
    ("acao_com_vencimento", {**ACAO, "maturity": AMANHA}),
    ("acao_com_indexador", {**ACAO, "indexer": "cdi", "rate": 100}),
    ("renda_fixa_com_ticker", {**RF, "ticker": "PETR4"}),
    ("renda_fixa_com_quantidade", {**RF, "quantity": 10, "avg_price": 5}),
]


@pytest.mark.parametrize("nome,corpo", INVALIDOS, ids=[n for n, _ in INVALIDOS])
def test_cadastro_com_valor_extremo_da_422(client, auth, nome, corpo):
    r = client.post("/portfolio/assets", json=corpo, headers=auth)
    assert r.status_code == 422, (nome, r.status_code, r.text)


@pytest.mark.parametrize("corpo", [
    {**RF, "indexer": "ipca", "rate": -10}, {**RF, "indexer": "ipca", "rate": 50}, {**RF, "rate": 500},
    {**RF, "start_date": HOJE.isoformat()}, {**RF, "maturity": INICIO},
])
def test_limites_validos_sao_aceitos(client, auth, corpo):
    assert client.post("/portfolio/assets", json=corpo, headers=auth).status_code == 201


def test_ativo_ruim_ja_gravado_nao_derruba_o_painel(client, auth):
    """Dados antigos, gravados antes da validação, viram 'erro de cálculo' e o resto do painel segue."""
    from app.db import get_db

    client.post("/portfolio/assets", json=RF, headers=auth)
    db = get_db()
    uid = db.users.find_one({"email": "teste@finsight.app"})["_id"]
    ruins = [
        {**RF, "id": "ruim1", "name": "IPCA -150", "indexer": "ipca", "rate": -150},
        {**RF, "id": "ruim2", "name": "CDI 1e308", "rate": 1e308},
        {**RF, "id": "ruim3", "name": "Sem taxa", "rate": None},
    ]
    db.portfolios.update_one({"user_id": uid}, {"$push": {"assets": {"$each": ruins}}})

    r = client.get("/dashboard", headers=auth)
    assert r.status_code == 200, r.text
    d = r.json()
    erros = {a["id"] for a in d["ativos"] if a.get("calc_error")}
    assert erros == {"ruim1", "ruim2", "ruim3"}
    ok = [a for a in d["ativos"] if not a.get("calc_error")]
    assert len(ok) == 1 and d["patrimonio"] == ok[0]["current"]
    assert any(a["kind"] == "erro_calculo" for a in d["alertas"])
