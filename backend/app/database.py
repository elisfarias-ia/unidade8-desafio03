"""Conexão com o banco SQLite e sessão do SQLAlchemy."""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "data" / "gestao_veiculos.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _habilitar_foreign_keys(dbapi_connection, connection_record):
    """O SQLite ignora chaves estrangeiras se o PRAGMA não for ligado."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependência do FastAPI: abre e fecha a sessão por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas() -> None:
    """Cria as tabelas que ainda não existem (sem migrações até o pós-MVP)."""
    from app import models  # noqa: F401  (registra os modelos no metadata)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
