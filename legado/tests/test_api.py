"""Testes dos critérios de aceite do MVP.

Rodar com:  pytest -v
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def cliente():
    Base.metadata.create_all(bind=engine)

    def _get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def novo_veiculo(cliente, placa="ABC1D23"):
    return cliente.post(
        "/api/veiculos",
        json={
            "placa": placa,
            "marca": "Fiat",
            "modelo": "Strada",
            "ano": 2022,
            "km_atual": 10000,
        },
    ).json()


def novo_motorista(cliente, cnh="04512378901"):
    return cliente.post(
        "/api/motoristas", json={"nome": "Joana Ribeiro", "cnh": cnh}
    ).json()


# --------------------------------------------------------------------------- #
# CA1 — cadastro de veículo com placa única e validada
# --------------------------------------------------------------------------- #
def test_ca1_cadastro_de_veiculo_com_placa_unica(cliente):
    r = cliente.post(
        "/api/veiculos",
        json={"placa": "abc-1d23", "marca": "Fiat", "modelo": "Strada", "ano": 2022},
    )
    assert r.status_code == 201
    assert r.json()["placa"] == "ABC1D23"  # normalizada

    duplicada = cliente.post(
        "/api/veiculos",
        json={"placa": "ABC1D23", "marca": "Fiat", "modelo": "Uno", "ano": 2019},
    )
    assert duplicada.status_code == 409

    invalida = cliente.post(
        "/api/veiculos",
        json={"placa": "12345", "marca": "Fiat", "modelo": "Uno", "ano": 2019},
    )
    assert invalida.status_code == 422


# --------------------------------------------------------------------------- #
# CA2 — registro de deslocamento com validações e consulta de histórico
# --------------------------------------------------------------------------- #
def test_ca2_registro_e_historico_de_deslocamento(cliente):
    v = novo_veiculo(cliente)
    m = novo_motorista(cliente)
    hoje = date.today()

    r = cliente.post(
        "/api/deslocamentos",
        json={
            "veiculo_id": v["id"],
            "motorista_id": m["id"],
            "destino": "Campinas - SP",
            "data_saida": hoje.isoformat(),
            "data_retorno": (hoje + timedelta(days=1)).isoformat(),
            "finalidade": "administrativa",
            "status": "previsto",
        },
    )
    assert r.status_code == 201
    assert r.json()["veiculo"]["placa"] == "ABC1D23"

    # data de retorno anterior à saída é rejeitada
    invalido = cliente.post(
        "/api/deslocamentos",
        json={
            "veiculo_id": v["id"],
            "motorista_id": m["id"],
            "destino": "Santos",
            "data_saida": hoje.isoformat(),
            "data_retorno": (hoje - timedelta(days=2)).isoformat(),
            "finalidade": "entrega",
        },
    )
    assert invalido.status_code == 422

    # mesmo veículo no mesmo intervalo gera conflito de agenda
    conflito = cliente.post(
        "/api/deslocamentos",
        json={
            "veiculo_id": v["id"],
            "motorista_id": m["id"],
            "destino": "Santos",
            "data_saida": hoje.isoformat(),
            "finalidade": "entrega",
        },
    )
    assert conflito.status_code == 409

    historico = cliente.get("/api/deslocamentos?destino=Campinas").json()
    assert len(historico) == 1
    assert historico[0]["destino"] == "Campinas - SP"


# --------------------------------------------------------------------------- #
# CA3 — indicadores calculados a partir dos dados persistidos
# --------------------------------------------------------------------------- #
def test_ca3_indicadores_do_dashboard(cliente):
    v1 = novo_veiculo(cliente, "ABC1D23")
    v2 = novo_veiculo(cliente, "DEF2G45")
    m = novo_motorista(cliente)
    hoje = date.today()

    # uma viagem realizada (120 km)
    cliente.post(
        "/api/deslocamentos",
        json={
            "veiculo_id": v1["id"],
            "motorista_id": m["id"],
            "destino": "Campinas - SP",
            "data_saida": (hoje - timedelta(days=5)).isoformat(),
            "data_retorno": (hoje - timedelta(days=5)).isoformat(),
            "finalidade": "operacional",
            "km_inicial": 10000,
            "km_final": 10120,
            "status": "realizado",
        },
    )
    # uma viagem prevista
    cliente.post(
        "/api/deslocamentos",
        json={
            "veiculo_id": v1["id"],
            "motorista_id": m["id"],
            "destino": "Santos - Porto",
            "data_saida": (hoje + timedelta(days=3)).isoformat(),
            "finalidade": "entrega",
            "status": "previsto",
        },
    )

    ind = cliente.get(
        "/api/dashboard/indicadores"
        f"?data_inicio={(hoje - timedelta(days=30))}&data_fim={hoje + timedelta(days=30)}"
    ).json()

    assert ind["total_veiculos"] == 2
    assert ind["viagens_realizadas"] == 1
    assert ind["viagens_previstas"] == 1
    assert ind["taxa_realizacao"] == 50.0
    assert ind["km_total_percorrido"] == 120.0
    assert ind["media_km_por_viagem"] == 120.0
    assert ind["taxa_utilizacao_frota"] == 50.0  # 1 de 2 veículos usado
    assert {i["rotulo"] for i in ind["top_destinos"]} == {
        "Campinas - SP",
        "Santos - Porto",
    }
    assert v2["id"]  # veículo ocioso permanece na contagem da frota


def test_veiculo_com_historico_nao_pode_ser_excluido(cliente):
    v = novo_veiculo(cliente)
    m = novo_motorista(cliente)
    cliente.post(
        "/api/deslocamentos",
        json={
            "veiculo_id": v["id"],
            "motorista_id": m["id"],
            "destino": "Sorocaba",
            "data_saida": date.today().isoformat(),
            "finalidade": "outros",
        },
    )
    assert cliente.delete(f"/api/veiculos/{v['id']}").status_code == 409


def test_concluir_viagem_atualiza_km_do_veiculo(cliente):
    v = novo_veiculo(cliente)
    m = novo_motorista(cliente)
    d = cliente.post(
        "/api/deslocamentos",
        json={
            "veiculo_id": v["id"],
            "motorista_id": m["id"],
            "destino": "Guarulhos",
            "data_saida": date.today().isoformat(),
            "finalidade": "entrega",
            "status": "em_andamento",
        },
    ).json()

    r = cliente.post(f"/api/deslocamentos/{d['id']}/concluir?km_final=10250")
    assert r.status_code == 200
    assert r.json()["status"] == "realizado"
    assert r.json()["km_percorrido"] == 250.0

    veiculo = cliente.get(f"/api/veiculos/{v['id']}").json()
    assert veiculo["km_atual"] == 10250
    assert veiculo["status"] == "disponivel"
