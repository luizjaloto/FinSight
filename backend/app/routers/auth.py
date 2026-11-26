"""Cadastro, login e exclusão de conta (RF01, RF02, RNF03)."""
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pymongo.errors import DuplicateKeyError

from ..config import settings
from ..db import get_db
from ..models import TERMOS_VERSAO, LoginIn, RegisterIn, TokenOut
from ..security import (
    PasswordTooLong,
    create_token,
    current_user_id,
    hash_password,
    verify_login,
)
from ..services import rate_limit

router = APIRouter(prefix="/auth", tags=["autenticação"])


def _too_many(e: rate_limit.RateLimited) -> HTTPException:
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                         f"Muitas tentativas. Tente de novo em {e.retry_after} segundos.",
                         headers={"Retry-After": str(e.retry_after)})


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request):
    db = get_db()
    ip_key = rate_limit.key("register:ip", rate_limit.client_ip(request, settings.trusted_proxies))
    email_key = rate_limit.key("register:email", body.email)
    try:
        rate_limit.ensure_allowed(db, [ip_key, email_key])
    except rate_limit.RateLimited as e:
        raise _too_many(e)
    rate_limit.hit(db, ip_key, rate_limit.REGISTER_IP)
    rate_limit.hit(db, email_key, rate_limit.REGISTER_EMAIL)
    if not body.accept_terms:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "É preciso aceitar o termo de privacidade para criar a conta.")
    try:
        password_hash = hash_password(body.password)
    except PasswordTooLong as e:  # o modelo já valida; aqui é defesa em profundidade
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    user: dict[str, Any] = {
        "_id": uuid.uuid4().hex,
        "name": body.name.strip(),
        "email": body.email.lower(),
        "password_hash": password_hash,
        "terms_accepted_at": datetime.now(UTC),
        "terms_version": TERMOS_VERSAO,
        "created_at": datetime.now(UTC),
    }
    try:
        db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.")
    db.portfolios.insert_one({"user_id": user["_id"], "assets": []})
    return TokenOut(access_token=create_token(user["_id"]), name=user["name"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request):
    db = get_db()
    ip_key = rate_limit.key("login:ip", rate_limit.client_ip(request, settings.trusted_proxies))
    email_key = rate_limit.key("login:email", body.email)
    try:
        rate_limit.ensure_allowed(db, [email_key, ip_key])
    except rate_limit.RateLimited as e:
        raise _too_many(e)
    user = db.users.find_one({"email": body.email.lower()})
    # mensagem genérica e tempo constante: não revela se o e-mail existe (RF02, S1)
    ok = verify_login(user, body.password)  # roda o bcrypt mesmo se o e-mail não existir
    if user is None or not ok:
        rate_limit.hit(db, email_key, rate_limit.LOGIN_EMAIL)
        rate_limit.hit(db, ip_key, rate_limit.LOGIN_IP)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    rate_limit.reset(db, email_key)
    return TokenOut(access_token=create_token(user["_id"]), name=user["name"])


def _user_or_401(db, user_id: str) -> dict[str, Any]:
    u = db.users.find_one({"_id": user_id}, {"password_hash": 0})
    if u is None:  # conta excluída entre a validação do token e esta leitura
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado.")
    return u


@router.get("/me")
def me(user_id: Annotated[str, Depends(current_user_id)]):
    u = _user_or_401(get_db(), user_id)
    return {"id": u["_id"], "name": u["name"], "email": u["email"]}


@router.get("/me/export")
def export_data(user_id: Annotated[str, Depends(current_user_id)]):
    """Exporta os dados do usuário (direito de acesso – LGPD)."""
    db = get_db()
    u = _user_or_401(db, user_id)
    p = db.portfolios.find_one({"user_id": user_id}, {"_id": 0})
    return {"usuario": {"nome": u["name"], "email": u["email"]}, "carteira": (p or {}).get("assets", [])}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user_id: Annotated[str, Depends(current_user_id)]):
    """Remove o usuário e TODOS os seus documentos (correção do teste T10: alertas incluídos)."""
    db = get_db()
    db.portfolios.delete_many({"user_id": user_id})
    db.alerts.delete_many({"user_id": user_id})
    db.users.delete_one({"_id": user_id})
