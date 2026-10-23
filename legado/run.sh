#!/usr/bin/env bash
set -e
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --quiet
[ -f gestao_veiculos.db ] || python -m app.seed
echo "Aplicação em http://127.0.0.1:8000"
uvicorn app.main:app --reload
