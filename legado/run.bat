@echo off
REM Rodagem - inicializacao no Windows
if not exist .venv (
    echo Criando ambiente virtual...
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt --quiet
if not exist gestao_veiculos.db (
    echo Carregando dados de demonstracao...
    python -m app.seed
)
echo.
echo Aplicacao em http://127.0.0.1:8000
uvicorn app.main:app --reload
