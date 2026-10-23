"""Sprint 1 — deslocamentos: CRUD, regras de negócio e histórico (IDs em docs/teste.md)."""

import pytest


@pytest.fixture()
def base(client):
    """Um veículo disponível (km 1000) e um motorista ativo, ambos fictícios."""
    v = client.post(
        "/api/veiculos",
        json={
            "placa": "TST1A23",
            "marca": "Fiat",
            "modelo": "Strada",
            "ano": 2022,
            "km_atual": 1000,
        },
    ).json()
    m = client.post("/api/motoristas", json={"nome": "Ana Exemplo", "cnh": "00000000001"}).json()
    return {"veiculo_id": v["id"], "motorista_id": m["id"]}


def registrar(client, base, **extra):
    dados = {
        **base,
        "destino": "Unidade Centro",
        "data_saida": "2030-03-10",
        "data_retorno": "2030-03-12",
        "finalidade": "administrativa",
        **extra,
    }
    return client.post("/api/deslocamentos", json=dados)


def test_ca2_a_registrar_e_aparecer_no_historico(client, base):
    resposta = registrar(client, base)
    assert resposta.status_code == 201, resposta.text
    criado = resposta.json()
    assert criado["status"] == "previsto"
    assert criado["km_inicial"] == 1000  # herdado do veículo
    assert criado["veiculo"]["placa"] == "TST1A23"
    assert criado["motorista"]["nome"] == "Ana Exemplo"

    historico = client.get("/api/deslocamentos").json()
    assert [d["id"] for d in historico] == [criado["id"]]


def test_ca2_b_retorno_antes_da_saida_422(client, base):
    resposta = registrar(client, base, data_saida="2030-03-10", data_retorno="2030-03-09")
    assert resposta.status_code == 422
    assert "data de retorno não pode ser anterior" in resposta.json()["detail"]


def test_ca2_c_conflito_de_agenda_409(client, base):
    primeiro = registrar(client, base).json()
    resposta = registrar(client, base, data_saida="2030-03-12", data_retorno="2030-03-14")
    assert resposta.status_code == 409
    assert f"#{primeiro['id']}" in resposta.json()["detail"]
    # dia seguinte ao retorno: livre
    assert (
        registrar(client, base, data_saida="2030-03-13", data_retorno="2030-03-13").status_code
        == 201
    )


def test_ca2_d_filtro_por_destino(client, base):
    registrar(client, base, destino="Almoxarifado Central")
    registrar(client, base, destino="Polo Rural", data_saida="2030-04-01", data_retorno=None)
    nomes = [d["destino"] for d in client.get("/api/deslocamentos?destino=almox").json()]
    assert nomes == ["Almoxarifado Central"]


def test_t1_20_demais_filtros_combinados(client, base):
    registrar(client, base, finalidade="entrega")
    registrar(client, base, data_saida="2030-05-01", data_retorno=None, status="cancelado")
    q = "/api/deslocamentos?finalidade=entrega&data_inicio=2030-03-01&data_fim=2030-03-31"
    assert len(client.get(q).json()) == 1
    assert len(client.get("/api/deslocamentos?status=cancelado").json()) == 1
    assert len(client.get(f"/api/deslocamentos?veiculo_id={base['veiculo_id']}").json()) == 2
    assert client.get("/api/deslocamentos?motorista_id=999").json() == []
    invertido = client.get("/api/deslocamentos?data_inicio=2030-03-31&data_fim=2030-03-01")
    assert invertido.status_code == 422


def test_t1_21_campos_obrigatorios_e_finalidade_invalida_422(client, base):
    resposta = client.post("/api/deslocamentos", json={**base, "finalidade": "passeio"})
    assert resposta.status_code == 422
    erros = {e["campo"]: e["mensagem"] for e in resposta.json()["erros"]}
    assert erros["destino"] == "Campo obrigatório."
    assert erros["data_saida"] == "Campo obrigatório."
    assert erros["finalidade"].startswith("Valor inválido. Opções aceitas:")


def test_t1_22_km_final_menor_que_inicial_422(client, base):
    resposta = registrar(client, base, status="realizado", km_inicial=500, km_final=400)
    assert resposta.status_code == 422
    # km inicial herdado do veículo (1000) também vale
    resposta = registrar(client, base, status="realizado", km_final=900)
    assert resposta.status_code == 422


def test_t1_23_realizado_exige_data_retorno_422(client, base):
    resposta = registrar(client, base, status="realizado", data_retorno=None)
    assert resposta.status_code == 422


def test_t1_24_veiculo_manutencao_ou_motorista_inativo_409(client, base):
    client.put(f"/api/veiculos/{base['veiculo_id']}", json={"status": "manutencao"})
    resposta = registrar(client, base)
    assert resposta.status_code == 409
    assert "está em manutenção" in resposta.json()["detail"]

    client.put(f"/api/veiculos/{base['veiculo_id']}", json={"status": "disponivel"})
    client.put(f"/api/motoristas/{base['motorista_id']}", json={"ativo": False})
    resposta = registrar(client, base)
    assert resposta.status_code == 409
    assert "inativo" in resposta.json()["detail"]


def test_t1_25_veiculo_ou_motorista_inexistente_404(client, base):
    assert registrar(client, {**base, "veiculo_id": 999}).status_code == 404
    assert registrar(client, {**base, "motorista_id": 999}).status_code == 404


