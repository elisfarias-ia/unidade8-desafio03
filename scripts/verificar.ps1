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

Write-Host "`n== Testes (pytest) =="
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Ambiente virtual ausente. Rode .\scripts\configurar.ps1"
    exit 1
}
& .\.venv\Scripts\python.exe -m pytest -v
exit $LASTEXITCODE
