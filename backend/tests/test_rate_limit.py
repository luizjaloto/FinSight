"""S2 – limite de tentativas em /auth/login e /auth/register, por e-mail e por IP."""
from datetime import UTC, datetime, timedelta

import pytest

from app import clock

EMAIL = "teste@finsight.app"


@pytest.fixture
def relogio(monkeypatch):
    """Relógio controlável: começa num instante fixo e avança quando o teste pede."""
    estado = {"agora": datetime(2026, 11, 24, 15, 0, tzinfo=UTC)}
    monkeypatch.setattr(clock, "_now", lambda: estado["agora"])

    def avancar(segundos):
        estado["agora"] += timedelta(seconds=segundos)

    return avancar


def _login(client, email=EMAIL, senha="senha-errada-123", **headers):
    return client.post("/auth/login", json={"email": email, "password": senha}, headers=headers)


def test_sexta_tentativa_errada_em_1_minuto_da_429(client, auth, relogio):
    for _ in range(5):
        assert _login(client).status_code == 401
    r = _login(client)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    assert "tentativas" in r.json()["detail"]


def test_bloqueado_nem_a_senha_certa_entra(client, auth, relogio):
    for _ in range(5):
        _login(client)
    assert _login(client, senha="senha-forte-1").status_code == 429


def test_bloqueio_acaba_e_o_seguinte_e_mais_longo(client, auth, relogio):
    for _ in range(5):
        _login(client)
    primeiro = int(_login(client).headers["Retry-After"])
    relogio(primeiro + 1)
    assert _login(client, senha="senha-forte-1").status_code == 200  # liberado e o acerto zera o contador do e-mail
    for _ in range(5):
        assert _login(client).status_code == 401
    segundo = int(_login(client).headers["Retry-After"])
    assert segundo > primeiro  # atraso progressivo


def test_x_forwarded_for_forjado_nao_cria_novo_limite(client, relogio):
    """Sem proxy confiável configurado, o cabeçalho é ignorado: trocar o IP falso não zera o limite por IP."""
    ultimos = []
    for i in range(21):
        r = _login(client, email=f"pessoa{i}@finsight.app", **{"X-Forwarded-For": f"10.0.0.{i}"})
        ultimos.append(r.status_code)
    assert ultimos[:20] == [401] * 20
    assert ultimos[20] == 429


def test_cadastro_tambem_tem_limite(client, relogio):
    codigos = [client.post("/auth/register", json={"name": "Spam", "email": f"spam{i}@finsight.app", "password": "senha-forte-1",
                                                   "accept_terms": True}).status_code for i in range(6)]
    assert codigos[:5] == [201] * 5 and codigos[5] == 429


def test_ip_do_cliente_so_usa_x_forwarded_for_atras_de_proxy_confiavel():
    from types import SimpleNamespace

    from app.services.rate_limit import client_ip

    def req(host, xff=None):
        return SimpleNamespace(client=SimpleNamespace(host=host), headers={"x-forwarded-for": xff} if xff else {})

    assert client_ip(req("203.0.113.9", "1.2.3.4"), trusted=()) == "203.0.113.9"
    assert client_ip(req("172.18.0.5", "1.2.3.4"), trusted=("172.18.0.5",)) == "1.2.3.4"
    # o cliente pode inventar entradas à esquerda; vale o primeiro IP não confiável a partir da direita
    assert client_ip(req("172.18.0.5", "6.6.6.6, 1.2.3.4"), trusted=("172.18.0.5",)) == "1.2.3.4"


def test_rate_limit_nao_guarda_email_nem_ip_em_texto(client, auth, relogio):
    from app.db import get_db

    _login(client)
    chaves = [d["_id"] for d in get_db().rate_limits.find()]
    assert chaves and not any(EMAIL in k or "testclient" in k for k in chaves)
