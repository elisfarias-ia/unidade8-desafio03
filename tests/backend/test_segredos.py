"""Sprint 4 — o detector de segredos precisa realmente detectar (T4-01 a T4-04).

Todos os "segredos" abaixo são falsos e montados em tempo de execução; nenhum literal
parecido com credencial fica no código-fonte.
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "verificar_segredos", RAIZ / "homologacao" / "verificar_segredos.py"
)
vs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs)

FALSO_TOKEN = "ghp_" + "a1B2c3D4" * 5  # 40 caracteres, formato de token do GitHub
FALSA_CHAVE_PRIVADA = "-----BEGIN " + "RSA PRIVATE KEY-----"
EMAIL_INSTITUCIONAL = "fulano" + "@" + "orgao.exemplo.gov.br"
FALSA_URL = "https://" + "usuario" + ":" + "senha-de-teste" + "@" + "servidor.exemplo/x"


def git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=Teste", "-c", "user.email=teste@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    return tmp_path


def commitar(repo, arquivos: dict[str, str], mensagem="c"):
    for nome, conteudo in arquivos.items():
        caminho = repo / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", mensagem)


def tipos(achados):
    return {a.tipo for a in achados}


def test_t4_01_detecta_segredos_plantados_em_arquivos_versionados(repo):
    commitar(
        repo,
        {
            "config.py": f'GITHUB = "{FALSO_TOKEN}"\nsenha = "{"x9" * 6}"\n',
            "chave.txt": FALSA_CHAVE_PRIVADA + "\n",
            "contato.md": f"fale com {EMAIL_INSTITUCIONAL}\n",
            ".env": "A=1\n",
            "dados/frota.db": "x",
            "url.txt": FALSA_URL + "\n",
        },
    )
    achados = vs.verificar(repo)
    encontrados = tipos(achados)
    assert {
        "token GitHub",
        "atribuição de segredo",
        "chave privada",
        "e-mail fora da lista permitida",
        "arquivo .env versionado",
        "banco de dados versionado",
        "credencial em URL",
    } <= encontrados
    # o trecho é sempre mascarado: o token completo nunca aparece na saída
    assert all(FALSO_TOKEN not in str(a) for a in achados)


def test_t4_02_detecta_segredo_que_foi_removido_mas_continua_no_historico(repo):
    commitar(repo, {"a.py": f'T = "{FALSO_TOKEN}"\n'}, "adiciona")
    commitar(repo, {"a.py": "T = None\n"}, "remove")
    assert "token GitHub" not in tipos(vs.varrer_arquivos(repo)), "no arquivo atual já não existe"
    historico = vs.varrer_historico(repo)
    assert "token GitHub" in tipos(historico), "mas o histórico ainda guarda o segredo"


def test_t4_03_detecta_autor_com_email_institucional(repo):
    commitar(repo, {"a.txt": "ok\n"})
    git(
        repo,
        "-c",
        f"user.email={EMAIL_INSTITUCIONAL}",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "x",
        "--author",
        f"Fulano <{EMAIL_INSTITUCIONAL}>",
    )
    achados = vs.varrer_historico(repo)
    assert "e-mail de autor fora da lista permitida" in tipos(achados)


def test_t4_04_repositorio_limpo_nao_gera_alarme_falso(repo):
    commitar(
        repo,
        {
            "README.md": "Use a variável de ambiente PASSWORD e não grave senha em arquivo.\n"
            "Contato: elisfarias-ia@users.noreply.github.com\n",
            ".env.example": "RODAGEM_DB=\n",
            "app.py": "token = obter_token()\nsegredo = None\n",
            "imagem.png": "\0\0binario",
        },
    )
    assert vs.verificar(repo) == []
