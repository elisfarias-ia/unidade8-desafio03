# Homologacao ponta a ponta com capturas de tela (ADR-011).
# Sobe o servidor REAL com banco temporario (nao toca nos seus dados), exercita a interface
# num navegador (Playwright) e grava docs\evidencias\*.png e resultado.json.
#
# Uso (na raiz do projeto):  .\scripts\homologar.ps1  [-SemClone]
# Requer rede na 1a vez (baixa o Playwright e o Chromium, ~700 MB, FORA do projeto).
# Ambiente separado em %TEMP%\rodagem-hml (caminho curto: limite de 260 caracteres do Windows).

param([switch]$SemClone)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Ambiente do projeto nao encontrado. Rode .\scripts\configurar.ps1 primeiro."
}

$base = Join-Path $env:TEMP "rodagem-hml"
$venv = Join-Path $base "venv"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $base "pw-browsers"

if (-not (Test-Path "$venv\Scripts\python.exe")) {
    Write-Host "Criando ambiente de homologacao em $venv ..."
    New-Item -ItemType Directory -Force $base | Out-Null
    python -m venv $venv
    & "$venv\Scripts\python.exe" -m pip install --quiet --only-binary=:all: -r homologacao\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o Playwright." }
    Write-Host "Baixando o Chromium (uma vez) ..."
    & "$venv\Scripts\python.exe" -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar o Chromium." }
}

$env:PYTHONIOENCODING = "utf-8"
$argumentos = @("homologacao\homologar.py")
if ($SemClone) { $argumentos += "--sem-clone" }
& "$venv\Scripts\python.exe" @argumentos
exit $LASTEXITCODE
