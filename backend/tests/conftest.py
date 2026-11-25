import os
import sys
from datetime import date, timedelta
from pathlib import Path

os.environ["MONGO_URI"] = "mongomock://"
os.environ["JWT_SECRET"] = "chave-de-teste-com-pelo-menos-32-caracteres"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


def daily_cdi(days: int = 800, rate: float = 0.0004) -> list:
    """Série diária sintética de CDI (0,04% a.d. ≈ 10,6% a.a.) para testes determinísticos."""
    today = date.today()
    return [(today - timedelta(days=i), rate * 100) for i in range(days, 0, -1)] + [(today, rate * 100)]


def monthly_ipca(months: int = 30, rate: float = 0.4) -> list:
    today = date.today()
    out = []
    y, m = today.year, today.month
    for _ in range(months):
        out.append((date(y, m, 1), rate))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return sorted(out)


@pytest.fixture
def series():
    return daily_cdi(), monthly_ipca()


@pytest.fixture
def client(monkeypatch, series):
    from fastapi.testclient import TestClient

    from app import db as dbmod
    from app.services import bcb, quotes

    dbmod._client.cache_clear()
    cdi, ipca = series
    monkeypatch.setattr(bcb, "get_series",
                        lambda db, name, **kw: bcb.Series(cdi if name == "cdi" else ipca, (cdi if name == "cdi" else ipca)[0][0]))
    monkeypatch.setattr(quotes, "fetch_quote", lambda ticker: {"PETR4": 38.0, "HGLG11": 160.0}.get(ticker))
    from app.main import app

    with TestClient(app) as c:
        yield c
    dbmod._client.cache_clear()


@pytest.fixture
def auth(client):
    r = client.post("/auth/register", json={"name": "Teste", "email": "teste@finsight.app", "password": "senha-forte-1", "accept_terms": True})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
