"""S3 – segredo JWT forte em produção e tokens sempre com exp, iat, sub, iss e aud."""
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest

BACKEND = Path(__file__).resolve().parent.parent
SEGREDO_FORTE = "k" * 16 + "Xy9-forte-de-verdade-0123456789"  # 47 caracteres


def _settings(**env):
    from app.config import Settings

    return Settings(_env_file=None, **env)


@pytest.mark.parametrize("segredo", ["troque-esta-chave-em-producao", "curta-demais",
                                     "troque-por-um-texto-longo-e-aleatorio-com-32-caracteres"])
def test_producao_recusa_segredo_fraco_ou_de_exemplo(segredo):
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(env="production", jwt_secret=segredo)


def test_producao_aceita_segredo_forte_e_desenvolvimento_aceita_o_padrao():
    assert _settings(env="production", jwt_secret=SEGREDO_FORTE).env == "production"
    assert _settings(env="development").env == "development"


def test_app_nao_sobe_em_producao_com_segredo_fraco():
    env = {**os.environ, "ENV": "production", "JWT_SECRET": "fraco", "MONGO_URI": "mongomock://"}
    r = subprocess.run([sys.executable, "-c", "import app.main"], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert r.returncode != 0 and "JWT_SECRET" in r.stderr


def _uid(client, auth):
    return client.get("/auth/me", headers=auth).json()["id"]


def _token(payload):
    from app.config import settings

    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _base(uid):
    from app.config import settings

    agora = datetime.now(timezone.utc)
    return {"sub": uid, "iat": agora, "exp": agora + timedelta(minutes=5),
            "iss": settings.jwt_issuer, "aud": settings.jwt_audience}


def test_token_emitido_tem_iss_aud_exp(client, auth):
    from app.config import settings

    claims = jwt.decode(auth["Authorization"].split()[1], settings.jwt_secret, algorithms=["HS256"],
                        audience=settings.jwt_audience, issuer=settings.jwt_issuer)
    assert {"sub", "iat", "exp", "iss", "aud"} <= claims.keys()


@pytest.mark.parametrize("remover", ["exp", "iat", "sub", "iss", "aud"])
def test_token_sem_claim_obrigatoria_da_401(client, auth, remover):
    payload = _base(_uid(client, auth))
    payload.pop(remover)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {_token(payload)}"})
    assert r.status_code == 401


@pytest.mark.parametrize("campo,valor", [("aud", "outro-sistema"), ("iss", "outro-emissor")])
def test_token_de_outro_emissor_ou_publico_da_401(client, auth, campo, valor):
    payload = {**_base(_uid(client, auth)), campo: valor}
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {_token(payload)}"}).status_code == 401


def test_docker_compose_exige_jwt_secret_sem_valor_padrao():
    compose = (BACKEND.parent / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${JWT_SECRET:?" in compose
    assert "JWT_SECRET:-" not in compose
