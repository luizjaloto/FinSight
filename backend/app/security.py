"""Senhas com bcrypt e autenticação com JWT (RNF02)."""
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import clock
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
    now = datetime.now(UTC)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=settings.jwt_minutes),
               "iss": settings.jwt_issuer, "aud": settings.jwt_audience}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decodifica(token: str) -> dict:
    try:
        # S3: exp, iat, sub, iss e aud são obrigatórios; sem eles o token seria eterno ou de outro sistema
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"],
                          audience=settings.jwt_audience, issuer=settings.jwt_issuer,
                          options={"require": ["exp", "iat", "sub", "iss", "aud"]})
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Faça login novamente.")


def current_user_id(creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar.")
    payload = _decodifica(creds.credentials)
    user_id = payload.get("sub")
    if not user_id or get_db().users.find_one({"_id": user_id}, {"_id": 1}) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado.")
    return user_id


# P3-e: excluir a conta e baixar os dados pedem um login feito há pouco tempo.
MINUTOS_LOGIN_RECENTE = 5


def current_user_id_recente(creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
                            user_id: Annotated[str, Depends(current_user_id)]) -> str:
    """Como current_user_id, mas só aceita token emitido nos últimos 5 min.

    Uma sessão deixada aberta por horas, ou um token copiado, não basta para apagar a conta nem para baixar
    os dados. O usuário entra de novo e confirma a ação.
    """
    if creds is None:  # current_user_id já recusou a requisição; esta checagem só ajuda o tipo
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar.")
    emitido = datetime.fromtimestamp(_decodifica(creds.credentials)["iat"], UTC)
    if clock._now() - emitido > timedelta(minutes=MINUTOS_LOGIN_RECENTE):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Por segurança, entre de novo para confirmar esta ação.")
    return user_id
