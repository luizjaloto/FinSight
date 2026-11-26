"""Cálculos do painel: valor atual, rentabilidade vs. CDI/IPCA, alocação, diversificação e alertas (RF08, RF09).

A ferramenta é educativa: mede e explica, mas não recomenda compra ou venda (Resolução CVM nº 30).
"""
import math
from datetime import date

import pandas as pd

from . import bcb

CLASS_LABELS = {"renda_fixa": "Renda fixa", "acao": "Ações", "fii": "Fundos imobiliários"}


def _as_date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def value_asset(asset: dict, cdi: list, ipca: list, price: float | None, today: date) -> dict:
    """Valor atual de uma aplicação e os benchmarks (CDI e IPCA) no mesmo período.

    Renda fixa vencida para de render na data do vencimento (B4): o valor e a comparação com CDI/IPCA
    usam o período da aplicação até o vencimento.
    """
    start = _as_date(asset["start_date"])
    invested = float(asset["invested"])
    maturity = _as_date(asset["maturity"]) if asset.get("maturity") else None
    end = min(today, maturity) if maturity and asset["type"] == "renda_fixa" else today
    status = "vencido" if maturity and asset["type"] == "renda_fixa" and maturity < today else "ativo"
    cdi_period = bcb.accumulated(cdi, start, end)
    ipca_period = bcb.accumulated_monthly(ipca, start, end)
    quote_missing = False

    if asset["type"] == "renda_fixa":
        if asset.get("indexer") == "cdi":
            current = invested * (1 + bcb.accumulated(cdi, start, end, factor=float(asset["rate"]) / 100))
        else:  # IPCA + taxa prefixada ao ano
            years = max((end - start).days, 0) / 365
            current = invested * (1 + ipca_period) * (1 + float(asset["rate"]) / 100) ** years
    else:
        quote_missing = price is None
        current = float(asset["quantity"]) * (price if price is not None else float(asset["avg_price"]))

    return {
        "id": asset["id"],
        "name": asset["name"],
        "ticker": asset.get("ticker"),
        "type": asset["type"],
        "class_label": CLASS_LABELS[asset["type"]],
        "invested": round(invested, 2),
        "current": round(current, 2),
        "return_pct": round((current / invested - 1) * 100, 2),
        "cdi_period_pct": round(cdi_period * 100, 2),
        "ipca_period_pct": round(ipca_period * 100, 2),
        "maturity": asset.get("maturity"),
        "status": status,
        "quote_missing": quote_missing,
    }


def hhi(weights: list[float]) -> float:
    """Índice de Herfindahl-Hirschman: soma dos quadrados das participações (0 a 1)."""
    return float(sum(w * w for w in weights))


def diversification(weights: list[float]) -> dict:
    """Índice de 0 a 100 (100 = bem distribuído) exibido em faixas com texto (FB01)."""
    if not weights:
        return {"score": 0, "band": "sem dados", "text": "Cadastre aplicações para ver a diversificação."}
    score = round((1 - hhi(weights)) * 100)
    if score < 40:
        band, text = "baixa", "Boa parte do dinheiro está concentrada em poucos ativos. Se um deles cair, a carteira inteira sente."
    elif score < 70:
        band, text = "média", "A carteira tem alguma divisão, mas ainda depende bastante de poucos ativos."
    else:
        band, text = "boa", "O dinheiro está bem distribuído entre os ativos."
    return {"score": score, "band": band, "text": text}


def alerts(items: list[dict], total: float, today: date, limit: float, days: int) -> list[dict]:
    """Alertas em linguagem simples, sem recomendação de compra ou venda (FB02, FB06)."""
    out = []
    for it in items:
        w = it["current"] / total if total else 0
        if w > limit:
            label = it["ticker"] or it["name"]
            out.append({
                "kind": "concentracao",
                "level": "atencao",
                "title": f"{w * 100:.0f}% da sua carteira está em um único ativo ({label})",
                "text": "Quando muito dinheiro fica em um só lugar, uma queda nesse ativo afeta quase toda a carteira.",
                "why": "Diversificar é dividir o dinheiro entre ativos diferentes para que o resultado não dependa de um só. "
                       "Isto é uma informação educativa, não uma recomendação de venda.",
            })
        mat = it.get("maturity")
        if mat:
            mat_d = mat if isinstance(mat, date) else date.fromisoformat(mat)
            left = (mat_d - today).days
            if left < 0:
                out.append({
                    "kind": "vencido",
                    "level": "info",
                    "title": f"{it['name']} venceu em {mat_d.strftime('%d/%m/%Y')}",
                    "text": "Desde essa data, esta aplicação não rende mais nas condições combinadas. "
                            "O valor mostrado é o do dia do vencimento.",
                    "why": "Toda aplicação de renda fixa tem um prazo. No vencimento, o prazo termina e o rendimento "
                           "combinado deixa de ser calculado.",
                })
            elif left <= days:
                out.append({
                    "kind": "vencimento",
                    "level": "info",
                    "title": f"{it['name']} vence em {left} {'dia' if left == 1 else 'dias'} ({mat_d.strftime('%d/%m/%Y')})",
                    "text": "No vencimento, o valor volta para a sua conta. Converse com seu gerente se tiver dúvidas sobre o que fazer.",
                    "why": "Aplicações de renda fixa têm data de vencimento. Depois dela, o dinheiro deixa de render nas mesmas condições.",
                })
        if it.get("quote_missing"):
            out.append({
                "kind": "cotacao",
                "level": "info",
                "title": f"Cotação de {it['ticker']} indisponível no momento",
                "text": "Usamos o preço médio informado por você até a cotação voltar.",
                "why": "As cotações vêm de uma API pública com limite de consultas e até 15 minutos de atraso.",
            })
    return out


