"""Sprint 1 — CRUD de motoristas (IDs em docs/teste.md). Dados fictícios."""

MOTORISTA = {"nome": "Ana Exemplo", "cnh": "00000000001", "categoria_cnh": "B"}


def criar(client, **extra):
    resposta = client.post("/api/motoristas", json={**MOTORISTA, **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_t1_10_cadastrar_e_listar_motorista(client):
    criado = criar(client, setor="Logística", telefone="(00) 90000-0001")
    assert criado["ativo"] is True
    assert criado["setor"] == "Logística"
    assert [m["nome"] for m in client.get("/api/motoristas").json()] == ["Ana Exemplo"]


def test_t1_11_cnh_normalizada_e_duplicada_409(client):
    assert criar(client, cnh="000.000.000-01")["cnh"] == "00000000001"
    resposta = client.post("/api/motoristas", json={**MOTORISTA, "nome": "Outra Pessoa"})
    assert resposta.status_code == 409
    assert "CNH" in resposta.json()["detail"]


def test_t1_12_cnh_e_categoria_invalidas_422(client):
    resposta = client.post("/api/motoristas", json={**MOTORISTA, "cnh": "123"})
    assert resposta.status_code == 422
    assert resposta.json()["erros"][0]["mensagem"] == "A CNH deve ter 11 dígitos numéricos."

    resposta = client.post("/api/motoristas", json={**MOTORISTA, "categoria_cnh": "Z"})
    assert resposta.status_code == 422
    assert "Categoria de CNH inválida" in resposta.json()["detail"]


def test_t1_13_consultar_editar_e_inexistente(client):
    criado = criar(client)
    url = f"/api/motoristas/{criado['id']}"
    assert client.get(url).json()["cnh"] == "00000000001"

    resposta = client.put(url, json={"setor": "Operações", "ativo": False, "categoria_cnh": "ab"})
    assert resposta.status_code == 200
    atualizado = client.get(url).json()
    assert (atualizado["setor"], atualizado["ativo"], atualizado["categoria_cnh"]) == (
        "Operações",
        False,
        "AB",
    )
    assert client.get("/api/motoristas/999").status_code == 404
    assert client.put("/api/motoristas/999", json={"setor": "X"}).status_code == 404


def test_t1_14_filtro_apenas_ativos_e_busca(client):
    criar(client)
    criar(client, nome="Bruno Exemplo", cnh="00000000002", ativo=False)
    ativos = client.get("/api/motoristas?apenas_ativos=true").json()
    assert [m["nome"] for m in ativos] == ["Ana Exemplo"]
    assert [m["nome"] for m in client.get("/api/motoristas?busca=bruno").json()] == [
        "Bruno Exemplo"
    ]


def test_t1_15_editar_para_cnh_de_outro_409(client):
    criar(client)
    outro = criar(client, nome="Bruno Exemplo", cnh="00000000002")
    resposta = client.put(f"/api/motoristas/{outro['id']}", json={"cnh": "00000000001"})
    assert resposta.status_code == 409


def test_t1_16_excluir_motorista_sem_historico(client):
    criado = criar(client)
    assert client.delete(f"/api/motoristas/{criado['id']}").status_code == 204
    assert client.get(f"/api/motoristas/{criado['id']}").status_code == 404
