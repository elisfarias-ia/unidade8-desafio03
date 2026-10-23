"""Sprint 1 — CRUD de veículos e CA01 (IDs em docs/teste.md)."""

VEICULO = {"placa": "TST1A23", "marca": "Fiat", "modelo": "Strada", "ano": 2022}


def criar(client, **extra):
    resposta = client.post("/api/veiculos", json={**VEICULO, **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_ca1_a_cadastro_aparece_na_listagem_como_disponivel(client):
    criado = criar(client)
    assert criado["status"] == "disponivel"
    assert criado["km_atual"] == 0

    lista = client.get("/api/veiculos").json()
    assert [v["placa"] for v in lista] == ["TST1A23"]


def test_ca1_b_placa_duplicada_e_recusada_com_409(client):
    criar(client)
    # mesma placa, escrita com hífen e minúsculas: normaliza e conflita
    resposta = client.post("/api/veiculos", json={**VEICULO, "placa": "tst-1a23"})
    assert resposta.status_code == 409
    assert "TST1A23" in resposta.json()["detail"]


def test_ca1_c_placa_invalida_e_recusada_com_422_sem_gravar(client):
    for placa in ["AB12345", "ABCD123", "1234567", "ABC12D3", ""]:
        resposta = client.post("/api/veiculos", json={**VEICULO, "placa": placa})
        assert resposta.status_code == 422, placa
        assert resposta.json()["erros"][0]["campo"] == "placa"
    assert client.get("/api/veiculos").json() == []


def test_t1_01_placas_nos_dois_padroes_sao_aceitas_e_normalizadas(client):
    assert criar(client, placa="abc-1234")["placa"] == "ABC1234"
    assert criar(client, placa=" abc1d23 ")["placa"] == "ABC1D23"


def test_t1_02_validacoes_de_campos_em_portugues(client):
    resposta = client.post("/api/veiculos", json={"placa": "TST1A23", "ano": 1900, "km_atual": -1})
    assert resposta.status_code == 422
    erros = {e["campo"]: e["mensagem"] for e in resposta.json()["erros"]}
    assert erros["marca"] == "Campo obrigatório."
    assert erros["modelo"] == "Campo obrigatório."
    assert erros["ano"] == "Deve ser maior ou igual a 1950."
    assert erros["km_atual"] == "Deve ser maior ou igual a 0."


def test_t1_03_consultar_por_id_e_inexistente_404(client):
    criado = criar(client)
    assert client.get(f"/api/veiculos/{criado['id']}").json()["placa"] == "TST1A23"
    resposta = client.get("/api/veiculos/999")
    assert resposta.status_code == 404
    assert "não encontrado" in resposta.json()["detail"]


def test_t1_04_filtros_de_busca_e_situacao(client):
    criar(client)
    criar(client, placa="TST2B34", marca="Toyota", modelo="Corolla", status="manutencao")
    assert [v["placa"] for v in client.get("/api/veiculos?busca=corol").json()] == ["TST2B34"]
    assert [v["placa"] for v in client.get("/api/veiculos?status=disponivel").json()] == ["TST1A23"]


def test_t1_05_editar_veiculo_persiste_alteracoes(client):
    criado = criar(client)
    resposta = client.put(
        f"/api/veiculos/{criado['id']}",
        json={"modelo": "Strada Cabine Dupla", "km_atual": 1500, "placa": "tst9z99"},
    )
    assert resposta.status_code == 200
    atualizado = client.get(f"/api/veiculos/{criado['id']}").json()
    assert atualizado["modelo"] == "Strada Cabine Dupla"
    assert atualizado["km_atual"] == 1500
    assert atualizado["placa"] == "TST9Z99"
    assert atualizado["marca"] == "Fiat"  # campo não enviado fica igual


def test_t1_06_editar_para_placa_de_outro_veiculo_409(client):
    criar(client)
    outro = criar(client, placa="TST2B34")
    resposta = client.put(f"/api/veiculos/{outro['id']}", json={"placa": "TST1A23"})
    assert resposta.status_code == 409


def test_t1_07_editar_campo_obrigatorio_para_nulo_422(client):
    criado = criar(client)
    resposta = client.put(f"/api/veiculos/{criado['id']}", json={"marca": None})
    assert resposta.status_code == 422
    assert "marca" in resposta.json()["detail"]


def test_t1_08_editar_inexistente_404(client):
    assert client.put("/api/veiculos/999", json={"modelo": "Xyz"}).status_code == 404


def test_t1_09_excluir_veiculo_sem_historico(client):
    criado = criar(client)
    assert client.delete(f"/api/veiculos/{criado['id']}").status_code == 204
    assert client.get(f"/api/veiculos/{criado['id']}").status_code == 404
    assert client.delete(f"/api/veiculos/{criado['id']}").status_code == 404
