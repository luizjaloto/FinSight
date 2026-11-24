"""Testes de ponta a ponta da API (T01, T02, T04, T05, T09, T10)."""
from datetime import date, timedelta


def test_cadastro_exige_aceite_do_termo(client):
    """T01"""
    body = {"name": "Ana", "email": "ana@finsight.app", "password": "senha-forte-1", "accept_terms": False}
    assert client.post("/auth/register", json=body).status_code == 400
    body["accept_terms"] = True
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409  # e-mail único


def test_login_com_mensagem_generica(client, auth):
    """T02"""
    r = client.post("/auth/login", json={"email": "teste@finsight.app", "password": "errada-123"})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha incorretos."
    r = client.post("/auth/login", json={"email": "naoexiste@finsight.app", "password": "qualquer-123"})
    assert r.json()["detail"] == "E-mail ou senha incorretos."
    assert client.post("/auth/login", json={"email": "teste@finsight.app", "password": "senha-forte-1"}).status_code == 200


def test_rotas_protegidas_sem_token(client):
    assert client.get("/dashboard").status_code == 401
    assert client.get("/portfolio").status_code == 401


def test_cadastro_de_aplicacoes_e_painel(client, auth):
    """T04 + painel (RF08) + alerta de concentração (RF09)."""
    start = (date.today() - timedelta(days=180)).isoformat()
    rdc = {"type": "renda_fixa", "name": "RDC CrediAlta", "invested": 2000, "start_date": start, "indexer": "cdi", "rate": 1.05}
    r = client.post("/portfolio/assets", json=rdc, headers=auth)
    assert r.status_code == 201 and r.json()["rate"] == 105  # FB05: 1,05 vira 105% do CDI
    acao = {"type": "acao", "name": "Petrobras", "ticker": "petr4", "quantity": 100, "avg_price": 35, "invested": 1, "start_date": start}
    r = client.post("/portfolio/assets", json=acao, headers=auth)
    assert r.status_code == 201 and r.json()["ticker"] == "PETR4" and r.json()["invested"] == 3500
    sem_codigo = {"type": "acao", "name": "Sem código", "quantity": 1, "avg_price": 1, "invested": 1, "start_date": start}
    assert client.post("/portfolio/assets", json=sem_codigo, headers=auth).status_code == 422

    d = client.get("/dashboard", headers=auth).json()
    assert d["patrimonio"] > 0 and len(d["ativos"]) == 2
    assert any(a["kind"] == "concentracao" for a in d["alertas"])
    assert "não são recomendação" in d["aviso"]


def test_importacao_csv(client, auth):
    """T05"""
    csv = "Código de Negociação;Quantidade;Preço de Fechamento\nPETR4;10;38,00\nHGLG11;0,5;160,00\nXX;1;1\n"
    r = client.post("/portfolio/import-csv", headers=auth, files={"file": ("posicao.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200
    assert r.json()["imported"] == 2 and len(r.json()["rejected"]) == 1


def test_glossario_tem_22_termos(client):
    """T09 / RF10"""
    g = client.get("/glossario").json()
    assert len(g) == 22 and any(t["termo"] == "IPCA+" for t in g)


def test_excluir_conta_remove_tudo(client, auth):
    """T10 – a exclusão deve remover usuário, carteira e alertas."""
    start = (date.today() - timedelta(days=30)).isoformat()
    client.post("/portfolio/assets", headers=auth, json={"type": "acao", "name": "Petrobras", "ticker": "PETR4", "quantity": 10,
                                                          "avg_price": 30, "invested": 300, "start_date": start})
    client.get("/dashboard", headers=auth)  # gera alertas
    from app.db import get_db

    db = get_db()
    uid = db.users.find_one({"email": "teste@finsight.app"})["_id"]
    assert db.alerts.count_documents({"user_id": uid}) > 0
    assert client.delete("/auth/me", headers=auth).status_code == 204
    assert db.users.count_documents({"_id": uid}) == 0
    assert db.portfolios.count_documents({"user_id": uid}) == 0
    assert db.alerts.count_documents({"user_id": uid}) == 0
