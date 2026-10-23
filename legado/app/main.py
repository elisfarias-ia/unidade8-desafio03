"""Ponto de entrada da aplicação: API + interface web."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import criar_tabelas
from app.routers import dashboard, deslocamentos, motoristas, veiculos

STATIC_DIR = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def lifespan(_: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Rodagem — Gestão de Veículos e Deslocamentos",
    description=(
        "API do MVP de controle de frota: cadastro de veículos e motoristas, "
        "registro de deslocamentos, consulta de histórico e indicadores."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(veiculos.router)
app.include_router(motoristas.router)
app.include_router(deslocamentos.router)
app.include_router(dashboard.router)


@app.get("/api/saude", tags=["Infra"])
def saude():
    return {"status": "ok", "versao": app.version}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
