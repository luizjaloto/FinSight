"""P0-4 – o upload do CSV é recusado antes de o arquivo inteiro ser lido ou gravado."""


def _csv(tamanho: int) -> bytes:
    linha = b"PETR4;1;38,00\n"
    return (linha * (tamanho // len(linha) + 1))[:tamanho]


def test_upload_de_2_mb_recebe_400_sem_montar_o_formulario(client, auth, monkeypatch):
    """O cabeçalho Content-Length é checado antes de request.form(), que grava o arquivo inteiro."""
    from starlette.requests import Request

    def nao_deve_ser_chamado(self, *args, **kwargs):
        raise AssertionError("o formulário não deveria ser lido para um upload tão grande")

    monkeypatch.setattr(Request, "form", nao_deve_ser_chamado)
    r = client.post("/portfolio/import-csv", headers=auth,
                    files={"file": ("grande.csv", _csv(2 * 1024 * 1024), "text/csv")})
    assert r.status_code == 400
    assert r.json()["detail"] == "Arquivo muito grande (máximo 1 MB)."


def test_arquivo_logo_acima_de_1_mb_e_recusado_pela_leitura_limitada(client, auth):
    """Passa do cabeçalho (cabe na margem do multipart), mas a leitura para em 1_000_001 bytes."""
    r = client.post("/portfolio/import-csv", headers=auth,
                    files={"file": ("quase.csv", _csv(1_000_500), "text/csv")})
    assert r.status_code == 400
    assert r.json()["detail"] == "Arquivo muito grande (máximo 1 MB)."


def test_csv_pequeno_continua_sendo_importado(client, auth):
    csv = "Código de Negociação;Quantidade;Preço de Fechamento\nPETR4;10;38,00\n"
    r = client.post("/portfolio/import-csv", headers=auth, files={"file": ("ok.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200 and r.json()["imported"] == 1


def test_upload_sem_token_continua_recusado(client):
    r = client.post("/portfolio/import-csv", files={"file": ("ok.csv", b"a;b\n", "text/csv")})
    assert r.status_code == 401


def test_formulario_sem_o_campo_file_recebe_422(client, auth):
    r = client.post("/portfolio/import-csv", headers=auth, files={"outro": ("ok.csv", b"a;b\n", "text/csv")})
    assert r.status_code == 422
