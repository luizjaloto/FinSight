"""Limite de tentativas no login e no cadastro (S2).

Contadores no MongoDB (coleção rate_limits, com índice TTL para limpeza). Cada chave tem uma janela de tempo;
ao estourar o limite, a chave fica bloqueada e o bloqueio dobra a cada nova rodada (atraso progressivo).

LGPD: as chaves guardam um hash do e-mail e do IP, nunca o valor em texto.
"""
import hashlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .. import clock


@dataclass(frozen=True)
class Policy:
    limit: int            # tentativas permitidas na janela
    window_s: int         # tamanho da janela, em segundos
    base_block_s: int     # primeiro bloqueio; dobra a cada novo estouro
    max_block_s: int      # teto do bloqueio


LOGIN_EMAIL = Policy(limit=5, window_s=60, base_block_s=60, max_block_s=15 * 60)
LOGIN_IP = Policy(limit=20, window_s=60, base_block_s=60, max_block_s=15 * 60)
REGISTER_IP = Policy(limit=5, window_s=60, base_block_s=60, max_block_s=60 * 60)
REGISTER_EMAIL = Policy(limit=5, window_s=60, base_block_s=60, max_block_s=60 * 60)
STRIKE_MEMORY = timedelta(hours=24)  # por quanto tempo lembrar dos estouros anteriores


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        super().__init__(retry_after)
        self.retry_after = retry_after


def key(scope: str, value: str) -> str:
    digest = hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:32]
    return f"{scope}:{digest}"


def client_ip(request, trusted: tuple = ()) -> str:
    """IP do cliente. O X-Forwarded-For só é usado se a conexão vier de um proxy confiável.

    Percorre a lista da direita para a esquerda e devolve o primeiro IP que não é de proxy confiável:
    entradas à esquerda podem ter sido inventadas pelo próprio cliente.
    """
    host = request.client.host if request.client else "desconhecido"
    xff = request.headers.get("x-forwarded-for")
    if not xff or host not in trusted:
        return host
    for ip in reversed([p.strip() for p in xff.split(",") if p.strip()]):
        if ip not in trusted:
            return ip
    return host


def _aware(dt: datetime) -> datetime:

    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def ensure_allowed(db, keys: list[str]) -> None:
    """Levanta RateLimited se alguma das chaves estiver bloqueada."""
    now = clock._now()
    for k in keys:
        doc = db.rate_limits.find_one({"_id": k}, {"blocked_until": 1})
        if doc and doc.get("blocked_until") and _aware(doc["blocked_until"]) > now:
            raise RateLimited(max(1, math.ceil((_aware(doc["blocked_until"]) - now).total_seconds())))


def hit(db, k: str, policy: Policy) -> None:
    """Registra uma tentativa (falha de login ou pedido de cadastro). Bloqueia a chave ao estourar o limite."""
    now = clock._now()
    doc = db.rate_limits.find_one({"_id": k}) or {}
    window_start = _aware(doc["window_start"]) if doc.get("window_start") else None
    if window_start is None or now - window_start >= timedelta(seconds=policy.window_s):
        count, window_start = 1, now
    else:
        count = doc.get("count", 0) + 1
    strikes = doc.get("strikes", 0)
    last_strike = _aware(doc["last_strike"]) if doc.get("last_strike") else None
    if last_strike and now - last_strike > STRIKE_MEMORY:
        strikes = 0
    update = {"count": count, "window_start": window_start, "strikes": strikes,
              "expires_at": now + STRIKE_MEMORY}
    if count >= policy.limit:
        strikes += 1
        block = min(policy.base_block_s * 2 ** (strikes - 1), policy.max_block_s)
        update.update(strikes=strikes, last_strike=now, blocked_until=now + timedelta(seconds=block),
                      count=0, window_start=now)
    db.rate_limits.update_one({"_id": k}, {"$set": update}, upsert=True)


def reset(db, k: str) -> None:
    """Login certo: zera o contador da janela, mas mantém a memória de bloqueios anteriores."""
    db.rate_limits.update_one({"_id": k}, {"$set": {"count": 0}, "$unset": {"blocked_until": ""}})
