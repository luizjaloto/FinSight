"""Indicadores oficiais do Banco Central (API SGS) com cache no MongoDB (RF07).

Séries usadas:
  12  – CDI, taxa diária (% a.d.)
  433 – IPCA, variação mensal (%)
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
SERIES = {"cdi": 12, "ipca": 433}
CACHE_HOURS = 12
# O SGS recusa (HTTP 406) consultas acima de 10 anos em séries diárias – verificado na API em 24/11/2026.
# Usamos janelas de 9 anos para ter folga. A série mensal do IPCA não tem esse limite, mas usa a mesma janela.
WINDOW_DAYS = 9 * 365
# Margem antes da aplicação mais antiga: cobre feriados e meses incompletos do IPCA.
MARGIN_DAYS = 45


class BcbUnavailable(Exception):
    """API do Banco Central indisponível e sem cache utilizável."""


@dataclass
class Series:
    values: list[tuple[date, float]]
    covers_from: date | None   # primeira data que a busca cobriu
    stale: bool = False        # True quando a API falhou e usamos um cache antigo ou que não cobre todo o período


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


def fetch_range(name: str, start: date, end: date) -> list[tuple[date, float]]:
    """Busca [start, end] em janelas de até WINDOW_DAYS dias, dentro do limite do SGS."""
    values: list[tuple[date, float]] = []
    ini = start
    while ini <= end:
        fim = min(ini + timedelta(days=WINDOW_DAYS), end)
        values.extend(fetch_series(name, ini, fim))
        ini = fim + timedelta(days=1)
    return sorted(dict(values).items())


def _load(cached: dict) -> tuple[list[tuple[date, float]], date | None]:
    values = [(date.fromisoformat(d), v) for d, v in cached.get("values", [])]
    covers = cached.get("covers_from")
    covers_from = date.fromisoformat(covers) if covers else (values[0][0] if values else None)
    return values, covers_from


def get_series(db, name: str, *, since: date, today: date) -> Series:
    """Série de `since` (menos uma margem) até hoje, com cache por faixa (B3).

    - Cache recente que já cobre a faixa: usado sem consultar a API.
    - Caso contrário, busca a faixa inteira em janelas e grava o resultado junto com o que o cache já tinha.
    - API fora do ar: devolve o cache antigo com stale=True, para o painel avisar o usuário.
    """
    need_from = since - timedelta(days=MARGIN_DAYS)
    cached = db.indicators.find_one({"serie": name})
    now = utcnow()
    old_values, old_from = _load(cached) if cached else ([], None)
    if cached:
        updated = cached["updated_at"]
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        fresh = now - updated < timedelta(hours=CACHE_HOURS)
        if fresh and old_from is not None and old_from <= need_from:
            return Series(old_values, old_from)
    try:
        values = fetch_range(name, need_from, today)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        if old_values:
            return Series(old_values, old_from, stale=True)
        raise BcbUnavailable(name) from e
    merged = dict(v for v in old_values if v[0] < need_from)
    merged.update(values)
    covers_from = min(need_from, old_from) if old_from else need_from
    db.indicators.update_one(
        {"serie": name},
        {"$set": {"values": [(d.isoformat(), v) for d, v in sorted(merged.items())],
                  "covers_from": covers_from.isoformat(), "updated_at": now}},
        upsert=True,
    )
    return Series(sorted(merged.items()), covers_from)


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
    since = today - timedelta(days=400)
    cdi_s = get_series(db, "cdi", since=since, today=today)
    ipca_s = get_series(db, "ipca", since=since, today=today)
    cdi, ipca = cdi_s.values, ipca_s.values
    end = cdi[-1][0] if cdi else today
    start = end - timedelta(days=365)
    return {
        "cdi_12m": round(accumulated(cdi, start, end) * 100, 2),
        "ipca_12m": round(accumulated_monthly(ipca, start, end) * 100, 2),
        "cdi_ultimo_dia": cdi[-1][0].isoformat() if cdi else None,
        "ipca_ultimo_mes": ipca[-1][0].isoformat() if ipca else None,
        "desatualizado": cdi_s.stale or ipca_s.stale,
        "fonte": "Banco Central do Brasil – SGS (séries 12 e 433)",
    }
