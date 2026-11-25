"""Cadastro, login e exclusão de conta (RF01, RF02, RNF03)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from ..db import get_db
from ..models import LoginIn, RegisterIn, TokenOut
from ..security import PasswordTooLong, create_token, current_user_id, hash_password, verify_login

router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn):
    if not body.accept_terms:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "É preciso aceitar o termo de privacidade para criar a conta.")
    db = get_db()
    try:
        password_hash = hash_password(body.password)
    except PasswordTooLong as e:  # o modelo já valida; aqui é defesa em profundidade
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    user = {
        "_id": uuid.uuid4().hex,
        "name": body.name.strip(),
        "email": body.email.lower(),
        "password_hash": password_hash,
        "terms_accepted_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    try:
        db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.")
    db.portfolios.insert_one({"user_id": user["_id"], "assets": []})
    return TokenOut(access_token=create_token(user["_id"]), name=user["name"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn):
    user = get_db().users.find_one({"email": body.email.lower()})
    # mensagem genérica e tempo constante: não revela se o e-mail existe (RF02, S1)
    ok = verify_login(user, body.password)  # roda o bcrypt mesmo se o e-mail não existir
    if user is None or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    return TokenOut(access_token=create_token(user["_id"]), name=user["name"])


@router.get("/me")
def me(user_id: str = Depends(current_user_id)):
    u = get_db().users.find_one({"_id": user_id}, {"password_hash": 0})
    return {"id": u["_id"], "name": u["name"], "email": u["email"]}


@router.get("/me/export")
def export_data(user_id: str = Depends(current_user_id)):
    """Exporta os dados do usuário (direito de acesso – LGPD)."""
    db = get_db()
    u = db.users.find_one({"_id": user_id}, {"password_hash": 0})
    p = db.portfolios.find_one({"user_id": user_id}, {"_id": 0})
    return {"usuario": {"nome": u["name"], "email": u["email"]}, "carteira": (p or {}).get("assets", [])}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user_id: str = Depends(current_user_id)):
    """Remove o usuário e TODOS os seus documentos (correção do teste T10: alertas incluídos)."""
    db = get_db()
    db.portfolios.delete_many({"user_id": user_id})
    db.alerts.delete_many({"user_id": user_id})
    db.users.delete_one({"_id": user_id})