_NUMERIC = ("invested", "current", "return_pct", "cdi_period_pct", "ipca_period_pct")
# Falhas esperadas de um cálculo com dados ruins: overflow, divisão por zero, potência de base negativa,
# campo ausente ou de tipo errado, data inválida.
_CALC_ERRORS = (ArithmeticError, ValueError, TypeError, KeyError)


def _calc_error_item(asset: dict) -> dict:
    return {
        "id": asset.get("id"),
        "name": asset.get("name", "Aplicação"),
        "ticker": asset.get("ticker"),
        "type": asset.get("type"),
        "class_label": CLASS_LABELS.get(asset.get("type", ""), "Outros"),
        "calc_error": True,
        "invested": None, "current": None, "return_pct": None, "cdi_period_pct": None, "ipca_period_pct": None,
        "peso_pct": None, "maturity": asset.get("maturity"), "status": "erro", "quote_missing": False,
    }


def safe_value_asset(asset: dict, cdi: list, ipca: list, price: float | None, today: date) -> dict:
    """value_asset protegido: um ativo com dados inválidos vira 'erro de cálculo' em vez de derrubar o painel (B2)."""
    try:
        item = value_asset(asset, cdi, ipca, price, today)
    except _CALC_ERRORS:
        return _calc_error_item(asset)
    if not all(isinstance(item[k], (int, float)) and math.isfinite(item[k]) for k in _NUMERIC) or item["invested"] <= 0:
        return _calc_error_item(asset)
    item["calc_error"] = False
    return item


def build_dashboard(assets: list[dict], cdi: list, ipca: list, prices: dict, today: date, limit: float = 0.25, days: int = 30) -> dict:
    all_items = [safe_value_asset(a, cdi, ipca, prices.get(a.get("ticker")), today) for a in assets]
    items = [it for it in all_items if not it["calc_error"]]
    errors = [it for it in all_items if it["calc_error"]]
    error_alerts = [{
        "kind": "erro_calculo",
        "level": "atencao",
        "title": f"Não foi possível calcular: {it['ticker'] or it['name']}",
        "text": "Algum dado desta aplicação está fora do esperado. Ela ficou fora dos totais. Confira o cadastro.",
        "why": "Valores como taxa negativa demais ou valor aplicado gigantesco impedem um cálculo confiável.",
    } for it in errors]
    if not items:
        return {"patrimonio": 0, "investido": 0, "rentabilidade_pct": 0, "cdi_periodo_pct": 0, "ipca_periodo_pct": 0,
                "superou_cdi": None, "superou_ipca": None, "alocacao": [], "ativos": errors, "diversificacao": diversification([]),
                "alertas": error_alerts}

    df = pd.DataFrame(items)
    total = float(df["current"].sum())
    invested = float(df["invested"].sum())
    # benchmarks ponderados pelo valor aplicado em cada ativo, no mesmo período de cada aplicação
    cdi_w = float((df["invested"] * df["cdi_period_pct"]).sum() / invested)
    ipca_w = float((df["invested"] * df["ipca_period_pct"]).sum() / invested)
    ret = (total / invested - 1) * 100

    alloc = df.groupby("class_label")["current"].sum().sort_values(ascending=False)
    alocacao = [{"classe": k, "valor": round(float(v), 2), "pct": round(float(v) / total * 100, 1)} for k, v in alloc.items()]
    weights = (df["current"] / total).tolist()

    return {
        "patrimonio": round(total, 2),
        "investido": round(invested, 2),
        "rentabilidade_pct": round(ret, 2),
        "cdi_periodo_pct": round(cdi_w, 2),
        "ipca_periodo_pct": round(ipca_w, 2),
        "superou_cdi": ret > cdi_w,
        "superou_ipca": ret > ipca_w,
        "alocacao": alocacao,
        "ativos": [dict(it, peso_pct=round(it["current"] / total * 100, 1)) for it in items] + errors,
        "diversificacao": diversification(weights),
        "alertas": error_alerts + alerts(items, total, today, limit, days),
    }
