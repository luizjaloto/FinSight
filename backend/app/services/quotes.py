"""Cotações de ações e FIIs (brapi.dev) com cache no MongoDB.

Sem token, a brapi libera apenas alguns códigos de teste; com BRAPI_TOKEN no .env, todos.
Se a cotação não estiver disponível, o painel usa o preço médio e avisa o usuário.

O painel busca as cotações em paralelo, com limite de chamadas simultâneas e um prazo total (ORCAMENTO_TOTAL_S).
Quem não responde a tempo ou falha fica marcado no cache por alguns minutos, para não repetir a chamada.
"""
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx

from ..config import settings

BRAPI_URL = "https://brapi.dev/api/quote/{ticker}"
CACHE_MINUTES = 15          # cotação encontrada vale por 15 min
FALHA_CACHE_MINUTES = 5     # cotação ausente não é pedida de novo por 5 min
MAX_SIMULTANEAS = 5         # chamadas à brapi ao mesmo tempo
ORCAMENTO_TOTAL_S = 8.0     # prazo total para todas as cotações de um painel


def fetch_quote(ticker: str) -> float | None:
    params = {"token": settings.brapi_token} if settings.brapi_token else {}
    try:
        # safe="" escapa também "/", "?" e "#": o ticker não pode mudar o caminho nem os parâmetros (P0-3)
        r = httpx.get(BRAPI_URL.format(ticker=quote(ticker, safe="")), params=params, timeout=10)
        if r.status_code != 200:
            return None
        results = r.json().get("results") or []
        price = results[0].get("regularMarketPrice") if results else None
        return float(price) if price else None
    except Exception:
        return None


def _agora() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _sem_cotacao() -> dict:
    return {"price": None, "as_of": None, "source": "indisponivel"}


def _buscar_em_paralelo(tickers: list[str]) -> dict[str, float | None]:
    """Consulta a brapi em paralelo (no máximo MAX_SIMULTANEAS ao mesmo tempo).

    Quem não responde até ORCAMENTO_TOTAL_S fica com None. As threads só fazem a chamada HTTP;
    a gravação no banco fica na thread da requisição.
    """
    encontrados: dict[str, float | None] = {tk: None for tk in tickers}
    executor = ThreadPoolExecutor(max_workers=min(MAX_SIMULTANEAS, len(tickers)))
    futuros = {executor.submit(fetch_quote, tk): tk for tk in tickers}
    try:
        feitos, _ = wait(futuros, timeout=ORCAMENTO_TOTAL_S)
        for f in feitos:
            try:
                encontrados[futuros[f]] = f.result()
            except Exception:  # fetch_quote já trata erros de rede; isto cobre qualquer outra falha
                encontrados[futuros[f]] = None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return encontrados


def get_quotes(db, tickers: list[str]) -> dict[str, dict]:
    """Cotações de vários ativos. Cada valor é {'price': float | None, 'as_of': iso | None, 'source': str}."""
    now = _agora()
    resultado: dict[str, dict] = {}
    pendentes: dict[str, dict | None] = {}  # ticker -> documento do cache (None se nunca foi consultado)
    for tk in dict.fromkeys(tickers):  # sem repetidos, na ordem original
        cached = db.quotes_cache.find_one({"ticker": tk})
        if cached and cached.get("price") is not None and now - _aware(cached["as_of"]) < timedelta(minutes=CACHE_MINUTES):
            resultado[tk] = {"price": cached["price"], "as_of": _aware(cached["as_of"]).isoformat(), "source": "cache"}
        elif cached and cached.get("falhou_em") and now - _aware(cached["falhou_em"]) < timedelta(minutes=FALHA_CACHE_MINUTES):
            # falha recente: não chama a brapi de novo; usa o último preço conhecido, se houver
            resultado[tk] = _ultimo_conhecido(cached) or _sem_cotacao()
        else:
            pendentes[tk] = cached

    if pendentes:
        buscados = _buscar_em_paralelo(list(pendentes))
        for tk, cached in pendentes.items():
            price = buscados.get(tk)
            if price is not None:
                db.quotes_cache.update_one({"ticker": tk}, {"$set": {"price": price, "as_of": now}, "$unset": {"falhou_em": ""}},
                                           upsert=True)
                resultado[tk] = {"price": price, "as_of": now.isoformat(), "source": "brapi"}
            else:
                db.quotes_cache.update_one({"ticker": tk}, {"$set": {"falhou_em": now}}, upsert=True)
                resultado[tk] = _ultimo_conhecido(cached) or _sem_cotacao()
    return resultado


def _ultimo_conhecido(cached: dict | None) -> dict | None:
    """API indisponível: último valor conhecido, se houver."""
    if cached and cached.get("price") is not None:
        return {"price": cached["price"], "as_of": _aware(cached["as_of"]).isoformat(), "source": "cache-antigo"}
    return None
