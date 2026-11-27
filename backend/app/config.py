"""Configurações lidas de variáveis de ambiente e do arquivo backend/.env, validadas na subida (S3).

Com ENV=production a aplicação não sobe se JWT_SECRET for o valor padrão, um valor de exemplo da documentação
ou tiver menos de 32 caracteres.
"""
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Falso positivo B105: valor padrão usado só em dev/testes; recusado em produção por _strong_secret_in_production.
DEFAULT_JWT_SECRET = "troque-esta-chave-em-producao"  # nosec B105
# Valores que já apareceram em arquivos de exemplo: nunca podem ser usados em produção
EXAMPLE_JWT_SECRETS = {DEFAULT_JWT_SECRET, "troque-por-um-texto-longo-e-aleatorio-com-32-caracteres"}
MIN_JWT_SECRET_LEN = 32

CommaList = Annotated[tuple[str, ...], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent.parent / ".env",
                                      env_file_encoding="utf-8", extra="ignore", frozen=True)

    env: Literal["development", "production"] = "development"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "finsight"
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_minutes: int = Field(default=60, gt=0, le=24 * 60)
    jwt_issuer: str = "finsight-api"
    jwt_audience: str = "finsight-web"
    cors_origins: CommaList = ("http://localhost:5173",)
    brapi_token: str = ""
    # Limiares das regras de negócio (documento 06_01 – RF09)
    concentration_limit: float = 0.25
    maturity_alert_days: int = 30
    # Proxies cujo X-Forwarded-For é confiável (ex.: IP do nginx na rede do Docker). Vazio = cabeçalho ignorado (S2).
    trusted_proxies: CommaList = ()

    @field_validator("cors_origins", "trusted_proxies", mode="before")
    @classmethod
    def _split_commas(cls, v):
        if isinstance(v, str):
            return tuple(p.strip() for p in v.split(",") if p.strip())
        return v

    @model_validator(mode="after")
    def _strong_secret_in_production(self) -> "Settings":
        if self.env == "production" and (self.jwt_secret in EXAMPLE_JWT_SECRETS or len(self.jwt_secret) < MIN_JWT_SECRET_LEN):
            raise ValueError(f"JWT_SECRET inseguro para produção: use um texto aleatório com pelo menos {MIN_JWT_SECRET_LEN} "
                             "caracteres (ex.: python -c \"import secrets; print(secrets.token_urlsafe(48))\").")
        return self


settings = Settings()
