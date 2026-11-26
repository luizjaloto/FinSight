"""P3-e – excluir a conta e baixar os dados exigem um login feito nos últimos 5 minutos."""
from datetime import UTC, datetime, timedelta

from app import clock
from app.db import get_db


def _relogio_adiantado(monkeypatch, minutos: float) -> None:
    """Finge que já passaram 'minutos' desde o login, sem mexer no relógio que o JWT usa para validar."""
    monkeypatch.setattr(clock, "_now", lambda: datetime.now(UTC) + timedelta(minutes=minutos))


def test_login_recente_exporta_e_exclui(client, auth, monkeypatch):
    _relogio_adiantado(monkeypatch, 4)
    assert client.get("/auth/me/export", headers=auth).status_code == 200


def test_login_de_mais_de_5_minutos_nao_exporta_nem_exclui(client, auth, monkeypatch):
    _relogio_adiantado(monkeypatch, 6)
    r = client.get("/auth/me/export", headers=auth)
    assert r.status_code == 403
    assert r.json()["detail"] == "Por segurança, entre de novo para confirmar esta ação."
    r = client.delete("/auth/me", headers=auth)
    assert r.status_code == 403
    assert get_db().users.find_one({"email": "teste@finsight.app"}) is not None  # nada foi apagado


def test_rotas_comuns_seguem_sem_restricao_de_tempo(client, auth, monkeypatch):
    _relogio_adiantado(monkeypatch, 60)
    assert client.get("/auth/me", headers=auth).status_code == 200
    assert client.get("/dashboard", headers=auth).status_code == 200


def test_exportar_e_excluir_sem_token_recebem_401(client):
    assert client.get("/auth/me/export").status_code == 401
    assert client.delete("/auth/me").status_code == 401


def test_exclusao_com_login_recente_remove_a_conta(client, auth):
    assert client.delete("/auth/me", headers=auth).status_code == 204
    assert get_db().users.find_one({"email": "teste@finsight.app"}) is None
