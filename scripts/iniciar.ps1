# Sobe API + interface em http://127.0.0.1:8000
# Uso (na raiz do projeto):  .\scripts\iniciar.ps1  [-Porta 8001]

param([int]$Porta = 8000)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Ambiente virtual nao encontrado. Rode .\scripts\configurar.ps1 primeiro."
}

Write-Host "Aplicacao em http://127.0.0.1:$Porta  (Ctrl+C para encerrar)"
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port $Porta
