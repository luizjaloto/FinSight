"""S2 – limite de tentativas em /auth/login e /auth/register, por e-mail e por IP."""
import os
import threading
from datetime import UTC, datetime, timedelta

import pytest

from app import clock

EMAIL = "teste@finsight.app"


@pytest.fixture
def relogio(monkeypatch):
    """Relógio controlável: começa agora e avança quando o teste pede.

    Começa no relógio real de propósito: o índice TTL de rate_limits (expires_at) é avaliado pelo relógio real,
    então um instante fixo no passado apagaria o contador logo no primeiro acesso.
    """
    estado = {"agora": datetime.now(UTC).replace(microsecond=0)}
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


def test_quarta_tentativa_ainda_nao_bloqueia(client, auth, relogio):
    for _ in range(4):
        assert _login(client).status_code == 401
    assert _login(client, senha="senha-forte-1").status_code == 200  # ainda dentro do limite de 5


@pytest.fixture
def banco_limpo():
    """Zera os contadores: o mongomock é compartilhado entre testes, e um bloqueio antigo contaminaria o seguinte."""
    from app.db import get_db

    db = get_db()
    db.rate_limits.delete_many({})
    return db


def _em_paralelo(tentativa, quantidade: int) -> None:
    """Dispara as tentativas ao mesmo tempo: a barreira faz todas as threads partirem juntas."""
    barreira = threading.Barrier(quantidade)

    def corre():
        barreira.wait()
        tentativa()

    fios = [threading.Thread(target=corre) for _ in range(quantidade)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()


def test_trinta_tentativas_em_paralelo_bloqueiam_a_partir_da_quinta(relogio, banco_limpo):
    """P0-5: falhas simultâneas não se perdem. Com o antigo 'lê, soma e grava', o contador não avançava."""
    from app.services import rate_limit

    db = banco_limpo
    k = rate_limit.key("login:email", EMAIL)
    _em_paralelo(lambda: rate_limit.hit(db, k, rate_limit.LOGIN_EMAIL), 30)
    with pytest.raises(rate_limit.RateLimited):
        rate_limit.ensure_allowed(db, [k])
    assert db.rate_limits.find_one({"_id": k})["strikes"] >= 1


class _LeituraSincronizada:
    """Espera todas as threads terminarem de ler antes de liberar a primeira gravação.

    Isso força o pior intercalamento para 'ler, somar, gravar': todas leem o mesmo valor antes de qualquer escrita.
    """

    def __init__(self, colecao, barreira):
        self._colecao = colecao
        self._barreira = barreira

    def find_one(self, *args, **kwargs):
        documento = self._colecao.find_one(*args, **kwargs)
        self._barreira.wait()
        return documento

    def __getattr__(self, nome):
        return getattr(self._colecao, nome)


class _BancoComLeituraSincronizada:
    def __init__(self, db, barreira):
        self._db = db
        self.rate_limits = _LeituraSincronizada(db.rate_limits, barreira)

    def __getattr__(self, nome):
        return getattr(self._db, nome)


def test_bloqueio_nao_depende_de_ler_antes_de_gravar(relogio, banco_limpo):
    """Com o padrão 'lê, soma, grava', as 30 threads somariam sobre count=0 e nenhuma chegaria ao limite.

    Sem leitura prévia, o resultado não depende do intercalamento.
    """
    from app.services import rate_limit

    db = _BancoComLeituraSincronizada(banco_limpo, threading.Barrier(30, timeout=10))
    k = rate_limit.key("login:email", EMAIL)
    _em_paralelo(lambda: rate_limit.hit(db, k, rate_limit.LOGIN_EMAIL), 30)
    with pytest.raises(rate_limit.RateLimited):
        rate_limit.ensure_allowed(banco_limpo, [k])  # a verificação final não passa pela barreira


@pytest.mark.skipif(not os.getenv("MONGO_TEST_URI"),
                    reason="defina MONGO_TEST_URI para provar a atomicidade em um MongoDB de verdade")
def test_contador_atomico_em_mongodb_real(relogio):
    """Mesmo teste de 30 tentativas, contra um servidor real (o mongomock não garante atomicidade do servidor)."""
    from pymongo import MongoClient

    from app.services import rate_limit

    cliente = MongoClient(os.environ["MONGO_TEST_URI"], serverSelectionTimeoutMS=5000)
    db = cliente["finsight_teste_rate_limit"]
    try:
        db.rate_limits.delete_many({})
        k = rate_limit.key("login:email", EMAIL)
        _em_paralelo(lambda: rate_limit.hit(db, k, rate_limit.LOGIN_EMAIL), 30)
        with pytest.raises(rate_limit.RateLimited):
            rate_limit.ensure_allowed(db, [k])
    finally:
        cliente.drop_database("finsight_teste_rate_limit")
        cliente.close()


def test_login_em_paralelo_pela_rota_nao_passa_de_cinco_tentativas(client, auth, banco_limpo, monkeypatch):
    """P0-5: a checagem de bloqueio acontece antes da verificação da senha (bcrypt é lento). Se a tentativa só
    fosse contada depois da falha, as 30 simultâneas passariam pela checagem e todas teriam direito à senha."""
    import time

    from app.routers import auth as rota

    verificadas = []

    def verificacao_lenta(user, senha):
        verificadas.append(senha)
        time.sleep(0.3)
        return False

    monkeypatch.setattr(rota, "verify_login", verificacao_lenta)
    codigos: list[int] = []
    _em_paralelo(lambda: codigos.append(_login(client).status_code), 30)
    assert codigos.count(401) <= 5
    assert codigos.count(429) >= 25
    assert len(verificadas) <= 5


def test_login_certo_nao_gasta_tentativa(client, auth, relogio, banco_limpo):
    """Contar a tentativa antes de verificar não pode punir quem acerta: só falhas contam."""
    for _ in range(4):
        assert _login(client).status_code == 401
    for _ in range(10):
        assert _login(client, senha="senha-forte-1").status_code == 200
    for _ in range(4):
        assert _login(client).status_code == 401  # o contador voltou a zero no acerto
