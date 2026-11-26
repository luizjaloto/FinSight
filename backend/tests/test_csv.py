"""Testes da importação do CSV da B3 (T05)."""
from datetime import date

import pytest

from app.services.csv_import import parse_b3_csv, parse_number, usa_milhar_sem_virgula

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


@pytest.mark.parametrize("texto,esperado", [
    ("5.000", 5000), ("1.500", 1500), ("10.000", 10000), ("12.345.678", 12345678),
    ("5.000,00", 5000), ("0.5", 0.5), ("12.5", 12.5), ("1500", 1500), (" R$ 1.500 ", 1500),
])
def test_regra_unica_de_ponto_de_milhar(texto, esperado):
    """P0-1b: mesma regra do front-end (parseBR). '0.5' continua decimal (quantidade fracionária de FII)."""
    assert parse_number(texto) == esperado


def test_milhar_sem_virgula_e_identificado():
    assert usa_milhar_sem_virgula("5.000") and usa_milhar_sem_virgula("12.345.678")
    assert not usa_milhar_sem_virgula("5.000,00") and not usa_milhar_sem_virgula("0.5")


def test_importacao_lista_linhas_lidas_como_milhar():
    txt = "Código de Negociação;Quantidade;Preço de Fechamento\nPETR4;5.000;38,00\nHGLG11;0.5;160,00\nVALE3;10;61.300\n"
    r = parse_b3_csv(txt.encode(), HOJE)
    assert [a["quantity"] for a in r["assets"]] == [5000, 0.5, 10]
    assert [(m["line"], m["ticker"], m["campo"], m["texto"], m["valor"]) for m in r["milhar_sem_virgula"]] == [
        (2, "PETR4", "quantidade", "5.000", 5000), (4, "VALE3", "preço", "61.300", 61300)]


def test_tabela_de_casos_passa_pela_importacao():
    """P0-1c: os casos da tabela do plano valem também no CSV da B3, onde o erro aparecia."""
    casos = [("5.000", 5000), ("1.500", 1500), ("10.000", 10000), ("12.345.678", 12345678), ("5.000,00", 5000), ("0.5", 0.5)]
    linhas = ["Código de Negociação;Quantidade;Preço de Fechamento"] + [f"PETR4;{texto};1" for texto, _ in casos]
    r = parse_b3_csv(("\n".join(linhas) + "\n").encode(), HOJE)
    assert [a["quantity"] for a in r["assets"]] == [valor for _, valor in casos]
    assert [m["texto"] for m in r["milhar_sem_virgula"]] == ["5.000", "1.500", "10.000", "12.345.678"]


def test_endpoint_informa_linhas_lidas_como_milhar(client, auth):
    txt = "Código de Negociação;Quantidade;Preço de Fechamento\nPETR4;5.000;38,00\nHGLG11;0.5;160,00\n"
    r = client.post("/portfolio/import-csv", headers=auth, files={"file": ("p.csv", txt.encode(), "text/csv")})
    assert r.status_code == 200 and r.json()["imported"] == 2
    assert r.json()["conferir_milhar"] == [{"line": 2, "ticker": "PETR4", "campo": "quantidade", "texto": "5.000", "valor": 5000}]
    carteira = client.get("/portfolio", headers=auth).json()["assets"]
    assert next(a for a in carteira if a["ticker"] == "PETR4")["quantity"] == 5000
