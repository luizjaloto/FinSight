"""Esquemas de entrada e saída da API."""
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from . import clock

AssetType = Literal["renda_fixa", "acao", "fii"]
Indexer = Literal["cdi", "ipca"]

# Código de negociação de ação ou FII (ex.: PETR4, HGLG11). Usado também pelo importador da B3 e pela
# montagem da URL da API de cotações: nada fora desse formato pode chegar lá (P0-3).
TICKER_RE = re.compile(r"^[A-Z]{4}\d{1,2}[A-Z]?$")
MSG_TICKER_INVALIDO = "Código de negociação inválido. Use o formato PETR4 ou HGLG11."

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


# Tetos realistas para o público do projeto (pequenos investidores) – B2.
# Servem para barrar erros de digitação e valores que quebram o cálculo (overflow, número complexo).
MAX_INVESTED = 100_000_000.0      # R$ 100 milhões por aplicação
MAX_QUANTITY = 100_000_000.0      # cotas/ações por posição
MAX_PRICE = 1_000_000.0           # R$ por ação/cota
CDI_RATE_MAX = 500.0              # 0 < % do CDI <= 500
IPCA_RATE_MIN, IPCA_RATE_MAX = -10.0, 50.0   # taxa real anual do IPCA+


class AssetIn(BaseModel):
    """Aplicação cadastrada pelo usuário (RF04 e RF05)."""

    type: AssetType
    name: str = Field(min_length=1, max_length=80, description="Ex.: RDC CrediAlta, PETR4, HGLG11")
    ticker: str | None = Field(default=None, max_length=12)
    invested: float = Field(gt=0, le=MAX_INVESTED, allow_inf_nan=False,
                            description="Valor aplicado (renda fixa) ou quantidade × preço médio")
    start_date: date
    # renda fixa
    indexer: Indexer | None = None
    rate: float | None = Field(default=None, allow_inf_nan=False,
                               description="% do CDI (ex.: 105) ou taxa anual do IPCA+ (ex.: 6.5)")
    maturity: date | None = None
    # renda variável
    quantity: float | None = Field(default=None, gt=0, le=MAX_QUANTITY, allow_inf_nan=False)
    avg_price: float | None = Field(default=None, gt=0, le=MAX_PRICE, allow_inf_nan=False)

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v

    @model_validator(mode="after")
    def _check(self) -> "AssetIn":
        if self.start_date > clock.today_br():
            raise ValueError("A data da aplicação não pode ser no futuro.")
        if self.type == "renda_fixa":
            self._check_renda_fixa()
        else:
            self._check_renda_variavel()
        return self

    def _check_renda_fixa(self) -> None:
        sobrando = [c for c in ("ticker", "quantity", "avg_price") if getattr(self, c) is not None]
        if sobrando:
            raise ValueError("Renda fixa não usa código de negociação, quantidade nem preço médio.")
        if self.indexer is None or self.rate is None:
            raise ValueError("Renda fixa precisa do indexador (CDI ou IPCA) e da taxa.")
        if self.indexer == "cdi":
            # FB05: usuários digitavam 1,05 querendo dizer 105% do CDI
            if 0 < self.rate < 3:
                self.rate = round(self.rate * 100, 4)
            if not 0 < self.rate <= CDI_RATE_MAX:
                raise ValueError(f"O percentual do CDI deve ser maior que 0 e no máximo {CDI_RATE_MAX:.0f}%.")
        elif not IPCA_RATE_MIN <= self.rate <= IPCA_RATE_MAX:
            raise ValueError(f"A taxa do IPCA+ deve ficar entre {IPCA_RATE_MIN:.0f}% e {IPCA_RATE_MAX:.0f}% ao ano.")
        if self.maturity is not None and self.maturity < self.start_date:
            raise ValueError("O vencimento não pode ser antes da data da aplicação.")

    def _check_renda_variavel(self) -> None:
        if self.maturity is not None or self.indexer is not None or self.rate is not None:
            raise ValueError("Ações e FIIs não têm vencimento, indexador nem taxa.")
        if not self.ticker:
            raise ValueError("Ações e FIIs precisam do código de negociação (ex.: PETR4).")
        if not TICKER_RE.fullmatch(self.ticker):
            raise ValueError(MSG_TICKER_INVALIDO)
        if self.quantity is None or self.avg_price is None:
            raise ValueError("Informe a quantidade e o preço médio.")
        invested = round(self.quantity * self.avg_price, 2)
        if invested > MAX_INVESTED:
            raise ValueError("Quantidade × preço médio passa do limite de R$ 100 milhões por posição.")
        self.invested = invested


class Asset(AssetIn):
    id: str
