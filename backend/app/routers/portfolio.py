"""Carteira do usuário: cadastro manual e importação do CSV da B3 (RF04, RF05, RF06)."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from .. import clock
from ..db import get_db
from ..models import AssetIn
from ..security import current_user_id
from ..services.csv_import import parse_b3_csv

router = APIRouter(prefix="/portfolio", tags=["carteira"])
MAX_ASSETS = 50


def _assets(db, user_id: str) -> list[dict]:
    p = db.portfolios.find_one({"user_id": user_id}) or {}
    return p.get("assets", [])


def _to_doc(asset: AssetIn) -> dict:
    d = asset.model_dump(mode="json")
    d["id"] = uuid.uuid4().hex[:12]
    return d


@router.get("")
def list_assets(user_id: str = Depends(current_user_id)):
    return {"assets": _assets(get_db(), user_id)}


@router.post("/assets", status_code=status.HTTP_201_CREATED)
def add_asset(body: AssetIn, user_id: str = Depends(current_user_id)):
    db = get_db()
    if len(_assets(db, user_id)) >= MAX_ASSETS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Limite de {MAX_ASSETS} aplicações atingido.")
    doc = _to_doc(body)
    db.portfolios.update_one({"user_id": user_id}, {"$push": {"assets": doc}}, upsert=True)
    return doc


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_asset(asset_id: str, user_id: str = Depends(current_user_id)):
    res = get_db().portfolios.update_one({"user_id": user_id}, {"$pull": {"assets": {"id": asset_id}}})
    if res.modified_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aplicação não encontrada.")


@router.post("/import-csv")
async def import_csv(file: Annotated[UploadFile, File()], user_id: Annotated[str, Depends(current_user_id)]):
    content = await file.read()
    if len(content) > 1_000_000:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo muito grande (máximo 1 MB).")
    result = parse_b3_csv(content, clock.today_br())
    db = get_db()
    # P3-c: um ticker que já está na carteira não é importado de novo nem altera a aplicação existente.
    # Assim, importar o mesmo arquivo duas vezes não duplica nada. Para atualizar uma posição, remova-a e importe de novo.
    atuais = _assets(db, user_id)
    existentes = {a.get("ticker") for a in atuais}
    ja_na_carteira = [a["ticker"] for a in result["assets"] if a["ticker"] in existentes]
    docs = []
    for a in result["assets"]:
        if a["ticker"] in existentes:
            continue
        try:
            docs.append(_to_doc(AssetIn(**a)))
        except ValueError as e:
            result["rejected"].append({"line": None, "reason": f"{a.get('ticker')}: {e}"})
    if len(atuais) + len(docs) > MAX_ASSETS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"A importação passaria do limite de {MAX_ASSETS} aplicações.")
    if docs:
        db.portfolios.update_one({"user_id": user_id}, {"$push": {"assets": {"$each": docs}}}, upsert=True)
    total = len(docs) + len(result["rejected"])
    importados = {d["ticker"] for d in docs}
    # linhas em que 'ponto de milhar' foi lido como milhar (5.000 → 5000): o usuário confere se era isso mesmo
    conferir = [m for m in result["milhar_sem_virgula"] if m["ticker"] in importados]
    return {"imported": len(docs), "rejected": result["rejected"], "rate_pct": round(len(docs) / total * 100, 1) if total else 0,
            "conferir_milhar": conferir, "ja_na_carteira": ja_na_carteira}
