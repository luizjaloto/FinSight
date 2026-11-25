"""Painel, indicadores do Banco Central e glossário (RF07, RF08, RF09, RF10)."""
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from .. import clock
from ..config import settings
from ..db import get_db
from ..glossary import GLOSSARY
from ..security import current_user_id
from ..services import analytics, bcb
from ..services.quotes import get_quote

router = APIRouter(tags=["painel"])

AVISO = "O FinSight é uma ferramenta educativa. As informações não são recomendação de investimento."


@router.get("/indicadores")
def indicadores():
    try:
        return bcb.summary(get_db(), clock.today_br())
    except bcb.BcbUnavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível consultar o Banco Central agora.")


def _oldest_start(assets: list[dict], today: date) -> date:
    """Data da aplicação mais antiga: a série do BCB precisa cobrir desde ela (B3)."""
    datas = []
    for a in assets:
        try:
            datas.append(date.fromisoformat(str(a["start_date"])))
        except (KeyError, ValueError):
            continue  # ativo com data inválida vira 'erro de cálculo' no painel (B2)
    return min(datas + [today - timedelta(days=400)])


@router.get("/glossario")
def glossario():
    return [{"termo": t, "definicao": d} for t, d in GLOSSARY]


@router.get("/dashboard")
def dashboard(user_id: str = Depends(current_user_id)):
    db = get_db()
    assets = (db.portfolios.find_one({"user_id": user_id}) or {}).get("assets", [])
    today = clock.today_br()
    since = _oldest_start(assets, today)
    try:
        cdi_s = bcb.get_series(db, "cdi", since=since, today=today)
        ipca_s = bcb.get_series(db, "ipca", since=since, today=today)
    except bcb.BcbUnavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Indicadores do Banco Central indisponíveis no momento.")
    cdi, ipca = cdi_s.values, ipca_s.values

    prices, quotes = {}, {}
    for a in assets:
        tk = a.get("ticker")
        if a["type"] != "renda_fixa" and tk and tk not in quotes:
            quotes[tk] = get_quote(db, tk)
            prices[tk] = quotes[tk]["price"]

    data = analytics.build_dashboard(assets, cdi, ipca, prices, today,
                                     limit=settings.concentration_limit, days=settings.maturity_alert_days)
    stale = cdi_s.stale or ipca_s.stale
    data["indicadores_desatualizados"] = stale
    if stale:
        ultimo = cdi[-1][0].strftime("%d/%m/%Y") if cdi else "data desconhecida"
        data["alertas"].insert(0, {
            "kind": "indicadores",
            "level": "info",
            "title": "Não conseguimos atualizar o CDI e o IPCA agora",
            "text": f"Os cálculos usam os últimos dados salvos do Banco Central (até {ultimo}). Tente de novo mais tarde.",
            "why": "O CDI e o IPCA vêm do site do Banco Central. Quando ele não responde, usamos a cópia mais recente que temos.",
        })
    db.alerts.delete_many({"user_id": user_id})
    if data["alertas"]:
        now = datetime.now(UTC)
        db.alerts.insert_many([dict(a, user_id=user_id, created_at=now) for a in data["alertas"]])
    data["cotacoes"] = quotes
    data["aviso"] = AVISO
    return data
