"""Ponto de entrada da aplicação: API + interface web.

Sprint 0: apenas o esqueleto executável (verificação de saúde e frontend
estático). As rotas de domínio entram a partir da Sprint 1.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import criar_tabelas, get_db

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Rodagem — Gestão de Veículos e Deslocamentos",
    description="API do sistema de controle de frota (Sprint 0 — esqueleto).",
    version="0.0.1",
)


@app.get("/api/saude", tags=["Infra"])
def saude(db: Session = Depends(get_db)):
    """Confirma que a API responde e que o banco aceita consultas."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "banco": "ok", "versao": app.version}


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
