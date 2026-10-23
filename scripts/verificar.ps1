# Verifica ferramentas e roda a suite de testes.
# Uso (na raiz do projeto):  .\scripts\verificar.ps1

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

function Versao($nome, $comando) {
    try { $v = (& $comando --version 2>&1 | Select-Object -First 1) } catch { $v = "NAO ENCONTRADO" }
    "{0,-8} {1}" -f $nome, $v
}

Write-Host "== Ferramentas =="
Versao "python" "python"
Versao "git" "git"
Versao "node" "node"
"{0,-8} {1}" -f "pwsh", $PSVersionTable.PSVersion

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Ambiente virtual ausente. Rode .\scripts\configurar.ps1"
    exit 1
}

Write-Host "`n== Lint (ruff) =="
& .\.venv\Scripts\python.exe -m ruff check .
$lint = $LASTEXITCODE
& .\.venv\Scripts\python.exe -m ruff format --check .
$formato = $LASTEXITCODE

Write-Host "`n== Testes (pytest) =="
& .\.venv\Scripts\python.exe -m pytest -v
$testes = $LASTEXITCODE

Write-Host "`n== Resumo: lint=$lint formato=$formato testes=$testes (0 = ok) =="
if ($lint -or $formato -or $testes) { exit 1 }
exit 0
