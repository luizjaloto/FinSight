"""Painel, indicadores do Banco Central e glossário (RF07, RF08, RF09, RF10)."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

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
        return bcb.summary(get_db())
    except Exception:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível consultar o Banco Central agora.")


@router.get("/glossario")
def glossario():
    return [{"termo": t, "definicao": d} for t, d in GLOSSARY]


@router.get("/dashboard")
def dashboard(user_id: str = Depends(current_user_id)):
    db = get_db()
    assets = (db.portfolios.find_one({"user_id": user_id}) or {}).get("assets", [])
    try:
        cdi = bcb.get_series(db, "cdi")
        ipca = bcb.get_series(db, "ipca")
    except Exception:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Indicadores do Banco Central indisponíveis no momento.")

    prices, quotes = {}, {}
    for a in assets:
        tk = a.get("ticker")
        if a["type"] != "renda_fixa" and tk and tk not in quotes:
            quotes[tk] = get_quote(db, tk)
            prices[tk] = quotes[tk]["price"]

    data = analytics.build_dashboard(assets, cdi, ipca, prices, date.today(),
                                     limit=settings.concentration_limit, days=settings.maturity_alert_days)
    db.alerts.delete_many({"user_id": user_id})
    if data["alertas"]:
        now = datetime.now(timezone.utc)
        db.alerts.insert_many([dict(a, user_id=user_id, created_at=now) for a in data["alertas"]])
    data["cotacoes"] = quotes
    data["aviso"] = AVISO
    return data
