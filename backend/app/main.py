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


PRODUCAO = settings.env == "production"

app = FastAPI(
    title="FinSight API",
    version=__version__,
    description="Painel inteligente de carteira e educação financeira para pequenos investidores – Equipe 04, PI III, Fatec Pompeia.",
    lifespan=lifespan,
    # P1-8: em produção, a documentação interativa e o esquema da API não ficam expostos
    docs_url=None if PRODUCAO else "/docs",
    redoc_url=None if PRODUCAO else "/redoc",
    openapi_url=None if PRODUCAO else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    # em produção, só os métodos e cabeçalhos que a API e o front-end realmente usam
    allow_methods=["GET", "POST", "DELETE"] if PRODUCAO else ["*"],
    allow_headers=["Authorization", "Content-Type"] if PRODUCAO else ["*"],
)
app.include_router(auth.router)
app.include_router(portfolio.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["status"])
def health():
    return {"status": "ok", "version": __version__}
