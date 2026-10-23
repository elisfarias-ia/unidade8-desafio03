# Cria o ambiente virtual e instala as dependencias do backend.
# Uso (na raiz do projeto):  .\scripts\configurar.ps1
# Obs.: texto sem acentos porque o PowerShell 5.1 le .ps1 sem BOM como ANSI.

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

if (-not (Test-Path ".venv")) {
    Write-Host "Criando ambiente virtual em .venv ..."
    python -m venv .venv
}

Write-Host "Instalando dependencias (backend\requirements.txt) ..."
& .\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias." }

Write-Host "Ambiente pronto. Rode .\scripts\iniciar.ps1 para subir a aplicacao."