def test_t1_26_em_andamento_ocupa_e_concluir_libera_e_atualiza_km(client, base):
    criado = registrar(client, base, status="em_andamento").json()
    veiculo_url = f"/api/veiculos/{base['veiculo_id']}"
    assert client.get(veiculo_url).json()["status"] == "em_viagem"

    resposta = client.post(
        f"/api/deslocamentos/{criado['id']}/concluir",
        json={"km_final": 1250, "data_retorno": "2030-03-11"},
    )
    assert resposta.status_code == 200
    concluido = resposta.json()
    assert concluido["status"] == "realizado"
    assert concluido["km_percorrido"] == 250
    veiculo = client.get(veiculo_url).json()
    assert (veiculo["status"], veiculo["km_atual"]) == ("disponivel", 1250)

    # concluir de novo não é permitido
    again = client.post(f"/api/deslocamentos/{criado['id']}/concluir", json={"km_final": 1300})
    assert again.status_code == 409


def test_t1_27_concluir_com_dados_incoerentes(client, base):
    criado = registrar(client, base).json()
    url = f"/api/deslocamentos/{criado['id']}/concluir"
    assert client.post(url, json={"km_final": 900, "data_retorno": "2030-03-12"}).status_code == 422
    assert (
        client.post(url, json={"km_final": 1100, "data_retorno": "2030-03-01"}).status_code == 422
    )
    assert client.post(url, json={}).status_code == 422
    assert client.post("/api/deslocamentos/999/concluir", json={"km_final": 1}).status_code == 404

    client.put(f"/api/deslocamentos/{criado['id']}", json={"status": "cancelado"})
    assert (
        client.post(url, json={"km_final": 1100, "data_retorno": "2030-03-12"}).status_code == 409
    )


def test_t1_28_editar_deslocamento(client, base):
    criado = registrar(client, base).json()
    url = f"/api/deslocamentos/{criado['id']}"
    resposta = client.put(url, json={"destino": "Polo Rural", "data_retorno": "2030-03-15"})
    assert resposta.status_code == 200
    atual = client.get(url).json()
    assert (atual["destino"], atual["data_retorno"]) == ("Polo Rural", "2030-03-15")

    # editar não gera conflito consigo mesmo, mas respeita as regras 3 e 5
    assert client.put(url, json={"data_retorno": "2030-03-01"}).status_code == 422
    outro = registrar(client, base, data_saida="2030-04-01", data_retorno="2030-04-02").json()
    resposta = client.put(f"/api/deslocamentos/{outro['id']}", json={"data_saida": "2030-03-14"})
    assert resposta.status_code == 409
    # nada foi gravado pelas tentativas recusadas
    assert client.get(url).json()["data_retorno"] == "2030-03-15"
    assert client.get(f"/api/deslocamentos/{outro['id']}").json()["data_saida"] == "2030-04-01"


def test_t1_29_editar_para_veiculo_inexistente_404_sem_erro_500(client, base):
    criado = registrar(client, base).json()
    resposta = client.put(f"/api/deslocamentos/{criado['id']}", json={"veiculo_id": 999})
    assert resposta.status_code == 404
    assert client.put("/api/deslocamentos/999", json={"destino": "X Y"}).status_code == 404


def test_t1_30_excluir_deslocamento_e_restricao_de_historico(client, base):
    criado = registrar(client, base).json()
    # com histórico, veículo e motorista não podem ser excluídos (regra 7)
    resposta = client.delete(f"/api/veiculos/{base['veiculo_id']}")
    assert resposta.status_code == 409
    assert "inativo" in resposta.json()["detail"]
    assert client.delete(f"/api/motoristas/{base['motorista_id']}").status_code == 409

    assert client.delete(f"/api/deslocamentos/{criado['id']}").status_code == 204
    assert client.get(f"/api/deslocamentos/{criado['id']}").status_code == 404
    # sem histórico, a exclusão passa
    assert client.delete(f"/api/veiculos/{base['veiculo_id']}").status_code == 204
    assert client.delete(f"/api/motoristas/{base['motorista_id']}").status_code == 204


def test_t1_31_excluir_em_andamento_devolve_veiculo(client, base):
    criado = registrar(client, base, status="em_andamento").json()
    client.delete(f"/api/deslocamentos/{criado['id']}")
    assert client.get(f"/api/veiculos/{base['veiculo_id']}").json()["status"] == "disponivel"


def test_t1_34_veiculo_em_viagem_nao_e_liberado_por_outra_viagem(client, base):
    """Regressão (achada na S3): só libera o veículo quando não resta viagem em andamento."""
    veiculo_url = f"/api/veiculos/{base['veiculo_id']}"
    primeira = registrar(client, base, status="em_andamento").json()
    assert client.get(veiculo_url).json()["status"] == "em_viagem"

    # registrar uma viagem futura para o mesmo veículo não pode libertá-lo
    registrar(client, base, data_saida="2030-04-01", data_retorno="2030-04-02")
    assert client.get(veiculo_url).json()["status"] == "em_viagem"

    # um cancelado registrado depois também não
    registrar(client, base, status="cancelado", data_saida="2030-05-01", data_retorno=None)
    assert client.get(veiculo_url).json()["status"] == "em_viagem"

    # duas em andamento: concluir uma mantém o veículo em viagem; a última o libera
    segunda = registrar(
        client, base, status="em_andamento", data_saida="2030-06-01", data_retorno="2030-06-02"
    ).json()
    concluida = client.post(
        f"/api/deslocamentos/{primeira['id']}/concluir",
        json={"km_final": 1100, "data_retorno": "2030-03-12"},
    )
    assert concluida.status_code == 200
    assert client.get(veiculo_url).json()["status"] == "em_viagem"
    concluida = client.post(
        f"/api/deslocamentos/{segunda['id']}/concluir",
        json={"km_final": 1200, "data_retorno": "2030-06-02"},
    )
    assert concluida.status_code == 200
    assert client.get(veiculo_url).json()["status"] == "disponivel"
