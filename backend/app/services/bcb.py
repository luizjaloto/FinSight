"""Indicadores oficiais do Banco Central (API SGS) com cache no MongoDB (RF07).

Séries usadas:
  12  – CDI, taxa diária (% a.d.)
  433 – IPCA, variação mensal (%)
"""
from datetime import date, datetime, timedelta, timezone

import httpx

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
SERIES = {"cdi": 12, "ipca": 433}
CACHE_HOURS = 12


def _parse(rows: list[dict]) -> list[tuple[date, float]]:
    out = []
    for r in rows:
        d = datetime.strptime(r["data"], "%d/%m/%Y").date()
        out.append((d, float(str(r["valor"]).replace(",", "."))))
    return out


def fetch_series(name: str, start: date, end: date, client: httpx.Client | None = None) -> list[tuple[date, float]]:
    """Busca uma série no SGS. Levanta exceção se a API estiver indisponível."""
    params = {"formato": "json", "dataInicial": start.strftime("%d/%m/%Y"), "dataFinal": end.strftime("%d/%m/%Y")}
    own = client is None
    client = client or httpx.Client(timeout=15)
    try:
        r = client.get(SGS_URL.format(serie=SERIES[name]), params=params)
        r.raise_for_status()
        return _parse(r.json())
    finally:
        if own:
            client.close()


def get_series(db, name: str, years: int = 3, *, today: date) -> list[tuple[date, float]]:
    """Série dos últimos `years` anos, usando o cache se ainda estiver válido."""
    cached = db.indicators.find_one({"serie": name})
    now = datetime.now(timezone.utc)
    if cached:
        updated = cached["updated_at"]
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        if now - updated < timedelta(hours=CACHE_HOURS):
            return [(date.fromisoformat(d), v) for d, v in cached["values"]]
    end = today
    start = end - timedelta(days=365 * years)
    try:
        values = fetch_series(name, start, end)
    except Exception:
        if cached:  # API fora do ar: usa o último cache disponível
            return [(date.fromisoformat(d), v) for d, v in cached["values"]]
        raise
    db.indicators.update_one(
        {"serie": name},
        {"$set": {"values": [(d.isoformat(), v) for d, v in values], "updated_at": now}},
        upsert=True,
    )
    return values


def accumulated(series: list[tuple[date, float]], start: date, end: date, factor: float = 1.0) -> float:
    """Variação acumulada (fração) entre start e end. `factor` aplica % do índice (ex.: 1.05 = 105% do CDI)."""
    acc = 1.0
    for d, v in series:
        if start < d <= end:
            acc *= 1 + factor * v / 100
    return acc - 1


def accumulated_monthly(series: list[tuple[date, float]], start: date, end: date) -> float:
    """Variação acumulada de uma série mensal (IPCA), considerando os meses completos do período."""
    acc = 1.0
    for d, v in series:
        if date(start.year, start.month, 1) < d <= end:
            acc *= 1 + v / 100
    return acc - 1


def summary(db, today: date) -> dict:
    """CDI e IPCA acumulados em 12 meses e o último valor de cada série."""
    cdi = get_series(db, "cdi", today=today)
    ipca = get_series(db, "ipca", today=today)
    end = cdi[-1][0] if cdi else today
    start = end - timedelta(days=365)
    return {
        "cdi_12m": round(accumulated(cdi, start, end) * 100, 2),
        "ipca_12m": round(accumulated_monthly(ipca, start, end) * 100, 2),
        "cdi_ultimo_dia": cdi[-1][0].isoformat() if cdi else None,
        "ipca_ultimo_mes": ipca[-1][0].isoformat() if ipca else None,
        "fonte": "Banco Central do Brasil – SGS (séries 12 e 433)",
    }
