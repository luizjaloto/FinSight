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


def test_endpoint_informa_linhas_lidas_como_milhar(client, auth):
    txt = "Código de Negociação;Quantidade;Preço de Fechamento\nPETR4;5.000;38,00\nHGLG11;0.5;160,00\n"
    r = client.post("/portfolio/import-csv", headers=auth, files={"file": ("p.csv", txt.encode(), "text/csv")})
    assert r.status_code == 200 and r.json()["imported"] == 2
    assert r.json()["conferir_milhar"] == [{"line": 2, "ticker": "PETR4", "campo": "quantidade", "texto": "5.000", "valor": 5000}]
    carteira = client.get("/portfolio", headers=auth).json()["assets"]
    assert next(a for a in carteira if a["ticker"] == "PETR4")["quantity"] == 5000


def test_mesmo_ticker_em_duas_linhas_vira_uma_posicao():
    """P3-c: a B3 lista uma linha por conta; as quantidades se somam e o preço médio é ponderado."""
    txt = ("Código de Negociação;Quantidade;Preço de Fechamento;Instituição\n"
           "PETR4;100;38,00;CORRETORA A\nPETR4;50;38,00;CORRETORA B\nVALE3;10;61,30;CORRETORA A\n")
    r = parse_b3_csv(txt.encode(), HOJE)
    petr = next(a for a in r["assets"] if a["ticker"] == "PETR4")
    assert [a["ticker"] for a in r["assets"]] == ["PETR4", "VALE3"]
    assert petr["quantity"] == 150 and petr["avg_price"] == 38.0 and petr["invested"] == 5700.0


def test_reimportar_o_mesmo_arquivo_nao_duplica(client, auth):
    """P3-c: o segundo envio do mesmo arquivo não altera a carteira; os códigos já existentes são informados."""
    csv = "Código de Negociação;Quantidade;Preço de Fechamento\nPETR4;10;38,00\nHGLG11;0,5;160,00\n"
    envio = {"file": ("posicao.csv", csv.encode(), "text/csv")}
    primeiro = client.post("/portfolio/import-csv", headers=auth, files=envio).json()
    assert primeiro["imported"] == 2 and primeiro["ja_na_carteira"] == []

    segundo = client.post("/portfolio/import-csv", headers=auth, files=envio).json()
    assert segundo["imported"] == 0 and segundo["ja_na_carteira"] == ["PETR4", "HGLG11"]
    assert len(client.get("/portfolio", headers=auth).json()["assets"]) == 2


def test_importacao_nao_altera_aplicacao_ja_cadastrada_a_mao(client, auth):
    """P3-c: se o ticker já está na carteira (cadastrado à mão), a importação o deixa como está."""
    manual = {"type": "acao", "name": "Petrobras", "ticker": "PETR4", "quantity": 1, "avg_price": 30, "invested": 30,
              "start_date": "2026-01-10"}
    client.post("/portfolio/assets", headers=auth, json=manual)
    csv = "Código de Negociação;Quantidade;Preço de Fechamento\nPETR4;10;38,00\n"
    r = client.post("/portfolio/import-csv", headers=auth, files={"file": ("p.csv", csv.encode(), "text/csv")}).json()
    assert r["imported"] == 0 and r["ja_na_carteira"] == ["PETR4"]
    ativos = client.get("/portfolio", headers=auth).json()["assets"]
    assert len(ativos) == 1 and ativos[0]["quantity"] == 1 and ativos[0]["start_date"] == "2026-01-10"
