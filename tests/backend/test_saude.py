"""Sprint 0 — testes de fumaça do esqueleto (T0-01 a T0-04 em docs/teste.md)."""


def test_t0_01_saude_responde_com_banco_ok(client):
    resposta = client.get("/api/saude")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["status"] == "ok"
    assert dados["banco"] == "ok"


def test_t0_02_interface_e_servida_na_raiz(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["content-type"]
    assert "Rodagem" in resposta.text


def test_t0_03_arquivos_estaticos_sao_servidos(client):
    assert client.get("/static/css/styles.css").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200


def test_t0_04_documentacao_openapi_disponivel(client):
    resposta = client.get("/openapi.json")
    assert resposta.status_code == 200
    assert "/api/saude" in resposta.json()["paths"]
