"""Conexão com o MongoDB (Atlas em produção; mongomock nos testes)."""
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from .config import settings


@lru_cache
def _client() -> MongoClient:
    if settings.mongo_uri.startswith("mongomock://"):
        import mongomock  # usado apenas em testes e demonstrações locais

        return mongomock.MongoClient()
    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)


def get_db() -> Database:
    db = _client()[settings.mongo_db]
    return db


def ensure_indexes(db: Database) -> None:
    db.users.create_index("email", unique=True)
    db.portfolios.create_index("user_id", unique=True)
    db.alerts.create_index("user_id")
    db.quotes_cache.create_index("ticker", unique=True)
    db.indicators.create_index("serie", unique=True)
