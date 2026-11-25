"""Esquemas de entrada e saída da API."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

AssetType = Literal["renda_fixa", "acao", "fii"]
Indexer = Literal["cdi", "ipca"]

# O bcrypt só considera os primeiros 72 BYTES da senha (o bcrypt 5 recusa o excedente com erro).
MAX_PASSWORD_BYTES = 72
MSG_SENHA_LONGA = (f"A senha pode ter no máximo {MAX_PASSWORD_BYTES} bytes: cerca de 72 letras sem acento. "
                   "Letras com acento ocupam 2 bytes e emojis, 4.")


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8)
    accept_terms: bool

    @field_validator("password")
    @classmethod
    def _password_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(MSG_SENHA_LONGA)
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str


class AssetIn(BaseModel):
    """Aplicação cadastrada pelo usuário (RF04 e RF05)."""

    type: AssetType
    name: str = Field(min_length=1, max_length=80, description="Ex.: RDC CrediAlta, PETR4, HGLG11")
    ticker: str | None = Field(default=None, max_length=12)
    invested: float = Field(gt=0, description="Valor aplicado (renda fixa) ou quantidade × preço médio")
    start_date: date
    # renda fixa
    indexer: Indexer | None = None
    rate: float | None = Field(default=None, description="% do CDI (ex.: 105) ou taxa anual do IPCA+ (ex.: 6.5)")
    maturity: date | None = None
    # renda variável
    quantity: float | None = Field(default=None, gt=0)
    avg_price: float | None = Field(default=None, gt=0)

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v

    @model_validator(mode="after")
    def _check(self) -> "AssetIn":
        if self.type == "renda_fixa":
            if self.indexer is None or self.rate is None:
                raise ValueError("Renda fixa precisa do indexador (CDI ou IPCA) e da taxa.")
            # FB05: usuários digitavam 1,05 querendo dizer 105% do CDI
            if self.indexer == "cdi" and 0 < self.rate < 3:
                self.rate = round(self.rate * 100, 4)
        else:
            if not self.ticker:
                raise ValueError("Ações e FIIs precisam do código de negociação (ex.: PETR4).")
            if self.quantity is None or self.avg_price is None:
                raise ValueError("Informe a quantidade e o preço médio.")
            self.invested = round(self.quantity * self.avg_price, 2)
        return self


class Asset(AssetIn):
    id: str
