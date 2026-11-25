"""B1 – o bcrypt só aceita até 72 bytes; senhas maiores não podem derrubar a API (500)."""
import pytest


def _cadastro(client, senha, email="limite@finsight.app"):
    return client.post("/auth/register", json={"name": "Limite", "email": email, "password": senha, "accept_terms": True})


def test_senha_de_72_bytes_cadastra(client):
    assert _cadastro(client, "a" * 72).status_code == 201


@pytest.mark.parametrize("senha", ["a" * 73, "é" * 37, "🔒" * 19, "x" * 128])
def test_senha_acima_de_72_bytes_da_422_com_mensagem_clara(client, senha):
    """'é' ocupa 2 bytes e '🔒' 4 bytes: o limite é em BYTES, não em caracteres."""
    r = _cadastro(client, senha)
    assert r.status_code == 422
    assert "72 bytes" in r.text


def test_login_com_senha_longa_nao_da_500(client, auth):
    r = client.post("/auth/login", json={"email": "teste@finsight.app", "password": "b" * 200})
    assert r.status_code in (401, 422)


def test_hash_password_trata_o_erro_do_bcrypt():
    from app.security import PasswordTooLong, hash_password

    with pytest.raises(PasswordTooLong):
        hash_password("a" * 73)
