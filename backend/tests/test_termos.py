"""P3-d – o cadastro grava a versão do termo aceito junto da data de aceite."""
from app.db import get_db
from app.models import TERMOS_VERSAO


def test_cadastro_grava_versao_e_data_do_aceite(client):
    r = client.post("/auth/register", json={"name": "Ana", "email": "ana@finsight.app",
                                            "password": "senha-forte-1", "accept_terms": True})
    assert r.status_code == 201
    usuario = get_db().users.find_one({"email": "ana@finsight.app"})
    assert usuario["terms_version"] == TERMOS_VERSAO == "1.0"
    assert usuario["terms_accepted_at"] is not None
