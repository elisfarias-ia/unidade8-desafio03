"""Ponto de entrada da aplicação: API + interface web."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import criar_tabelas, get_db
from app.erros import tratar_erro_validacao
from app.routers import dashboard, deslocamentos, motoristas, veiculos

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Rodagem — Gestão de Veículos e Deslocamentos",
    description=(
        "API de controle de frota: cadastro de veículos e motoristas, "
        "registro de deslocamentos, consulta de histórico e indicadores."
    ),
    version="0.1.0",
)

app.add_exception_handler(RequestValidationError, tratar_erro_validacao)
app.include_router(veiculos.router)
app.include_router(motoristas.router)
app.include_router(deslocamentos.router)
app.include_router(dashboard.router)


@app.get("/api/saude", tags=["Infra"])
def saude(db: Session = Depends(get_db)):
    """Confirma que a API responde e que o banco aceita consultas."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "banco": "ok", "versao": app.version}


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
