"""Cria o usuário de demonstração com uma carteira simulada.

Uso (na pasta backend):  python -m scripts.seed_demo
Login: demo@finsight.app  /  senha: definida em DEMO_PASSWORD no .env.
Em desenvolvimento, sem DEMO_PASSWORD, usa Demo@2026. Em produção (ENV=production), DEMO_PASSWORD é obrigatória.
"""
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite: python scripts/seed_demo.py

from app.clock import today_br
from app.config import settings
from app.db import ensure_indexes, get_db
from app.security import hash_password

EMAIL = "demo@finsight.app"


def senha_da_demonstracao() -> str:
    senha = os.getenv("DEMO_PASSWORD", "")  # vazio conta como ausente: nunca criar a conta sem senha
    if senha:
        return senha
    if settings.env == "production":
        sys.exit("Defina DEMO_PASSWORD no .env antes de criar a conta de demonstração em produção.")
    return "Demo@2026"  # padrão só para desenvolvimento local


def main() -> None:
    senha = senha_da_demonstracao()
    db = get_db()
    ensure_indexes(db)
    old = db.users.find_one({"email": EMAIL})
    if old:
        db.portfolios.delete_many({"user_id": old["_id"]})
        db.alerts.delete_many({"user_id": old["_id"]})
        db.users.delete_one({"_id": old["_id"]})
    uid = uuid.uuid4().hex
    db.users.insert_one({"_id": uid, "name": "Roberto (demonstração)", "email": EMAIL,
                         "password_hash": hash_password(senha),
                         "terms_accepted_at": datetime.now(UTC), "created_at": datetime.now(UTC)})
    today = today_br()
    d = lambda days: (today - timedelta(days=days)).isoformat()
    assets = [
        {"type": "renda_fixa", "name": "RDC CrediAlta", "invested": 15000, "start_date": d(330), "indexer": "cdi", "rate": 105,
         "maturity": (today + timedelta(days=20)).isoformat()},
        {"type": "renda_fixa", "name": "LCA CrediAlta", "invested": 8000, "start_date": d(300), "indexer": "cdi", "rate": 92},
        {"type": "renda_fixa", "name": "Tesouro IPCA+ 2029", "invested": 5000, "start_date": d(250), "indexer": "ipca", "rate": 6.2},
        {"type": "acao", "name": "Petrobras PN", "ticker": "PETR4", "quantity": 900, "avg_price": 36.5, "invested": 32850, "start_date": d(200)},
        {"type": "acao", "name": "Itaú Unibanco PN", "ticker": "ITUB4", "quantity": 100, "avg_price": 32.0, "invested": 3200, "start_date": d(150)},
    ]
    for a in assets:
        a["id"] = uuid.uuid4().hex[:12]
    db.portfolios.insert_one({"user_id": uid, "assets": assets})
    print(f"Usuário de demonstração criado: {EMAIL}")


if __name__ == "__main__":
    main()
