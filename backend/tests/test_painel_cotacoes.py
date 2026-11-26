"""P2-4 – GET /dashboard: cotações em paralelo com limite e prazo, falha em cache e GET sem escrita."""
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

from app.services import quotes

INICIO = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)


@pytest.fixture
def db():
    from app import db as dbmod

    dbmod._client.cache_clear()
    yield dbmod.get_db()
    dbmod._client.cache_clear()


@pytest.fixture
def relogio(monkeypatch):
    """Relógio das cotações: começa num instante fixo e avança quando o teste pede."""
    estado = {"agora": INICIO}
    monkeypatch.setattr(quotes, "_agora", lambda: estado["agora"])

    def avancar(segundos):
        estado["agora"] += timedelta(seconds=segundos)

    return avancar


def test_get_dashboard_nao_grava_alertas(client, auth):
    """A rota GET não apaga nem grava na coleção alerts; os alertas voltam só na resposta."""
    from app.db import get_db

    start = (INICIO - timedelta(days=60)).date().isoformat()
    client.post("/portfolio/assets", headers=auth, json={"type": "acao", "name": "Petrobras", "ticker": "PETR4", "quantity": 100,
                                                          "avg_price": 35, "invested": 3500, "start_date": start})
    db = get_db()
    uid = db.users.find_one({"email": "teste@finsight.app"})["_id"]
    db.alerts.insert_one({"user_id": uid, "kind": "legado"})

    d = client.get("/dashboard", headers=auth).json()

    assert any(a["kind"] == "concentracao" for a in d["alertas"])
    assert db.alerts.count_documents({"user_id": uid}) == 1  # o alerta antigo não foi apagado nem foram gravados novos


def test_cotacoes_buscadas_em_paralelo_com_limite(db, monkeypatch):
    em_voo = {"atual": 0, "pico": 0}
    trava = threading.Lock()

    def lenta(ticker):
        with trava:
            em_voo["atual"] += 1
            em_voo["pico"] = max(em_voo["pico"], em_voo["atual"])
        time.sleep(0.05)
        with trava:
            em_voo["atual"] -= 1
        return 10.0

    monkeypatch.setattr(quotes, "fetch_quote", lenta)
    tickers = [f"AAAA{i}" for i in range(1, 13)]

    r = quotes.get_quotes(db, tickers)

    assert all(r[t]["price"] == 10.0 and r[t]["source"] == "brapi" for t in tickers)
    assert 1 < em_voo["pico"] <= quotes.MAX_SIMULTANEAS


def test_orcamento_total_de_tempo_corta_quem_demora(db, monkeypatch):
    monkeypatch.setattr(quotes, "ORCAMENTO_TOTAL_S", 0.3)

    def fake(ticker):
        if ticker == "LENTA11":
            time.sleep(2)
            return 1.0
        return 5.0

    monkeypatch.setattr(quotes, "fetch_quote", fake)
    inicio = time.monotonic()

    r = quotes.get_quotes(db, ["RAPIDA3", "LENTA11"])

    assert time.monotonic() - inicio < 1.5
    assert r["RAPIDA3"]["price"] == 5.0
    assert r["LENTA11"] == {"price": None, "as_of": None, "source": "indisponivel"}


def test_falha_fica_em_cache_por_alguns_minutos(db, monkeypatch, relogio):
    chamadas = []

    def sem_cotacao(ticker):
        chamadas.append(ticker)
        return None

    monkeypatch.setattr(quotes, "fetch_quote", sem_cotacao)

    assert quotes.get_quotes(db, ["ZZZZ3"])["ZZZZ3"]["source"] == "indisponivel"
    quotes.get_quotes(db, ["ZZZZ3"])
    assert chamadas == ["ZZZZ3"]  # dentro da janela, não repete a chamada

    relogio((quotes.FALHA_CACHE_MINUTES + 1) * 60)
    quotes.get_quotes(db, ["ZZZZ3"])
    assert chamadas == ["ZZZZ3", "ZZZZ3"]  # passada a janela, tenta de novo


def test_falha_usa_ultimo_preco_conhecido_e_nao_repete_a_chamada(db, monkeypatch, relogio):
    precos = {"PETR4": 38.0}
    chamadas = []

    def brapi(ticker):
        chamadas.append(ticker)
        return precos.get(ticker)

    monkeypatch.setattr(quotes, "fetch_quote", brapi)
    assert quotes.get_quotes(db, ["PETR4"])["PETR4"]["source"] == "brapi"

    relogio(quotes.CACHE_MINUTES * 60 + 1)  # cotação antiga, brapi agora falha
    precos.clear()
    r = quotes.get_quotes(db, ["PETR4"])["PETR4"]
    assert r["price"] == 38.0 and r["source"] == "cache-antigo"

    quotes.get_quotes(db, ["PETR4"])  # dentro da janela de falha: usa o cache sem chamar a brapi
    assert chamadas == ["PETR4", "PETR4"]
    assert quotes.get_quotes(db, ["PETR4"])["PETR4"]["price"] == 38.0


def test_sucesso_depois_de_falha_limpa_a_marca_de_falha(db, monkeypatch, relogio):
    respostas = iter([None, 12.5])
    monkeypatch.setattr(quotes, "fetch_quote", lambda ticker: next(respostas))

    quotes.get_quotes(db, ["HGLG11"])
    relogio((quotes.FALHA_CACHE_MINUTES + 1) * 60)
    r = quotes.get_quotes(db, ["HGLG11"])["HGLG11"]

    assert r["price"] == 12.5 and r["source"] == "brapi"
    assert "falhou_em" not in db.quotes_cache.find_one({"ticker": "HGLG11"})
