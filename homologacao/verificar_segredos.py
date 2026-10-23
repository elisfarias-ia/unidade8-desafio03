"""Procura segredos e dados sensíveis nos arquivos versionados e em TODO o histórico do Git.

Só biblioteca padrão. Uso (na raiz):
    python homologacao/verificar_segredos.py            # repositório atual
    python homologacao/verificar_segredos.py --repo X   # outro repositório

Sai com código 1 se achar algo. O trecho encontrado é mascarado na saída.
Não embute nenhum domínio institucional: qualquer e-mail fora da lista permitida é sinalizado.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PADROES = {
    "chave privada": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY",
    "token GitHub": r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b",
    "chave AWS": r"\bAKIA[0-9A-Z]{16}\b",
    "token Slack": r"\bxox[baprs]-[A-Za-z0-9-]{10,}",
    "chave de API (sk-/AIza)": r"\bsk-[A-Za-z0-9]{20,}\b|\bAIza[0-9A-Za-z_\-]{35}\b",
    "credencial em URL": r"://[^/\s:@]+:[^/\s:@]+@",
    "atribuição de segredo": (
        r"(?i)\b(password|passwd|senha|secret|token|api[_-]?key)\b\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"
    ),
}
PADROES_COMPILADOS = {nome: re.compile(rx) for nome, rx in PADROES.items()}

# o último rótulo do domínio precisa ser alfabético: evita falso positivo em "pacote@18.3.1"
EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,})")
DOMINIOS_PERMITIDOS = {
    "users.noreply.github.com",
    "noreply.github.com",
    "noreply.anthropic.com",
    "example.com",
    "example.org",
}

ARQUIVOS_PROIBIDOS = [
    ("arquivo .env", re.compile(r"(^|/)\.env(\.(?!example$)[^/]*)?$")),
    ("banco de dados", re.compile(r"\.(db|sqlite3?)$", re.I)),
    ("chave/certificado", re.compile(r"\.(pem|key|pfx|p12)$", re.I)),
    ("chave SSH", re.compile(r"(^|/)id_(rsa|ed25519|ecdsa)")),
]


@dataclass
class Achado:
    onde: str  # "arquivo" | "historico" | "autor" | "nome-de-arquivo"
    tipo: str
    local: str
    trecho: str

    def __str__(self) -> str:
        return f"[{self.onde}] {self.tipo} — {self.local} — {self.trecho}"


def mascarar(texto: str) -> str:
    """Nunca imprime caracteres do segredo: só o tamanho (e o domínio, no caso de e-mail/URL)."""
    texto = texto.strip()
    if "@" in texto:
        return f"…@{texto.rsplit('@', 1)[1]} ({len(texto)} caracteres)"
    return f"*** ({len(texto)} caracteres)"


def git(repo: Path, *args: str) -> str:
    saida = subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True).stdout
    return saida.decode("utf-8", errors="replace")


def _linhas_suspeitas(texto: str):
    """Gera (tipo, trecho) para cada padrão e e-mail fora da lista permitida na linha."""
    for tipo, rx in PADROES_COMPILADOS.items():
        for m in rx.finditer(texto):
            yield tipo, m.group(0)
    for m in EMAIL.finditer(texto):
        if m.group(1).lower() not in DOMINIOS_PERMITIDOS:
            yield "e-mail fora da lista permitida", m.group(0)


def varrer_arquivos(repo: Path) -> list[Achado]:
    achados: list[Achado] = []
    nomes = [n for n in git(repo, "ls-files", "-z").split("\0") if n]
    for nome in nomes:
        for tipo, rx in ARQUIVOS_PROIBIDOS:
            if rx.search(nome):
                achados.append(Achado("arquivo", f"{tipo} versionado", nome, nome))
        caminho = repo / nome
        try:
            dados = caminho.read_bytes()
        except OSError:
            continue
        if b"\0" in dados[:8000]:  # binário (imagens etc.)
            continue
        for n, linha in enumerate(dados.decode("utf-8", errors="replace").splitlines(), 1):
            for tipo, trecho in _linhas_suspeitas(linha):
                achados.append(Achado("arquivo", tipo, f"{nome}:{n}", mascarar(trecho)))
    return achados


def varrer_historico(repo: Path) -> list[Achado]:
    achados: list[Achado] = []
    # 1) autores e committers de todos os commits
    for par in sorted(set(git(repo, "log", "--all", "--format=%an <%ae>%n%cn <%ce>").splitlines())):
        for m in EMAIL.finditer(par):
            if m.group(1).lower() not in DOMINIOS_PERMITIDOS:
                achados.append(
                    Achado(
                        "autor",
                        "e-mail de autor fora da lista permitida",
                        par,
                        mascarar(m.group(0)),
                    )
                )
    # 2) nomes de arquivo que já existiram em qualquer commit
    for nome in sorted(set(git(repo, "log", "--all", "--name-only", "--format=").splitlines())):
        for tipo, rx in ARQUIVOS_PROIBIDOS:
            if nome and rx.search(nome):
                achados.append(Achado("nome-de-arquivo", f"{tipo} já commitado", nome, nome))
    # 3) linhas adicionadas em qualquer commit (inclui o que foi removido depois)
    commit = ""
    arquivo = ""
    for linha in git(repo, "log", "--all", "-p", "--no-color", "--format=@@COMMIT %H").splitlines():
        if linha.startswith("@@COMMIT "):
            commit = linha.split()[1][:8]
        elif linha.startswith("+++ b/"):
            arquivo = linha[6:]
        elif linha.startswith("+") and not linha.startswith("+++"):
            for tipo, trecho in _linhas_suspeitas(linha[1:]):
                achados.append(Achado("historico", tipo, f"{arquivo} @ {commit}", mascarar(trecho)))
    return achados


def verificar(repo: Path) -> list[Achado]:
    vistos: set[tuple[str, str, str]] = set()
    unicos: list[Achado] = []
    for a in varrer_arquivos(repo) + varrer_historico(repo):
        chave = (a.tipo, a.local, a.trecho)  # local inclui linha ou commit: nada é escondido
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(a)
    return unicos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    repo = Path(args.repo)
    arquivos = len([n for n in git(repo, "ls-files", "-z").split("\0") if n])
    commits = len(git(repo, "rev-list", "--all").split())
    achados = verificar(repo)
    print(f"Varridos: {arquivos} arquivos versionados e {commits} commits (todo o histórico).")
    if achados:
        print(f"ACHADOS: {len(achados)}")
        for a in achados:
            print("  ", a)
        return 1
    print("Nenhum segredo, banco, chave, .env ou e-mail fora da lista permitida encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
