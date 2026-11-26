"""P1-8 – em produção, a documentação da API fica desligada e o seed da conta de demonstração exige senha."""
import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def _roda(args: list[str], **ambiente: str) -> subprocess.CompletedProcess:
    """Roda um processo novo: a configuração é lida na importação, então cada cenário precisa do seu."""
    env = {k: v for k, v in os.environ.items() if k not in ("ENV", "DEMO_PASSWORD")}
    env.update({"MONGO_URI": "mongomock://", "JWT_SECRET": "segredo-de-teste-com-mais-de-32-caracteres", **ambiente})
    return subprocess.run([sys.executable, *args], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)


CODIGO_APP = """
import json
from fastapi.middleware.cors import CORSMiddleware
from app.main import app
cors = [m for m in app.user_middleware if m.cls is CORSMiddleware][0]
opcoes = getattr(cors, "kwargs", None) or cors.options
print(json.dumps({"docs": app.docs_url, "redoc": app.redoc_url, "openapi": app.openapi_url,
                  "metodos": sorted(opcoes["allow_methods"]), "cabecalhos": sorted(opcoes["allow_headers"])}))
"""


def test_producao_desliga_documentacao_e_restringe_cors():
    r = _roda(["-c", CODIGO_APP], ENV="production")
    assert r.returncode == 0, r.stderr
    dados = json.loads(r.stdout.strip().splitlines()[-1])
    assert dados["docs"] is None and dados["redoc"] is None and dados["openapi"] is None
    assert dados["metodos"] == ["DELETE", "GET", "POST"]
    assert dados["cabecalhos"] == ["Authorization", "Content-Type"]


def test_desenvolvimento_mantem_documentacao_e_cors_aberto():
    r = _roda(["-c", CODIGO_APP], ENV="development")
    assert r.returncode == 0, r.stderr
    dados = json.loads(r.stdout.strip().splitlines()[-1])
    assert dados["docs"] == "/docs" and dados["openapi"] == "/openapi.json"
    assert dados["metodos"] == ["*"] and dados["cabecalhos"] == ["*"]


SEED = [str(BACKEND / "scripts" / "seed_demo.py")]


def test_seed_se_recusa_em_producao_sem_demo_password():
    r = _roda(SEED, ENV="production", DEMO_PASSWORD="")
    assert r.returncode != 0
    assert "Defina DEMO_PASSWORD no .env" in r.stderr
    assert "Usuário de demonstração criado" not in r.stdout


def test_seed_em_producao_com_demo_password_cria_a_conta():
    r = _roda(SEED, ENV="production", DEMO_PASSWORD="senha-da-demo-2026")
    assert r.returncode == 0, r.stderr
    assert "Usuário de demonstração criado" in r.stdout


def test_seed_em_desenvolvimento_usa_o_padrao_sem_demo_password():
    r = _roda(SEED, ENV="development")
    assert r.returncode == 0, r.stderr
    assert "Usuário de demonstração criado" in r.stdout
