"""Regressão: os testes não podem criar nem alterar o banco real (P6 em docs/execucao.md).

A trava de conexão fica em tests/conftest.py. Aqui não abrimos o engine real de
propósito: o SQLite criaria o arquivo antes mesmo de a trava disparar.
"""

from sqlalchemy import event

from app import database


def _estado_do_arquivo():
    caminho = database.DB_PATH
    if not caminho.exists():
        return None
    info = caminho.stat()
    return info.st_size, info.st_mtime_ns


def test_t1_32_gravar_pela_api_nao_altera_o_arquivo_real(client):
    antes = _estado_do_arquivo()
    resposta = client.post(
        "/api/veiculos", json={"placa": "TST1A23", "marca": "Fiat", "modelo": "Uno", "ano": 2020}
    )
    assert resposta.status_code == 201
    assert client.get("/api/veiculos").json()[0]["placa"] == "TST1A23"
    assert _estado_do_arquivo() == antes


def test_t1_33_trava_de_conexao_esta_ativa(proibir_banco_real):
    assert event.contains(database.engine, "connect", proibir_banco_real)
