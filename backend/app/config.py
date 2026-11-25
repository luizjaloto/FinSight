"""Configurações lidas de variáveis de ambiente (arquivo .env na raiz do back-end)."""
import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Carrega um arquivo .env simples (CHAVE=valor) sem dependências externas."""
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "finsight")
    jwt_secret: str = os.getenv("JWT_SECRET", "troque-esta-chave-em-producao")
    jwt_minutes: int = int(os.getenv("JWT_MINUTES", "60"))
    cors_origins: tuple = tuple(o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip())
    brapi_token: str = os.getenv("BRAPI_TOKEN", "")
    # Limiares das regras de negócio (documento 06_01 – RF09)
    concentration_limit: float = float(os.getenv("CONCENTRATION_LIMIT", "0.25"))
    maturity_alert_days: int = int(os.getenv("MATURITY_ALERT_DAYS", "30"))
    # Proxies cujo X-Forwarded-For é confiável (ex.: IP do nginx na rede do Docker). Vazio = cabeçalho ignorado (S2).
    trusted_proxies: tuple = tuple(p.strip() for p in os.getenv("TRUSTED_PROXIES", "").split(",") if p.strip())


settings = Settings()
