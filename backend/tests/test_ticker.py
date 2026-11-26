"""P0-3 – código de negociação não validado não pode alterar a URL da API de cotações."""
import pytest
from pydantic import ValidationError

from app.models import AssetIn
from app.services import quotes


def _acao(ticker):
    return {"type": "acao", "name": "Teste", "ticker": ticker, "invested": 100, "quantity": 1, "avg_price": 100,
            "start_date": "2024-01-02"}


@pytest.mark.parametrize("ticker", ["PETR4/../x", "PETR4?x=1", "PETR4#x", "PETR", "PETR4X2Y"])
def test_asset_rejeita_ticker_fora_do_formato(ticker):
    with pytest.raises(ValidationError) as erro:
        AssetIn(**_acao(ticker))
    assert "Código de negociação inválido. Use o formato PETR4 ou HGLG11." in str(erro.value)


@pytest.mark.parametrize("ticker", ["PETR4", "HGLG11", "BBDC4", "petr4 "])
def test_asset_aceita_ticker_valido(ticker):
    assert AssetIn(**_acao(ticker)).ticker == ticker.strip().upper()


def test_ticker_so_e_exigido_em_acao_e_fii_nao_muda_renda_fixa():
    renda_fixa = {"type": "renda_fixa", "name": "CDB", "invested": 1000, "start_date": "2024-01-02",
                  "indexer": "cdi", "rate": 100}
    assert AssetIn(**renda_fixa).ticker is None
    with pytest.raises(ValidationError):
        AssetIn(**{**renda_fixa, "ticker": "PETR4"})  # renda fixa não usa código de negociação


def test_url_da_cotacao_escapa_barra_interrogacao_e_cerquilha(monkeypatch):
    chamadas = []

    def falso_get(url, **kwargs):
        chamadas.append(url)
        raise ConnectionError("sem rede no teste")

    monkeypatch.setattr(quotes.httpx, "get", falso_get)
    assert quotes.fetch_quote("PETR4/../x?token=y#z") is None
    assert chamadas == ["https://brapi.dev/api/quote/PETR4%2F..%2Fx%3Ftoken%3Dy%23z"]
