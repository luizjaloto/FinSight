"""Importação da posição exportada da Área do Investidor da B3 (RF06).

Aceita CSV separado por ';' ou ',' e números no formato brasileiro (1.234,56) ou com ponto de milhar sem
vírgula (5.000). Os valores lidos assim são listados na resposta para o usuário conferir.
Colunas reconhecidas (sem diferenciar maiúsculas e acentos):
  código de negociação / código / ticker
  quantidade
  preço de fechamento / preço médio / preço
  produto (opcional, usado como nome)
"""
import csv
import io
import re
import unicodedata
from datetime import date

from ..models import TICKER_RE

# Mesma regra do front-end (frontend/src/format.ts, parseBR). Sem vírgula, "5.000" é milhar, não decimal.
# [0-9] em vez de \d: o \d do Python aceita dígitos de outros alfabetos, o do JavaScript não.
MILHAR_SEM_VIRGULA = re.compile(r"[1-9][0-9]{0,2}(\.[0-9]{3})+")


def _limpa(raw) -> str:
    return re.sub(r"\s|R\$", "", str(raw).strip())


def usa_milhar_sem_virgula(raw) -> bool:
    """True quando o texto usa ponto de milhar sem vírgula decimal (ex.: '5.000', '12.345.678')."""
    s = _limpa(raw)
    return "," not in s and MILHAR_SEM_VIRGULA.fullmatch(s) is not None


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def parse_number(raw) -> float:
    """Regra única, igual à do front-end:
    1. com vírgula: ponto é milhar e vírgula é decimal ('1.234,56' → 1234.56, '5.000,00' → 5000);
    2. sem vírgula, no padrão de milhar: ponto é milhar ('5.000' → 5000, '12.345.678' → 12345678);
    3. senão: ponto é decimal ('0.5' → 0.5, quantidade fracionária de FII – correção do T05; '12.5' → 12.5).
    """
    s = _limpa(raw)
    if not s or s == "-":
        raise ValueError("vazio")
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    if MILHAR_SEM_VIRGULA.fullmatch(s):
        return float(s.replace(".", ""))
    return float(s)


def _find(cols: list[str], *keys: str) -> int | None:
    for k in keys:
        for i, c in enumerate(cols):
            if k in c:
                return i
    return None


def parse_b3_csv(content: bytes, today: date) -> dict:
    """`today` é a data de Brasília, injetada pela rota (B9)."""
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:2048]
    delim = ";" if sample.count(";") >= sample.count(",") else ","
    reader = list(csv.reader(io.StringIO(text), delimiter=delim))
    if not reader:
        return {"assets": [], "rejected": [{"line": 0, "reason": "Arquivo vazio."}], "milhar_sem_virgula": []}

    header = [_norm(h) for h in reader[0]]
    i_tk = _find(header, "codigo de negociacao", "codigo", "ticker", "ativo")
    i_qt = _find(header, "quantidade")
    i_pr = _find(header, "preco de fechamento", "preco medio", "preco")
    i_nm = _find(header, "produto", "nome")
    if i_tk is None or i_qt is None or i_pr is None:
        return {"assets": [], "rejected": [{"line": 1, "reason": "Não encontrei as colunas de código, quantidade e preço."}],
                "milhar_sem_virgula": []}

    assets, rejected, milhar = [], [], []
    for n, row in enumerate(reader[1:], start=2):
        if not any(c.strip() for c in row):
            continue
        try:
            ticker = row[i_tk].strip().upper()
            if not TICKER_RE.match(ticker):
                raise ValueError(f"código inválido: '{ticker}'")
            qty = parse_number(row[i_qt])
            price = parse_number(row[i_pr])
            if qty <= 0 or price <= 0:
                raise ValueError("quantidade e preço devem ser maiores que zero")
        except (ValueError, IndexError) as e:
            rejected.append({"line": n, "reason": str(e) if str(e) else "linha incompleta"})
            continue
        for campo, texto, valor in (("quantidade", row[i_qt], qty), ("preço", row[i_pr], price)):
            if usa_milhar_sem_virgula(texto):
                milhar.append({"line": n, "ticker": ticker, "campo": campo, "texto": texto.strip(), "valor": valor})
        kind = "fii" if ticker.endswith("11") else "acao"
        name = row[i_nm].strip() if i_nm is not None and i_nm < len(row) and row[i_nm].strip() else ticker
        assets.append({"type": kind, "name": name[:80], "ticker": ticker, "quantity": qty, "avg_price": price,
                       "invested": round(qty * price, 2), "start_date": today.isoformat()})
    return {"assets": _junta_repetidos(assets), "rejected": rejected, "milhar_sem_virgula": milhar}


def _junta_repetidos(assets: list[dict]) -> list[dict]:
    """Um ticker vira uma posição só. A B3 traz uma linha por conta/corretora: as quantidades se somam
    e o preço médio é ponderado pela quantidade. O nome e o tipo ficam os da primeira linha."""
    por_ticker: dict[str, dict] = {}
    for a in assets:
        atual = por_ticker.get(a["ticker"])
        if atual is None:
            por_ticker[a["ticker"]] = dict(a)
            continue
        custo = atual["quantity"] * atual["avg_price"] + a["quantity"] * a["avg_price"]
        atual["quantity"] += a["quantity"]
        atual["avg_price"] = round(custo / atual["quantity"], 6)
        atual["invested"] = round(atual["invested"] + a["invested"], 2)
    return list(por_ticker.values())

