"""S1 – o login não pode revelar, pelo tempo de resposta, se um e-mail tem conta."""
import statistics
import time

from app import security


def _login(client, email, senha="senha-errada-123"):
    return client.post("/auth/login", json={"email": email, "password": senha})


def test_email_inexistente_tambem_passa_pelo_bcrypt(client, monkeypatch):
    chamadas = []
    original = security.bcrypt.checkpw
    monkeypatch.setattr(security.bcrypt, "checkpw", lambda s, h: chamadas.append(1) or original(s, h))
    r = _login(client, "ninguem@finsight.app")
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha incorretos."
    assert len(chamadas) == 1


def test_tempo_parecido_para_email_existente_e_inexistente(client, auth):
    def mediana(email):
        tempos = []
        for _ in range(5):
            t = time.perf_counter()
            _login(client, email)
            tempos.append(time.perf_counter() - t)
        return statistics.median(tempos)

    _login(client, "teste@finsight.app")  # aquece
    existe, nao_existe = mediana("teste@finsight.app"), mediana("ninguem@finsight.app")
    diferenca = abs(existe - nao_existe) / max(existe, nao_existe)
    assert diferenca < 0.20, f"existente={existe:.3f}s inexistente={nao_existe:.3f}s diferença={diferenca:.0%}"
