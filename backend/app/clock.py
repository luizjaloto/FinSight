"""Relógio único do sistema (B9).

As regras de negócio usam sempre a data de Brasília. O servidor pode estar em UTC: às 22:54 de Brasília
já é o dia seguinte em UTC, e usar date.today() ali aceitaria aplicações "de amanhã" ou erraria o cálculo.
Os serviços recebem a data por parâmetro; só as bordas (rotas, scripts e validação de entrada) chamam today_br().
"""
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

TZ_BR = ZoneInfo("America/Sao_Paulo")


def _now() -> datetime:
    """Instante atual em UTC (substituído nos testes para fixar o relógio)."""
    return datetime.now(UTC)


def now_br() -> datetime:
    return _now().astimezone(TZ_BR)


def today_br() -> date:
    return now_br().date()
