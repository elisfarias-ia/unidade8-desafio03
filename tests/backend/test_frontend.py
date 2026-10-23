"""Sprint 2 — verificações estáticas do frontend (IDs em docs/teste.md).

Sem Node no projeto (ADR-006), estes testes substituem um lint de JS para o que
mais quebra na prática: arquivo não servido, import quebrado e convenções.
"""

import re

from app.main import FRONTEND_DIR

JS_DIR = FRONTEND_DIR / "js"


def test_t2_07_arquivos_referenciados_no_index_sao_servidos(client):
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    referencias = re.findall(r'(?:href|src)="(/static/[^"]+)"', html)
    assert referencias, "o index.html deveria referenciar CSS e JS"
    for caminho in referencias:
        assert client.get(caminho).status_code == 200, caminho


def test_t2_08_imports_dos_modulos_existem_e_saem_como_javascript(client):
    modulos = sorted(JS_DIR.glob("*.js"))
    assert {m.name for m in modulos} >= {
        "app.js",
        "api.js",
        "ui.js",
        "painel.js",
        "veiculos.js",
        "motoristas.js",
        "deslocamentos.js",
    }
    for modulo in modulos:
        resposta = client.get(f"/static/js/{modulo.name}")
        assert resposta.status_code == 200
        assert "javascript" in resposta.headers["content-type"], modulo.name
        for alvo in re.findall(r'from\s+"(\./[^"]+)"', modulo.read_text(encoding="utf-8")):
            assert (JS_DIR / alvo).resolve().is_file(), f"{modulo.name} importa {alvo}"


def test_t2_09_nomes_importados_sao_exportados():
    exportados = {}
    for modulo in JS_DIR.glob("*.js"):
        texto = modulo.read_text(encoding="utf-8")
        exportados[modulo.name] = set(
            re.findall(r"export\s+(?:async\s+)?(?:function|const|class)\s+(\w+)", texto)
        )
    for modulo in JS_DIR.glob("*.js"):
        texto = modulo.read_text(encoding="utf-8")
        for nomes, alvo in re.findall(r'import\s+\{([^}]+)\}\s+from\s+"\./([^"]+)"', texto):
            for nome in (n.strip() for n in nomes.split(",") if n.strip()):
                assert nome in exportados[alvo], f"{modulo.name}: '{nome}' não existe em {alvo}"


def test_t2_10_cores_so_nas_variaveis_do_root():
    css = (FRONTEND_DIR / "css" / "styles.css").read_text(encoding="utf-8")
    fim_root = css.index("}", css.index(":root"))
    fora_do_root = css[fim_root:]
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", fora_do_root)
    assert not re.findall(r"\brgba?\(", fora_do_root)


def test_t2_11_navegacao_cobre_todas_as_telas():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert 'lang="pt-BR"' in html
    for tela in ("painel", "veiculos", "motoristas", "deslocamentos"):
        assert f'href="#{tela}"' in html
        assert f'id="tela-{tela}"' in html


def test_t2_12_campos_de_formulario_tem_rotulo():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    ids = re.findall(r'<(?:input|select|textarea)[^>]*\bid="([^"]+)"', html)
    rotulos = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', html))
    sem_rotulo = [i for i in ids if i not in rotulos]
    assert not sem_rotulo, f"campos sem <label for>: {sem_rotulo}"
