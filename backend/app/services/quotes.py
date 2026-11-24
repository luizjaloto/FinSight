"""Cotações de ações e FIIs (brapi.dev) com cache diário no MongoDB.

Sem token, a brapi libera apenas alguns códigos de teste; com BRAPI_TOKEN no .env, todos.
Se a cotação não estiver disponível, o painel usa o preço médio e avisa o usuário.
"""
from datetime import datetime, timedelta, timezone

import httpx

from ..config import settings

BRAPI_URL = "https://brapi.dev/api/quote/{ticker}"
CACHE_MINUTES = 15


def fetch_quote(ticker: str) -> float | None:
    params = {"token": settings.brapi_token} if settings.brapi_token else {}
    try:
        r = httpx.get(BRAPI_URL.format(ticker=ticker), params=params, timeout=10)
        if r.status_code != 200:
            return None
        results = r.json().get("results") or []
        price = results[0].get("regularMarketPrice") if results else None
        return float(price) if price else None
    except Exception:
        return None


def get_quote(db, ticker: str) -> dict:
    """Retorna {'price': float | None, 'as_of': iso | None, 'source': str}."""
    now = datetime.now(timezone.utc)
    cached = db.quotes_cache.find_one({"ticker": ticker})
    if cached:
        at = cached["as_of"]
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        if now - at < timedelta(minutes=CACHE_MINUTES):
            return {"price": cached["price"], "as_of": at.isoformat(), "source": "cache"}
    price = fetch_quote(ticker)
    if price is not None:
        db.quotes_cache.update_one({"ticker": ticker}, {"$set": {"price": price, "as_of": now}}, upsert=True)
        return {"price": price, "as_of": now.isoformat(), "source": "brapi"}
    if cached:  # API indisponível: último valor conhecido
        return {"price": cached["price"], "as_of": cached["as_of"].isoformat(), "source": "cache-antigo"}
    return {"price": None, "as_of": None, "source": "indisponivel"}
