"""Fixtures compartilhadas: banco SQLite em memória, nunca o arquivo real."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def proibir_banco_real():
    """Trava: qualquer conexão com backend/data/*.db durante os testes é um erro."""

    def _recusar(*_):
        raise RuntimeError(f"Um teste tentou abrir o banco real ({database.DB_PATH}).")

    event.listen(database.engine, "connect", _recusar)
    yield _recusar
    event.remove(database.engine, "connect", _recusar)


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessaoTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _get_db_teste():
        db = SessaoTeste()
        try:
            yield db
        finally:
            db.close()

    # O lifespan da aplicação criaria as tabelas no arquivo real; aqui não faz nada.
    monkeypatch.setattr("app.main.criar_tabelas", lambda: None)
    app.dependency_overrides[get_db] = _get_db_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()
