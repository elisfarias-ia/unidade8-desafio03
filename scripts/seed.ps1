# Carrega dados FICTICIOS de demonstracao. So age com o banco vazio.
# Uso (na raiz do projeto):  .\scripts\seed.ps1

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Ambiente virtual nao encontrado. Rode .\scripts\configurar.ps1 primeiro."
}

$env:PYTHONPATH = "backend"
& .\.venv\Scripts\python.exe -m app.seed
