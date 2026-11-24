"""Aplicação FastAPI do FinSight."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .db import ensure_indexes, get_db
from .routers import auth, dashboard, portfolio


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes(get_db())
    yield


app = FastAPI(
    title="FinSight API",
    version=__version__,
    description="Painel inteligente de carteira e educação financeira para pequenos investidores – Equipe 04, PI III, Fatec Pompeia.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(portfolio.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["status"])
def health():
    return {"status": "ok", "version": __version__}
