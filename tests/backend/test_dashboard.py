"""Sprint 3 — indicadores do painel (CA03 e T3-xx em docs/teste.md).

Base conhecida (todos os dados fictícios), valores calculados à mão conforme ADR-010:

  Veículos: V1 disponível · V2 disponível (vira em viagem) · V3 manutenção · V4 inativo
            · V5 disponível, só com uma viagem cancelada (que tem km: não pode entrar nas contas)
  Março/2030:
    D1 V1 realizado 100 km  entrega        Centro     D5 V2 em andamento  operacional  Sul
    D2 V1 realizado  50 km  entrega        Centro     D6 V5 cancelado     outros       Sul
    D3 V1 realizado sem km  operacional    Norte      D7 V2 previsto      entrega      Centro
    D4 V1 previsto          administrativa Centro
  Fora de março: D8 (fev) V2 realizado 300 km outros/Antigo · D9 (mai) V1 previsto outros/Futuro
"""

import time
from datetime import date, timedelta

import pytest

MARCO = "data_inicio=2030-03-01&data_fim=2030-03-31"
TUDO = "data_inicio=2030-02-01&data_fim=2030-05-31"


def post(client, url, corpo):
    resposta = client.post(url, json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.fixture()
def base(client):
    motorista = post(client, "/api/motoristas", {"nome": "Ana Exemplo", "cnh": "00000000001"})
    veiculos = {}
    for chave, placa, km, status in [
        ("v1", "TST1A01", 1000, "disponivel"),
        ("v2", "TST2B02", 2000, "disponivel"),
        ("v3", "TST3C03", 3000, "manutencao"),
        ("v4", "TST4D04", 4000, "inativo"),
        ("v5", "TST5E05", 5000, "disponivel"),
    ]:
        veiculos[chave] = post(
            client,
            "/api/veiculos",
            {
                "placa": placa,
                "marca": "Marca",
                "modelo": "Modelo",
                "ano": 2022,
                "km_atual": km,
                "status": status,
            },
        )

    def desl(chave, destino, saida, retorno, finalidade, status, km_inicial=None, km_final=None):
        corpo = {
            "veiculo_id": veiculos[chave]["id"],
            "motorista_id": motorista["id"],
            "destino": destino,
            "data_saida": saida,
            "data_retorno": retorno,
            "finalidade": finalidade,
            "status": status,
        }
        if km_inicial is not None:
            corpo["km_inicial"] = km_inicial
        if km_final is not None:
            corpo["km_final"] = km_final
        return post(client, "/api/deslocamentos", corpo)

    d = {}
    d[1] = desl("v1", "Centro", "2030-03-01", "2030-03-02", "entrega", "realizado", 1000, 1100)
    d[2] = desl("v1", "Centro", "2030-03-05", "2030-03-05", "entrega", "realizado", 1100, 1150)
    d[3] = desl("v1", "Norte", "2030-03-08", "2030-03-08", "operacional", "realizado", 1150)
    d[4] = desl("v1", "Centro", "2030-03-20", "2030-03-21", "administrativa", "previsto")
    d[5] = desl("v2", "Sul", "2030-03-10", "2030-03-12", "operacional", "em_andamento")
    d[6] = desl("v5", "Sul", "2030-03-15", "2030-03-15", "outros", "cancelado", 5000, 5200)
    d[7] = desl("v2", "Centro", "2030-03-25", "2030-03-26", "entrega", "previsto")
    d[8] = desl("v2", "Antigo", "2030-02-10", "2030-02-10", "outros", "realizado", 2000, 2300)
    d[9] = desl("v1", "Futuro", "2030-05-10", None, "outros", "previsto")
    return {"veiculos": veiculos, "motorista": motorista, "desl": d, "criar": desl}


def indicadores(client, periodo):
    resposta = client.get(f"/api/dashboard/indicadores?{periodo}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def rotulos(itens):
    return [(i["rotulo"], i["valor"]) for i in itens]


def test_ca3_a_indicadores_com_base_conhecida(client, base):
    ind = indicadores(client, MARCO)
    assert (ind["periodo_inicio"], ind["periodo_fim"]) == ("2030-03-01", "2030-03-31")

    # Veículos
    assert ind["total_veiculos"] == 5
    assert ind["veiculos_disponiveis"] == 2  # V1 e V5
    assert ind["veiculos_em_viagem"] == 1
    assert ind["veiculos_manutencao"] == 1
    assert ind["veiculos_inativos"] == 1

    # Deslocamentos e viagens: total = previstas + em andamento + realizadas + canceladas
    assert ind["total_deslocamentos"] == 7
    assert ind["viagens_previstas"] == 2
    assert ind["viagens_em_andamento"] == 1
    assert ind["viagens_realizadas"] == 3
    assert ind["viagens_canceladas"] == 1
    assert 2 + 1 + 3 + 1 == ind["total_deslocamentos"]

    # Calculados
    assert ind["taxa_realizacao"] == 60.0  # 3 ÷ (2 + 3)
    assert ind["km_total_percorrido"] == 150.0  # só realizadas com km: 100 + 50
    assert ind["media_km_por_viagem"] == 75.0  # 150 ÷ 2 (a realizada sem km não entra)
    assert ind["taxa_utilizacao_frota"] == 40.0  # V1 e V2 de 5; V5 só tem viagem cancelada

    # Quebras
    assert rotulos(ind["deslocamentos_por_finalidade"]) == [
        ("Entrega", 3),
        ("Operacional", 2),
        ("Administrativa", 1),
        ("Outros", 1),
    ]
    assert rotulos(ind["top_destinos"]) == [("Centro", 4), ("Sul", 2), ("Norte", 1)]
    assert rotulos(ind["serie_mensal"]) == [("2030-03", 7)]
    for quebra in ("deslocamentos_por_finalidade", "serie_mensal"):
        assert sum(i["valor"] for i in ind[quebra]) == ind["total_deslocamentos"]


def test_ca3_b_mudar_o_periodo_recalcula_tudo(client, base):
    tudo = indicadores(client, TUDO)
    assert tudo["total_deslocamentos"] == 9
    assert tudo["taxa_utilizacao_frota"] == 40.0
    assert (tudo["viagens_previstas"], tudo["viagens_realizadas"]) == (3, 4)
    assert tudo["taxa_realizacao"] == 57.1  # 4 ÷ 7
    assert tudo["km_total_percorrido"] == 450.0
    assert tudo["media_km_por_viagem"] == 150.0  # 450 ÷ 3 realizadas com km
    assert rotulos(tudo["serie_mensal"]) == [("2030-02", 1), ("2030-03", 7), ("2030-05", 1)]
    assert rotulos(tudo["top_destinos"]) == [
        ("Centro", 4),
        ("Sul", 2),
        ("Antigo", 1),
        ("Futuro", 1),
        ("Norte", 1),
    ]

    fevereiro = indicadores(client, "data_inicio=2030-02-01&data_fim=2030-02-28")
    assert fevereiro["total_deslocamentos"] == 1
    assert (fevereiro["viagens_previstas"], fevereiro["viagens_realizadas"]) == (0, 1)
    assert fevereiro["taxa_realizacao"] == 100.0
    assert fevereiro["km_total_percorrido"] == 300.0
    assert fevereiro["taxa_utilizacao_frota"] == 20.0  # só V2, de 5 veículos
    # a situação dos veículos não depende do período
    assert fevereiro["veiculos_em_viagem"] == 1

    sem_dados = indicadores(client, "data_inicio=2031-01-01&data_fim=2031-01-31")
    assert sem_dados["total_deslocamentos"] == 0
    assert sem_dados["total_veiculos"] == 5


def test_t3_01_base_vazia_retorna_zeros_sem_dividir_por_zero(client):
    ind = indicadores(client, MARCO)
    numericos = [k for k, v in ind.items() if isinstance(v, int | float)]
    assert numericos and all(ind[k] == 0 for k in numericos)
    assert ind["deslocamentos_por_finalidade"] == []
    assert ind["top_destinos"] == []
    assert ind["serie_mensal"] == []
    assert client.get("/api/dashboard/proximas-saidas").json() == []


def test_t3_01b_so_veiculos_sem_deslocamentos(client):
    post(
        client,
        "/api/veiculos",
        {"placa": "TST1A01", "marca": "Marca", "modelo": "Modelo", "ano": 2022},
    )
    ind = indicadores(client, MARCO)
    assert (ind["total_veiculos"], ind["veiculos_disponiveis"]) == (1, 1)
    assert ind["taxa_utilizacao_frota"] == 0.0
    assert ind["taxa_realizacao"] == 0.0
    assert ind["media_km_por_viagem"] == 0.0


def test_t3_02_indicadores_acompanham_criacao_conclusao_e_exclusao(client, base):
    """Os 3 indicadores (veículos, deslocamentos, viagens) mudam junto com os dados."""
    antes = indicadores(client, MARCO)

    # criar: mais um deslocamento previsto no período
    novo = base["criar"]("v1", "Leste", "2030-03-28", "2030-03-28", "entrega", "previsto")
    criado = indicadores(client, MARCO)
    assert criado["total_deslocamentos"] == antes["total_deslocamentos"] + 1
    assert criado["viagens_previstas"] == antes["viagens_previstas"] + 1
    assert criado["viagens_realizadas"] == antes["viagens_realizadas"]
    assert criado["veiculos_em_viagem"] == antes["veiculos_em_viagem"]

    # concluir a viagem em andamento (V2): vira realizada, V2 volta a disponível
    d5 = base["desl"][5]
    concluida = client.post(
        f"/api/deslocamentos/{d5['id']}/concluir",
        json={"km_final": d5["km_inicial"] + 80, "data_retorno": "2030-03-12"},
    )
    assert concluida.status_code == 200
    depois = indicadores(client, MARCO)
    assert depois["viagens_em_andamento"] == 0
    assert depois["viagens_realizadas"] == antes["viagens_realizadas"] + 1
    assert depois["veiculos_em_viagem"] == 0
    assert depois["veiculos_disponiveis"] == antes["veiculos_disponiveis"] + 1
    assert depois["km_total_percorrido"] == antes["km_total_percorrido"] + 80
    assert depois["taxa_realizacao"] == round(4 / (3 + 4) * 100, 1)  # 4 realizadas, 3 previstas

    # cancelar uma prevista: sai do denominador da taxa
    client.put(f"/api/deslocamentos/{novo['id']}", json={"status": "cancelado"})
    cancelado = indicadores(client, MARCO)
    assert cancelado["viagens_previstas"] == antes["viagens_previstas"]
    assert cancelado["viagens_canceladas"] == antes["viagens_canceladas"] + 1
    assert cancelado["total_deslocamentos"] == depois["total_deslocamentos"]

    # excluir: total cai
    client.delete(f"/api/deslocamentos/{novo['id']}")
    excluido = indicadores(client, MARCO)
    assert excluido["total_deslocamentos"] == cancelado["total_deslocamentos"] - 1
    assert excluido["viagens_canceladas"] == cancelado["viagens_canceladas"] - 1

    # veículos: novo cadastro e mudança de situação aparecem
    post(
        client,
        "/api/veiculos",
        {"placa": "TST6F06", "marca": "Marca", "modelo": "Modelo", "ano": 2023},
    )
    final = indicadores(client, MARCO)
    assert final["total_veiculos"] == antes["total_veiculos"] + 1
    assert final["taxa_utilizacao_frota"] == 33.3  # 2 de 6


def test_t3_03_periodo_invertido_e_data_invalida_422(client):
    invertido = client.get("/api/dashboard/indicadores?data_inicio=2030-03-31&data_fim=2030-03-01")
    assert invertido.status_code == 422
    assert "data final do período" in invertido.json()["detail"]
    assert client.get("/api/dashboard/indicadores?data_inicio=31-03-2030").status_code == 422


def test_t3_04_periodo_padrao_e_90_dias_atras_a_30_a_frente(client):
    ind = indicadores(client, "")
    hoje = date.today()
    assert ind["periodo_inicio"] == (hoje - timedelta(days=90)).isoformat()
    assert ind["periodo_fim"] == (hoje + timedelta(days=30)).isoformat()


def test_t3_05_proximas_saidas_so_previstas_futuras_em_ordem(client, base):
    hoje = date.today()
    veiculo_id, motorista_id = base["veiculos"]["v1"]["id"], base["motorista"]["id"]
    for dias, destino, status in [
        (5, "Terceiro", "previsto"),
        (1, "Primeiro", "previsto"),
        (3, "Segundo", "previsto"),
        (2, "Cancelada", "cancelado"),
        (-3, "Passada", "previsto"),
    ]:
        saida = (hoje + timedelta(days=dias)).isoformat()
        post(
            client,
            "/api/deslocamentos",
            {
                "veiculo_id": veiculo_id,
                "motorista_id": motorista_id,
                "destino": destino,
                "data_saida": saida,
                "finalidade": "outros",
                "status": status,
            },
        )
    proximas = client.get("/api/dashboard/proximas-saidas").json()
    # a base fixa (2030) também tem previstas futuras, mas depois das de hoje+N dias
    assert [p["destino"] for p in proximas][:3] == ["Primeiro", "Segundo", "Terceiro"]
    assert all(p["status"] == "previsto" for p in proximas)
    assert "Cancelada" not in [p["destino"] for p in proximas]
    assert "Passada" not in [p["destino"] for p in proximas]
    assert len(client.get("/api/dashboard/proximas-saidas?limite=2").json()) == 2
    assert client.get("/api/dashboard/proximas-saidas?limite=0").status_code == 422


def test_t3_06_desempenho_com_10_mil_deslocamentos(client):
    """RNF04: respostas em até 500 ms para bases de até 10 mil deslocamentos."""
    from app.database import get_db
    from app.main import app
    from app.models import Deslocamento, Finalidade, Motorista, StatusDeslocamento, Veiculo

    db = next(app.dependency_overrides[get_db]())
    try:
        veiculos = [
            Veiculo(placa=f"TST{i}A00", marca="M", modelo="Mod", ano=2022) for i in range(10)
        ]
        motorista = Motorista(nome="Pessoa Exemplo", cnh="00000000009")
        db.add_all(veiculos + [motorista])
        db.flush()
        inicio = date(2030, 1, 1)
        finalidades, situacoes = list(Finalidade), list(StatusDeslocamento)
        db.add_all(
            Deslocamento(
                veiculo_id=veiculos[i % 10].id,
                motorista_id=motorista.id,
                destino=f"Destino {i % 37}",
                data_saida=inicio + timedelta(days=i % 360),
                finalidade=finalidades[i % len(finalidades)],
                status=situacoes[i % len(situacoes)],
                km_inicial=0,
                km_final=50 + i % 100,
            )
            for i in range(10_000)
        )
        db.commit()
    finally:
        db.close()

    for caminho in (
        "/api/dashboard/indicadores?data_inicio=2030-01-01&data_fim=2030-12-31",
        "/api/dashboard/proximas-saidas",
        "/api/deslocamentos?limite=200",
    ):
        melhor = min(_medir(client, caminho) for _ in range(3))
        assert melhor < 0.5, f"{caminho} levou {melhor * 1000:.0f} ms"
    ind = indicadores(client, "data_inicio=2030-01-01&data_fim=2030-12-31")
    assert ind["total_deslocamentos"] == 10_000


def _medir(client, caminho):
    inicio = time.perf_counter()
    assert client.get(caminho).status_code == 200
    return time.perf_counter() - inicio
