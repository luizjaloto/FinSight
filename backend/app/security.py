"""Senhas com bcrypt e autenticação com JWT (RNF02)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .db import get_db
from .models import MAX_PASSWORD_BYTES, MSG_SENHA_LONGA

_bearer = HTTPBearer(auto_error=False)


class PasswordTooLong(ValueError):
    """Senha com mais bytes do que o bcrypt aceita (B1)."""


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise PasswordTooLong(MSG_SENHA_LONGA)
    try:
        return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")
    except ValueError as e:  # qualquer outra recusa do bcrypt vira erro de domínio, nunca 500
        raise PasswordTooLong(MSG_SENHA_LONGA) from e


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:  # senha longa demais ou hash inválido: tratado como senha incorreta
        return False


# Hash fictício com o mesmo custo dos hashes reais. Quando o e-mail não existe, a senha é verificada contra ele,
# para que a resposta demore o mesmo tempo e não revele quais e-mails têm conta (S1).
_DUMMY_HASH = bcrypt.hashpw(b"finsight-hash-ficticio-para-tempo-constante", bcrypt.gensalt()).decode("utf-8")


def verify_login(user: dict | None, password: str) -> bool:
    """Sempre executa exatamente uma verificação bcrypt, exista o usuário ou não."""
    ok = check_password(password, user["password_hash"] if user else _DUMMY_HASH)
    return user is not None and ok


def create_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=settings.jwt_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def current_user_id(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar.")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Faça login novamente.")
    user_id = payload.get("sub")
    if not user_id or get_db().users.find_one({"_id": user_id}, {"_id": 1}) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado.")
    return user_id
