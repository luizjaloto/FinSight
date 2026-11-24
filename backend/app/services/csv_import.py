"""Importação da posição exportada da Área do Investidor da B3 (RF06).

Aceita CSV separado por ';' ou ',' e números no formato brasileiro (1.234,56).
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

TICKER_RE = re.compile(r"^[A-Z]{4}\d{1,2}[A-Z]?$")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def parse_number(raw: str) -> float:
    """'1.234,56' → 1234.56 ; '12,5' → 12.5 ; '0.5' → 0.5 (quantidade fracionária de FII – correção do T05)."""
    s = str(raw).strip().replace("R$", "").replace(" ", "")
    if not s or s == "-":
        raise ValueError("vazio")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def _find(cols: list[str], *keys: str) -> int | None:
    for k in keys:
        for i, c in enumerate(cols):
            if k in c:
                return i
    return None


def parse_b3_csv(content: bytes, today: date | None = None) -> dict:
    today = today or date.today()
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:2048]
    delim = ";" if sample.count(";") >= sample.count(",") else ","
    reader = list(csv.reader(io.StringIO(text), delimiter=delim))
    if not reader:
        return {"assets": [], "rejected": [{"line": 0, "reason": "Arquivo vazio."}]}

    header = [_norm(h) for h in reader[0]]
    i_tk = _find(header, "codigo de negociacao", "codigo", "ticker", "ativo")
    i_qt = _find(header, "quantidade")
    i_pr = _find(header, "preco de fechamento", "preco medio", "preco")
    i_nm = _find(header, "produto", "nome")
    if i_tk is None or i_qt is None or i_pr is None:
        return {"assets": [], "rejected": [{"line": 1, "reason": "Não encontrei as colunas de código, quantidade e preço."}]}

    assets, rejected = [], []
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
        kind = "fii" if ticker.endswith("11") else "acao"
        name = row[i_nm].strip() if i_nm is not None and i_nm < len(row) and row[i_nm].strip() else ticker
        assets.append({"type": kind, "name": name[:80], "ticker": ticker, "quantity": qty, "avg_price": price,
                       "invested": round(qty * price, 2), "start_date": today.isoformat()})
    return {"assets": assets, "rejected": rejected}
