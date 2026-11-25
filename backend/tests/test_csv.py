"""Testes da importação do CSV da B3 (T05)."""
from datetime import date

from app.services.csv_import import parse_b3_csv, parse_number

HOJE = date(2026, 11, 24)

CSV_B3 = """Produto;Instituição;Conta;Código de Negociação;Quantidade;Preço de Fechamento;Valor Atualizado
PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS;CORRETORA X;123;PETR4;100;38,12;3.812,00
ITUB4 - ITAU UNIBANCO HOLDING S.A.;CORRETORA X;123;ITUB4;50;32,40;1.620,00
HGLG11 - CSHG LOGISTICA FII;CORRETORA X;123;HGLG11;0,5;160,00;80,00
VALE3 - VALE S.A.;CORRETORA X;123;VALE3;10;61,30;613,00
;;;;;;
INVALIDO;CORRETORA X;123;XYZ;10;1,00;10,00
"""


def test_numeros_formato_brasileiro():
    assert parse_number("1.234,56") == 1234.56
    assert parse_number("0,5") == 0.5
    assert parse_number("R$ 38,12") == 38.12


def test_importa_linhas_validas_e_aponta_recusadas():
    r = parse_b3_csv(CSV_B3.encode("utf-8"), HOJE)
    tickers = [a["ticker"] for a in r["assets"]]
    assert tickers == ["PETR4", "ITUB4", "HGLG11", "VALE3"]
    assert len(r["rejected"]) == 1 and "XYZ" in r["rejected"][0]["reason"]


def test_quantidade_fracionaria_de_fii():
    """Falha original do T05 (21/11): FII com quantidade fracionária era recusado."""
    fii = next(a for a in parse_b3_csv(CSV_B3.encode("utf-8"), HOJE)["assets"] if a["ticker"] == "HGLG11")
    assert fii["type"] == "fii" and fii["quantity"] == 0.5 and fii["invested"] == 80.0


def test_csv_com_virgula_como_separador():
    txt = "ticker,quantidade,preco\nPETR4,10,38.5\n"
    r = parse_b3_csv(txt.encode(), HOJE)
    assert r["assets"][0]["quantity"] == 10 and r["assets"][0]["avg_price"] == 38.5


def test_colunas_ausentes():
    r = parse_b3_csv(b"nome;valor\nA;1\n", HOJE)
    assert r["assets"] == [] and "colunas" in r["rejected"][0]["reason"]
