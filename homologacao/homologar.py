"""Homologação ponta a ponta do Rodagem (ADR-011).

Sobe o servidor REAL com um banco SQLite temporário (RODAGEM_DB) — nunca toca em
backend/data — e exercita a interface num navegador de verdade (Playwright).

Uso (ver scripts/homologar.ps1):
    python homologacao/homologar.py --python-projeto .venv/Scripts/python.exe

Saídas: capturas em docs/evidencias/*.png e docs/evidencias/resultado.json.
Tudo que não roda é registrado como NAO_TESTADO; nada é simulado.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, expect, sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
PREFIXO = "HOMOLOG"  # tudo que a homologação cria é fictício e identificado


# --------------------------------------------------------------------------- #
# Registro de verificações
# --------------------------------------------------------------------------- #
class Registro:
    def __init__(self):
        self.itens: list[dict] = []
        self.capturas: list[dict] = []

    def verificar(self, id_: str, descricao: str, condicao: bool, detalhe: str = "") -> bool:
        self.itens.append(
            {
                "id": id_,
                "descricao": descricao,
                "resultado": "OK" if condicao else "FALHA",
                "detalhe": detalhe,
            }
        )
        marca = "OK   " if condicao else "FALHA"
        print(
            f"[{marca}] {id_} {descricao}" + (f"  -> {detalhe}" if detalhe and not condicao else "")
        )
        return bool(condicao)

    def nao_testado(self, id_: str, descricao: str, motivo: str) -> None:
        self.itens.append(
            {"id": id_, "descricao": descricao, "resultado": "NAO_TESTADO", "detalhe": motivo}
        )
        print(f"[NAO TESTADO] {id_} {descricao}  -> {motivo}")


# --------------------------------------------------------------------------- #
# Servidor real com banco temporário
# --------------------------------------------------------------------------- #
class Servidor:
    def __init__(self, python: Path, porta: int, banco: Path, log: Path, raiz: Path = RAIZ):
        self.python, self.porta, self.banco, self.log, self.raiz = python, porta, banco, log, raiz
        self.proc: subprocess.Popen | None = None
        self.base = f"http://127.0.0.1:{porta}"

    def iniciar(self) -> None:
        env = {**os.environ, "RODAGEM_DB": str(self.banco), "PYTHONUTF8": "1"}
        self.proc = subprocess.Popen(
            [
                str(self.python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--app-dir",
                "backend",
                "--port",
                str(self.porta),
            ],
            cwd=self.raiz,
            env=env,
            stdout=open(self.log, "ab"),
            stderr=subprocess.STDOUT,
        )
        for _ in range(100):
            try:
                if self.api("/api/saude")["status"] == "ok":
                    return
            except OSError:
                time.sleep(0.2)
        raise RuntimeError(f"Servidor não respondeu. Veja {self.log}")

    def parar(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def api(self, caminho: str):
        with urllib.request.urlopen(self.base + caminho, timeout=10) as r:
            return json.loads(r.read())


def semear(python: Path, banco: Path, raiz: Path = RAIZ) -> str:
    env = {
        **os.environ,
        "RODAGEM_DB": str(banco),
        "PYTHONPATH": str(raiz / "backend"),
        "PYTHONUTF8": "1",
    }
    saida = subprocess.run(
        [str(python), "-m", "app.seed"],
        cwd=raiz,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return saida.stdout.strip() or saida.stderr.strip()


# --------------------------------------------------------------------------- #
# Cálculo independente dos indicadores: SQL direto no arquivo SQLite
# --------------------------------------------------------------------------- #
def br(n: float, casas: int = 1) -> str:
    texto = f"{n:,.{casas}f}".rstrip("0").rstrip(".") if casas else f"{int(n):,}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def pl(n: int, um: str, varios: str) -> str:
    return f"{br(n, 0)} {um if n == 1 else varios}"


def esperado_do_sql(banco: Path, ini: date, fim: date) -> dict[str, str]:
    c = sqlite3.connect(banco)
    try:
        um = lambda sql, *a: c.execute(sql, a).fetchone()[0]  # noqa: E731
        per = "data_saida >= ? AND data_saida <= ?"
        a = (str(ini), str(fim))
        veic = {
            s: um("select count(*) from veiculos where status=?", s)
            for s in ("disponivel", "em_viagem", "manutencao", "inativo")
        }
        total_v = um("select count(*) from veiculos")
        n = {
            s: um(f"select count(*) from deslocamentos where {per} and status=?", *a, s)
            for s in ("previsto", "em_andamento", "realizado", "cancelado")
        }
        total = um(f"select count(*) from deslocamentos where {per}", *a)
        base = n["previsto"] + n["realizado"]
        taxa = round(n["realizado"] / base * 100, 1) if base else 0.0
        km, com_km = c.execute(
            f"select coalesce(sum(km_final-km_inicial),0), count(*) from deslocamentos where {per} "
            "and status='realizado' and km_final is not null and km_inicial is not null",
            a,
        ).fetchone()
        media = round(km / com_km, 1) if com_km else 0.0
        usados = um(
            f"select count(distinct veiculo_id) from deslocamentos where {per} "
            "and status<>'cancelado'",
            *a,
        )
        uso = round(usados / total_v * 100, 1) if total_v else 0.0
    finally:
        c.close()
    return {
        "ind-veiculos": br(total_v, 0),
        "ind-veiculos-d": f"{pl(veic['disponivel'], 'disponível', 'disponíveis')} · {br(veic['em_viagem'], 0)} em viagem · "
        f"{br(veic['manutencao'], 0)} em manutenção · {pl(veic['inativo'], 'inativo', 'inativos')}",
        "ind-desl": br(total, 0),
        "ind-desl-d": f"{pl(n['previsto'], 'previsto', 'previstos')} · {br(n['em_andamento'], 0)} em andamento · "
        f"{pl(n['realizado'], 'realizado', 'realizados')} · {pl(n['cancelado'], 'cancelado', 'cancelados')}",
        "ind-viag": f"{br(n['previsto'], 0)} × {br(n['realizado'], 0)}",
        "ind-taxa": f"{br(taxa)}%",
        "ind-km": f"{br(km)} km",
        "ind-media": f"{br(media)} km",
        "ind-uso": f"{br(uso)}%",
    }


def ler_painel(page: Page) -> dict[str, str]:
    ids = [
        "ind-veiculos",
        "ind-veiculos-d",
        "ind-desl",
        "ind-desl-d",
        "ind-viag",
        "ind-taxa",
        "ind-km",
        "ind-media",
        "ind-uso",
    ]
    return {i: page.locator(f"#{i}").inner_text().strip() for i in ids}


def recarregar_painel(page: Page) -> None:
    page.click("#painel-padrao")
    aquietar(page)
    expect(page.locator("#painel-periodo-texto")).to_contain_text("Período:")


def painel_confere(
    page: Page,
    banco: Path,
    reg: Registro,
    id_: str,
    descricao: str,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Compara a tela com o SQL independente (e com valores esperados informados à mão)."""
    hoje = date.today()
    esperado = esperado_do_sql(banco, hoje - timedelta(days=90), hoje + timedelta(days=30))
    if extra:
        esperado = {**esperado, **extra}  # valores calculados à mão têm precedência
    recarregar_painel(page)
    atual: dict[str, str] = {}
    for _ in range(20):
        atual = ler_painel(page)
        if atual == esperado:
            break
        time.sleep(0.25)
    diffs = {k: (atual[k], esperado[k]) for k in esperado if atual.get(k) != esperado[k]}
    reg.verificar(id_, descricao, not diffs, f"diferenças (tela, esperado): {diffs}")
    return atual


# --------------------------------------------------------------------------- #
# Ajudantes de interface
# --------------------------------------------------------------------------- #
_PENDENTES: dict[int, int] = {}


def rastrear(page: Page) -> None:
    """Conta requisições em andamento. O 'networkidle' do Playwright resolve na hora se a
    página já o atingiu uma vez, então não serve para esperar o efeito de uma ação."""
    chave = id(page)
    _PENDENTES[chave] = 0

    def mais(_):
        _PENDENTES[chave] += 1

    def menos(_):
        _PENDENTES[chave] -= 1

    page.on("request", mais)
    page.on("requestfinished", menos)
    page.on("requestfailed", menos)


def aquietar(page: Page, estavel_ms: int = 300, limite_s: float = 10) -> None:
    """Espera não haver requisições em andamento por 'estavel_ms' seguidos."""
    chave = id(page)
    limite = time.time() + limite_s
    quieto_desde = None
    while time.time() < limite:
        if _PENDENTES.get(chave, 0) <= 0:
            quieto_desde = quieto_desde or time.time()
            if time.time() - quieto_desde >= estavel_ms / 1000:
                return
        else:
            quieto_desde = None
        page.wait_for_timeout(40)
    raise TimeoutError("a página não ficou sem requisições em andamento")


class Monitor:
    """Registra respostas HTTP, erros de console e exceções de página."""

    def __init__(self):
        self.respostas: list[tuple[int, str, str]] = []
        self.console: list[str] = []
        self.excecoes: list[str] = []

    def ligar(self, page: Page) -> None:
        rastrear(page)
        page.on(
            "response",
            lambda r: self.respostas.append((r.status, r.request.method, urlparse(r.url).path)),
        )
        page.on("console", lambda m: self.console.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: self.excecoes.append(str(e)))


class Capturas:
    def __init__(self, pasta: Path, reg: Registro):
        self.pasta, self.reg = pasta, reg
        pasta.mkdir(parents=True, exist_ok=True)

    def tirar(
        self,
        page: Page,
        nome: str,
        descricao: str,
        pagina_inteira: bool = False,
        com_avisos: bool = False,
    ) -> None:
        arquivo = self.pasta / f"{nome}.png"
        estilo = None
        if not com_avisos:  # os avisos passageiros cobririam o conteúdo
            estilo = page.add_style_tag(content="#avisos { visibility: hidden !important; }")
        page.screenshot(path=str(arquivo), full_page=pagina_inteira)
        if estilo:
            estilo.evaluate("e => e.remove()")
        self.reg.capturas.append({"arquivo": f"{nome}.png", "descricao": descricao})


def abrir(page: Page, base: str, tela: str) -> None:
    page.goto(f"{base}/#{tela}")
    expect(page.locator(f"#tela-{tela}")).to_be_visible()
    aquietar(page)


def escolher_por_prefixo(page: Page, seletor: str, prefixo: str) -> None:
    valor = page.evaluate(
        "([s, p]) => [...document.querySelector(s).options].find(o => o.textContent.startsWith(p))?.value",
        [seletor, prefixo],
    )
    assert valor, f"opção '{prefixo}' não encontrada em {seletor}"
    page.select_option(seletor, value=valor)


def enviar(page: Page, form: str) -> None:
    page.click(f"{form} button[type=submit]")


def confirmar_exclusao(page: Page) -> None:
    expect(page.locator("#dialogo-confirmar")).to_be_visible()
    page.click("#dialogo-confirmar button[value=sim]")
    expect(page.locator("#dialogo-confirmar")).not_to_be_visible()
    aquietar(page)


def texto_alerta(page: Page, form: str) -> str:
    return page.locator(f"{form} [data-alerta]").inner_text().strip()


# --------------------------------------------------------------------------- #
# Cenários
# --------------------------------------------------------------------------- #
def cenario_lista_vazia(page, base, srv, reg, cap):
    api = srv.api
    reg.verificar(
        "LV-00",
        "Banco temporário realmente vazio (API)",
        api("/api/veiculos") == []
        and api("/api/motoristas") == []
        and api("/api/deslocamentos") == [],
    )
    abrir(page, base, "painel")
    expect(page.locator("#painel-vazio")).to_be_visible()
    painel = ler_painel(page)
    reg.verificar(
        "LV-01",
        "Painel sem dados: zeros, sem NaN/undefined e aviso de estado vazio",
        painel["ind-desl"] == "0"
        and painel["ind-viag"] == "0 × 0"
        and painel["ind-taxa"] == "0%"
        and painel["ind-uso"] == "0%"
        and not any(re.search(r"NaN|undefined|Infinity", v) for v in painel.values()),
        str(painel),
    )
    reg.verificar(
        "LV-02",
        "Painel mostra 'Nenhuma saída prevista' na tabela de próximas saídas",
        "Nenhuma saída prevista" in page.locator("#proximas-linhas").inner_text(),
    )
    cap.tirar(
        page, "01-painel-vazio-desktop", "Painel com banco vazio: zeros e aviso de estado vazio"
    )

    for tela, rotulo, contagem in [
        ("veiculos", "veículo", "veiculos"),
        ("motoristas", "motorista", "motoristas"),
        ("deslocamentos", "deslocamento", "deslocamentos"),
    ]:
        abrir(page, base, tela)
        expect(page.locator(f"#{contagem}-contagem")).to_contain_text("0 ")
        texto = page.locator(f"#{contagem}-linhas").inner_text()
        reg.verificar(
            f"LV-0{['veiculos', 'motoristas', 'deslocamentos'].index(tela) + 3}",
            f"Lista de {tela} vazia mostra mensagem (sem linhas em branco)",
            f"Nenhum {rotulo} encontrado" in texto,
            texto,
        )
        cap.tirar(
            page,
            f"0{['veiculos', 'motoristas', 'deslocamentos'].index(tela) + 2}-{tela}-vazio-desktop",
            f"Tela de {tela} com banco vazio",
        )

    # sem veículos/motoristas cadastrados, o formulário de deslocamento recusa o envio
    page.click("#deslocamentos-novo")
    enviar(page, "#form-deslocamento")
    expect(page.locator("#form-deslocamento [data-alerta]")).to_be_visible()
    alerta = texto_alerta(page, "#form-deslocamento")
    reg.verificar(
        "LV-06",
        "Registrar deslocamento sem cadastros: 422 em português com campo marcado",
        "obrigatório" in alerta.lower()
        and page.locator("#form-deslocamento [aria-invalid=true]").count() >= 3,
        alerta,
    )
    cap.tirar(
        page,
        "05-deslocamento-sem-cadastros-422",
        "Formulário de deslocamento sem veículos/motoristas: erros de validação nos campos",
    )
    page.click("#form-deslocamento [data-fechar]")


def cenario_crud(page, base, srv, reg, cap, dados):
    api = srv.api
    hoje = date.today()
    v1, v2 = dados["veiculos"]
    m1, m2 = dados["motoristas"]

    # ----- Veículos: criar / ler / editar / excluir -----
    abrir(page, base, "veiculos")
    page.click("#veiculos-novo")
    page.fill("#veiculo-placa", "AB-12")
    enviar(page, "#form-veiculo")
    expect(page.locator("#form-veiculo [data-alerta]")).to_be_visible()
    reg.verificar(
        "CA01-c",
        "Veículo: placa inválida → 422 com a mensagem no campo placa",
        "Placa inválida" in page.locator("#veiculo-placa-erro").inner_text()
        and api("/api/veiculos") == [],
        texto_alerta(page, "#form-veiculo"),
    )
    cap.tirar(
        page,
        "06-veiculo-validacao-422",
        "Cadastro de veículo com placa inválida e campos obrigatórios vazios",
    )

    for v in (v1, v2):
        page.fill("#veiculo-placa", v["placa"].lower())  # minúsculas: o sistema normaliza
        page.fill("#veiculo-ano", str(v["ano"]))
        page.fill("#veiculo-marca", v["marca"])
        page.fill("#veiculo-modelo", v["modelo"])
        page.fill("#veiculo-km", str(v["km"]))
        enviar(page, "#form-veiculo")
        expect(page.locator("#dialogo-veiculo")).not_to_be_visible()
        aquietar(page)
        if v is not v2:
            page.click("#veiculos-novo")
    lista = api("/api/veiculos")
    reg.verificar(
        "CRUD-V1",
        "Veículo: criar 2 pela tela → aparecem na API e na tabela (placa normalizada, 'Disponível')",
        sorted(x["placa"] for x in lista) == sorted([v1["placa"], v2["placa"]])
        and all(x["status"] == "disponivel" for x in lista)
        and v1["placa"] in page.locator("#veiculos-linhas").inner_text(),
        str([x["placa"] for x in lista]),
    )

    page.click("#veiculos-novo")
    page.fill("#veiculo-placa", v1["placa"])
    page.fill("#veiculo-ano", "2020")
    page.fill("#veiculo-marca", "Outra")
    page.fill("#veiculo-modelo", "Outro")
    enviar(page, "#form-veiculo")
    expect(page.locator("#form-veiculo [data-alerta]")).to_contain_text("Já existe um veículo")
    reg.verificar(
        "CA01-b",
        "Veículo: placa duplicada → 409 com mensagem e diálogo aberto",
        page.locator("#dialogo-veiculo").is_visible() and len(api("/api/veiculos")) == 2,
    )
    cap.tirar(
        page, "07-veiculo-placa-duplicada-409", "Cadastro de veículo com placa já existente (409)"
    )
    page.click("#form-veiculo [data-fechar]")

    page.fill("#veiculos-busca", v2["placa"][:4])
    expect(page.locator("#veiculos-contagem")).to_contain_text("1 veículo")
    reg.verificar(
        "CRUD-V2",
        "Veículo: busca filtra a tabela",
        v2["placa"] in page.locator("#veiculos-linhas").inner_text()
        and v1["placa"] not in page.locator("#veiculos-linhas").inner_text(),
    )
    page.fill("#veiculos-busca", "")
    expect(page.locator("#veiculos-contagem")).to_contain_text("2 veículos")

    # Corrida de respostas: a busca antiga (lenta) não pode sobrescrever a mais nova.
    page.evaluate(
        """() => {
            const original = window.fetch.bind(window);
            window.__fetchOriginal = original;
            window.fetch = (u, o) => String(u).includes('busca=HOM1')
                ? new Promise((r) => setTimeout(r, 1500)).then(() => original(u, o))
                : original(u, o);
        }"""
    )
    page.fill("#veiculos-busca", v1["placa"][:4])
    page.wait_for_timeout(450)  # a 1ª busca já saiu (e está presa por 1,5 s)
    page.fill("#veiculos-busca", v2["placa"][:4])
    expect(page.locator("#veiculos-contagem")).to_contain_text("1 veículo")
    page.wait_for_timeout(2200)  # agora a resposta lenta da 1ª busca chega
    texto_corrida = page.locator("#veiculos-linhas").inner_text()
    reg.verificar(
        "RACE-1",
        "Respostas fora de ordem: a busca antiga e lenta não sobrescreve a mais nova",
        v2["placa"] in texto_corrida and v1["placa"] not in texto_corrida,
        texto_corrida,
    )
    page.evaluate("() => { window.fetch = window.__fetchOriginal; }")
    page.fill("#veiculos-busca", "")
    expect(page.locator("#veiculos-contagem")).to_contain_text("2 veículos")

    page.get_by_role("button", name=f"Editar veículo {v2['placa']}").click()
    expect(page.locator("#dialogo-veiculo-titulo")).to_contain_text(v2["placa"])
    cap.tirar(page, "08-veiculo-edicao", "Edição de veículo com os dados atuais preenchidos")
    page.fill("#veiculo-modelo", "Modelo Editado")
    page.fill("#veiculo-cor", "Verde")
    enviar(page, "#form-veiculo")
    expect(page.locator("#dialogo-veiculo")).not_to_be_visible()
    aquietar(page)
    editado = next(x for x in api("/api/veiculos") if x["placa"] == v2["placa"])
    reg.verificar(
        "CRUD-V3",
        "Veículo: editar modelo e cor → gravado; outros campos intactos",
        editado["modelo"] == "Modelo Editado"
        and editado["cor"] == "Verde"
        and editado["marca"] == v2["marca"]
        and editado["km_atual"] == v2["km"],
        str(editado),
    )

    # ----- Motoristas -----
    abrir(page, base, "motoristas")
    page.click("#motoristas-novo")
    page.fill("#motorista-nome", m1["nome"])
    page.fill("#motorista-cnh", "123")
    enviar(page, "#form-motorista")
    expect(page.locator("#motorista-cnh-erro")).to_be_visible()
    reg.verificar(
        "CRUD-M0",
        "Motorista: CNH com 3 dígitos → 422 no campo cnh",
        "11 dígitos" in page.locator("#motorista-cnh-erro").inner_text()
        and api("/api/motoristas") == [],
    )
    cap.tirar(page, "09-motorista-validacao-cnh", "Cadastro de motorista com CNH inválida")
    for m in (m1, m2):
        page.fill("#motorista-nome", m["nome"])
        page.fill("#motorista-cnh", m["cnh_mascarada"])
        page.fill("#motorista-setor", m["setor"])
        enviar(page, "#form-motorista")
        expect(page.locator("#dialogo-motorista")).not_to_be_visible()
        aquietar(page)
        if m is not m2:
            page.click("#motoristas-novo")
    lm = api("/api/motoristas")
    reg.verificar(
        "CRUD-M1",
        "Motorista: criar 2 pela tela → CNH normalizada para 11 dígitos",
        sorted(x["cnh"] for x in lm) == sorted([m1["cnh"], m2["cnh"]]),
        str([x["cnh"] for x in lm]),
    )
    page.get_by_role("button", name=f"Editar {m2['nome']}").click()
    page.uncheck("#motorista-ativo")
    page.fill("#motorista-telefone", "(00) 90000-0099")
    enviar(page, "#form-motorista")
    expect(page.locator("#dialogo-motorista")).not_to_be_visible()
    aquietar(page)
    m2_api = next(x for x in api("/api/motoristas") if x["cnh"] == m2["cnh"])
    reg.verificar(
        "CRUD-M2",
        "Motorista: editar (desativar + telefone) → API e selo 'Inativo' na tabela",
        m2_api["ativo"] is False
        and m2_api["telefone"] == "(00) 90000-0099"
        and "Inativo" in page.locator("#motoristas-linhas").inner_text(),
    )
    cap.tirar(page, "10-motoristas-lista", "Lista de motoristas: um ativo e um inativo")
    page.check("#motoristas-ativos")
    expect(page.locator("#motoristas-contagem")).to_contain_text("1 motorista")
    reg.verificar(
        "CRUD-M3",
        "Motorista: filtro 'Somente ativos' esconde o inativo",
        m2["nome"] not in page.locator("#motoristas-linhas").inner_text(),
    )
    page.uncheck("#motoristas-ativos")

    # ----- Deslocamentos -----
    d1_saida, d1_ret = hoje, hoje + timedelta(days=1)
    d2_saida, d2_ret = hoje + timedelta(days=3), hoje + timedelta(days=4)
    abrir(page, base, "deslocamentos")
    page.click("#deslocamentos-novo")
    cap.tirar(page, "11-deslocamento-formulario", "Formulário de registro de deslocamento")
    escolher_por_prefixo(page, "#desl-veiculo", v1["placa"])
    escolher_por_prefixo(page, "#desl-motorista", m1["nome"])
    page.fill("#desl-destino", "Destino Norte")
    page.fill("#desl-saida", d1_saida.isoformat())
    page.fill("#desl-retorno", (d1_saida - timedelta(days=1)).isoformat())
    page.select_option("#desl-finalidade", "entrega")
    enviar(page, "#form-deslocamento")
    expect(page.locator("#form-deslocamento [data-alerta]")).to_contain_text("anterior")
    reg.verificar(
        "CA02-b",
        "Deslocamento: retorno antes da saída → 422 na tela",
        api("/api/deslocamentos") == [],
        texto_alerta(page, "#form-deslocamento"),
    )
    page.fill("#desl-retorno", d1_ret.isoformat())
    page.select_option("#desl-status", "em_andamento")
    enviar(page, "#form-deslocamento")
    expect(page.locator("#dialogo-deslocamento")).not_to_be_visible()
    aquietar(page)
    d1 = api("/api/deslocamentos")[0]
    reg.verificar(
        "CA02-a",
        "Deslocamento: registrar pela tela → 201; histórico traz veículo e motorista; km inicial herdado",
        d1["veiculo"]["placa"] == v1["placa"]
        and d1["motorista"]["nome"] == m1["nome"]
        and d1["km_inicial"] == v1["km"]
        and d1["status"] == "em_andamento",
        str(d1),
    )
    reg.verificar(
        "CRUD-D1",
        "Veículo do deslocamento em andamento passa a 'em viagem'",
        next(x for x in api("/api/veiculos") if x["placa"] == v1["placa"])["status"] == "em_viagem",
    )

    page.click("#deslocamentos-novo")
    escolher_por_prefixo(page, "#desl-veiculo", v1["placa"])
    escolher_por_prefixo(page, "#desl-motorista", m1["nome"])
    page.fill("#desl-destino", "Destino Conflito")
    page.fill("#desl-saida", d1_saida.isoformat())
    page.select_option("#desl-finalidade", "outros")
    enviar(page, "#form-deslocamento")
    expect(page.locator("#form-deslocamento [data-alerta]")).to_contain_text("Conflito de agenda")
    reg.verificar(
        "CA02-c",
        "Deslocamento: mesmo veículo no mesmo período → 409 citando o conflito",
        f"#{d1['id']}" in texto_alerta(page, "#form-deslocamento")
        and len(api("/api/deslocamentos")) == 1,
        texto_alerta(page, "#form-deslocamento"),
    )
    cap.tirar(
        page,
        "12-deslocamento-conflito-409",
        "Registro de deslocamento com conflito de agenda (409)",
    )
    escolher_por_prefixo(page, "#desl-veiculo", v2["placa"])
    page.fill("#desl-destino", "Destino Sul")
    page.fill("#desl-saida", d2_saida.isoformat())
    page.fill("#desl-retorno", d2_ret.isoformat())
    page.select_option("#desl-finalidade", "operacional")
    page.select_option("#desl-status", "previsto")
    enviar(page, "#form-deslocamento")
    expect(page.locator("#dialogo-deslocamento")).not_to_be_visible()
    aquietar(page)
    reg.verificar(
        "CRUD-D2",
        "Deslocamento: segundo registro (veículo 2, previsto) criado pela tela",
        len(api("/api/deslocamentos")) == 2,
    )

    page.fill("#filtro-destino", "Norte")
    expect(page.locator("#deslocamentos-contagem")).to_contain_text("1 deslocamento")
    reg.verificar(
        "CA02-d",
        "Deslocamento: filtro por destino retorna só os correspondentes",
        "Destino Norte" in page.locator("#deslocamentos-linhas").inner_text()
        and "Destino Sul" not in page.locator("#deslocamentos-linhas").inner_text(),
    )
    page.fill("#filtro-destino", "")
    expect(page.locator("#deslocamentos-contagem")).to_contain_text("2 deslocamentos")

    pedidos_filtro: list[str] = []

    def contar_filtro(r):
        if "/api/deslocamentos?" in r.url and "finalidade=entrega" in r.url:
            pedidos_filtro.append(r.url)

    page.on("request", contar_filtro)
    page.select_option("#filtro-finalidade", "entrega")
    page.wait_for_timeout(900)
    page.remove_listener("request", contar_filtro)
    reg.verificar(
        "BUSCA-1",
        "Filtro de deslocamentos: escolher uma opção dispara uma única busca (antes eram duas)",
        len(pedidos_filtro) == 1,
        f"{len(pedidos_filtro)} requisições",
    )
    page.select_option("#filtro-finalidade", "")
    expect(page.locator("#deslocamentos-contagem")).to_contain_text("2 deslocamentos")
    cap.tirar(
        page, "13-deslocamentos-lista", "Histórico de deslocamentos com os dois registros", True
    )

    page.get_by_role("button", name="Editar deslocamento para Destino Sul").click()
    page.fill("#desl-obs", "editado na homologação")
    enviar(page, "#form-deslocamento")
    expect(page.locator("#dialogo-deslocamento")).not_to_be_visible()
    aquietar(page)
    d2 = next(x for x in api("/api/deslocamentos") if x["destino"] == "Destino Sul")
    reg.verificar(
        "CRUD-D3",
        "Deslocamento: editar observação → gravada",
        d2["observacao"] == "editado na homologação",
    )
    return {"d1": d1, "d2": d2, "v1": v1, "v2": v2, "m1": m1, "m2": m2}


def cenario_indicadores(page, base, srv, reg, cap, ctx):
    banco = srv.banco
    v1, d1 = ctx["v1"], ctx["d1"]
    abrir(page, base, "painel")
    # valores calculados à mão (precedem o SQL): 2 veículos, 1 em andamento + 1 prevista
    painel_confere(
        page,
        banco,
        reg,
        "IND-1",
        "Painel após criar 2 deslocamentos: bate com o SQL independente e com o cálculo manual",
        {
            "ind-veiculos": "2",
            "ind-desl": "2",
            "ind-viag": "1 × 0",
            "ind-taxa": "0%",
            "ind-km": "0 km",
            "ind-uso": "100%",
            "ind-veiculos-d": "1 disponível · 1 em viagem · 0 em manutenção · 0 inativos",
            "ind-desl-d": "1 previsto · 1 em andamento · 0 realizados · 0 cancelados",
        },
    )
    cap.tirar(
        page,
        "14-painel-apos-criar",
        "Painel após criar um deslocamento em andamento e um previsto",
        True,
    )

    abrir(page, base, "veiculos")
    page.get_by_role("button", name=f"Editar veículo {v1['placa']}").click()
    page.select_option("#veiculo-status", "disponivel")
    enviar(page, "#form-veiculo")
    aquietar(page)  # sem 'expect': se o defeito voltar, queremos uma FALHA registrada, não um crash
    situacao_v1 = next(x for x in srv.api("/api/veiculos") if x["placa"] == v1["placa"])["status"]
    alerta_v1 = page.locator("#form-veiculo [data-alerta]").text_content() or ""
    reg.verificar(
        "REV-1",
        "Veículo com viagem em andamento não pode virar 'Disponível' pela tela (409); situação mantida",
        situacao_v1 == "em_viagem" and "viagem em andamento" in alerta_v1,
        f"situação={situacao_v1}; alerta={alerta_v1!r}",
    )
    cap.tirar(
        page,
        "14b-veiculo-situacao-bloqueada-409",
        "Tentativa de tornar 'Disponível' um veículo com viagem em andamento (409)",
    )
    page.click("#form-veiculo [data-fechar]")

    abrir(page, base, "deslocamentos")
    page.get_by_role("button", name="Concluir viagem para Destino Norte").click()
    page.fill("#concluir-km", str(v1["km"] + 120))
    page.fill("#concluir-data", d1["data_retorno"])
    cap.tirar(page, "15-deslocamento-concluir", "Diálogo de conclusão de viagem com km final")
    page.fill("#concluir-km", str(v1["km"] - 5))
    enviar(page, "#form-concluir")
    expect(page.locator("#form-concluir [data-alerta]")).to_contain_text("não pode ser menor")
    reg.verificar(
        "CRUD-D4",
        "Concluir viagem com km final menor que o inicial → 422 na tela",
        next(x for x in srv.api("/api/deslocamentos") if x["id"] == d1["id"])["status"]
        == "em_andamento",
    )
    page.fill("#concluir-km", str(v1["km"] + 120))
    enviar(page, "#form-concluir")
    expect(page.locator("#dialogo-concluir")).not_to_be_visible()
    aquietar(page)
    veic = next(x for x in srv.api("/api/veiculos") if x["placa"] == v1["placa"])
    reg.verificar(
        "CRUD-D5",
        "Concluir viagem → realizada, 120 km, veículo disponível e km atualizado",
        veic["status"] == "disponivel" and veic["km_atual"] == v1["km"] + 120,
        f"veículo: {veic['status']} km={veic['km_atual']}",
    )
    abrir(page, base, "painel")
    painel_confere(
        page,
        banco,
        reg,
        "IND-2",
        "Painel após concluir: 1 × 1, 120 km, taxa 50%, nenhum veículo em viagem",
        {
            "ind-viag": "1 × 1",
            "ind-taxa": "50%",
            "ind-km": "120 km",
            "ind-media": "120 km",
            "ind-veiculos-d": "2 disponíveis · 0 em viagem · 0 em manutenção · 0 inativos",
        },
    )
    cap.tirar(
        page,
        "16-painel-apos-concluir",
        "Painel após concluir a viagem: previstas × realizadas e km atualizados",
        True,
    )

    abrir(page, base, "deslocamentos")
    page.get_by_role("button", name="Excluir deslocamento para Destino Sul").click()
    cap.tirar(page, "17-confirmacao-exclusao", "Diálogo de confirmação antes de excluir")
    confirmar_exclusao(page)
    expect(page.locator("#deslocamentos-linhas")).not_to_contain_text("Destino Sul")
    reg.verificar(
        "CRUD-D6",
        "Deslocamento: excluir pela tela → some da tabela e da API",
        len(srv.api("/api/deslocamentos")) == 1
        and "Destino Sul" not in page.locator("#deslocamentos-linhas").inner_text(),
    )
    abrir(page, base, "painel")
    painel_confere(
        page,
        banco,
        reg,
        "IND-3",
        "Painel após excluir a viagem prevista: 0 × 1, taxa 100%, utilização 50%",
        {"ind-desl": "1", "ind-viag": "0 × 1", "ind-taxa": "100%", "ind-uso": "50%"},
    )
    cap.tirar(page, "18-painel-apos-excluir", "Painel após excluir a viagem prevista", True)

    # período: um recorte sem dados zera os indicadores (e volta ao padrão)
    page.fill("#painel-inicio", "2031-01-01")
    page.fill("#painel-fim", "2031-01-31")
    page.click("#painel-periodo button[type=submit]")
    aquietar(page)
    expect(page.locator("#painel-vazio")).to_be_visible()
    reg.verificar(
        "IND-4",
        "Painel: período sem dados → zeros e estado vazio; veículos continuam contados",
        ler_painel(page)["ind-desl"] == "0" and ler_painel(page)["ind-veiculos"] == "2",
    )
    recarregar_painel(page)

    abrir(page, base, "veiculos")
    with page.expect_request(lambda r: "/api/dashboard/indicadores" in r.url) as pedido:
        abrir(page, base, "painel")
    reg.verificar(
        "IND-5",
        "Painel: voltar à tela sem ter escolhido datas usa o período padrão da API (requisição sem datas)",
        "data_inicio" not in pedido.value.url,
        pedido.value.url,
    )
    page.fill("#painel-inicio", "2026-10-01")
    page.fill("#painel-fim", "2026-10-31")
    with page.expect_request(lambda r: "/api/dashboard/indicadores" in r.url) as pedido2:
        page.click("#painel-periodo button[type=submit]")
    reg.verificar(
        "IND-6",
        "Painel: as datas escolhidas pelo usuário são enviadas à API",
        "data_inicio=2026-10-01" in pedido2.value.url
        and "data_fim=2026-10-31" in pedido2.value.url,
        pedido2.value.url,
    )
    recarregar_painel(page)

    # exclusão com histórico é bloqueada (regra 7)
    abrir(page, base, "veiculos")
    page.get_by_role("button", name=f"Excluir veículo {v1['placa']}").click()
    confirmar_exclusao(page)
    expect(page.locator("#avisos")).to_contain_text("não pode ser excluído")
    reg.verificar(
        "CRUD-V4",
        "Excluir veículo com histórico → 409 em aviso e veículo mantido",
        any(x["placa"] == v1["placa"] for x in srv.api("/api/veiculos")),
        page.locator("#avisos").inner_text(),
    )
    cap.tirar(
        page,
        "19-exclusao-bloqueada-historico",
        "Exclusão de veículo com histórico bloqueada (409): o aviso é a evidência",
        com_avisos=True,
    )
    page.get_by_role("button", name=f"Excluir veículo {v1['placa']}").click()
    dialogo_confirmar = page.locator("#dialogo-confirmar")
    expect(dialogo_confirmar).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialogo_confirmar).not_to_be_visible()
    aquietar(page)
    reg.verificar(
        "CONF-1",
        "Confirmação de exclusão: Esc cancela, não exclui e o diálogo pode ser reaberto",
        any(x["placa"] == v1["placa"] for x in srv.api("/api/veiculos")),
    )
    page.get_by_role("button", name=f"Excluir veículo {v1['placa']}").click()
    expect(dialogo_confirmar).to_be_visible()
    page.click("#dialogo-confirmar button[value=nao]")
    expect(dialogo_confirmar).not_to_be_visible()


def cenario_exclusoes(page, base, srv, reg, ctx):
    """Exclui veículo e motorista SEM histórico; o deslocamento realizado fica para a persistência."""
    abrir(page, base, "veiculos")
    page.get_by_role("button", name=f"Excluir veículo {ctx['v2']['placa']}").click()
    confirmar_exclusao(page)
    abrir(page, base, "motoristas")
    page.get_by_role("button", name=f"Excluir {ctx['m2']['nome']}").click()
    confirmar_exclusao(page)
    reg.verificar(
        "CRUD-X",
        "Excluir veículo e motorista sem histórico pela tela → removidos da API",
        all(x["placa"] != ctx["v2"]["placa"] for x in srv.api("/api/veiculos"))
        and all(x["cnh"] != ctx["m2"]["cnh"] for x in srv.api("/api/motoristas")),
    )


def instantaneo(srv) -> dict:
    return {
        k: srv.api(f"/api/{k}?limite=1000" if k == "deslocamentos" else f"/api/{k}")
        for k in ("veiculos", "motoristas", "deslocamentos")
    }


def cenario_persistencia(browser, base, srv, reg, cap):
    antes = instantaneo(srv)
    painel_antes = None
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    rastrear(page)
    abrir(page, base, "painel")
    painel_antes = ler_painel(page)
    srv.parar()
    reg.verificar("PERS-0", "Servidor encerrado (processo terminado)", srv.proc is None)
    srv.iniciar()
    depois = instantaneo(srv)
    reg.verificar(
        "PERS-1",
        "Após reiniciar: veículos, motoristas e deslocamentos idênticos (API)",
        antes == depois,
        f"antes={ {k: len(v) for k, v in antes.items()} } depois={ {k: len(v) for k, v in depois.items()} }",
    )
    page.reload()
    expect(page.locator("#tela-painel")).to_be_visible()
    aquietar(page)
    reg.verificar(
        "PERS-2",
        "Após reiniciar: o painel mostra os mesmos indicadores",
        ler_painel(page) == painel_antes,
        f"{painel_antes} -> {ler_painel(page)}",
    )
    abrir(page, base, "veiculos")
    reg.verificar(
        "PERS-3",
        "Após reiniciar: a tabela de veículos mostra os dados gravados",
        ctx_texto(page, "#veiculos-linhas") != "" and "HOM" in ctx_texto(page, "#veiculos-linhas"),
    )
    cap.tirar(
        page, "20-persistencia-apos-reiniciar", "Veículos após reiniciar o servidor: dados mantidos"
    )
    ctx.close()


def ctx_texto(page, seletor):
    return page.locator(seletor).inner_text()


def cenario_populado(playwright, python, porta, reg, cap, tmp, log):
    banco = tmp / "seed.db"
    saida = semear(python, banco)
    reg.verificar("SEED-1", "Seed fictício carrega em banco novo", "criados" in saida, saida)
    srv = Servidor(python, porta, banco, log)
    srv.iniciar()
    try:
        browser = playwright.chromium.launch()
        desk = browser.new_context(viewport={"width": 1280, "height": 800})
        p = desk.new_page()
        mon = Monitor()
        mon.ligar(p)
        abrir(p, srv.base, "painel")
        painel_confere(
            p,
            banco,
            reg,
            "SEED-2",
            "Painel com seed (156 deslocamentos): todos os números iguais ao SQL independente",
        )
        cap.tirar(
            p, "21-painel-seed-desktop", "Painel com dados de demonstração (desktop 1280 px)", True
        )
        for tela, nome, desc in [
            ("veiculos", "22-veiculos-seed-desktop", "Veículos com dados de demonstração"),
            (
                "deslocamentos",
                "23-deslocamentos-seed-desktop",
                "Histórico de deslocamentos com filtros e dados",
            ),
        ]:
            abrir(p, srv.base, tela)
            cap.tirar(p, nome, desc)
        # sem rolagem horizontal no desktop
        sem_rolagem = all(
            (
                abrir(p, srv.base, t),
                p.evaluate("document.documentElement.scrollWidth <= innerWidth"),
            )[1]
            for t in ("painel", "veiculos", "motoristas", "deslocamentos")
        )
        reg.verificar(
            "RESP-1", "Desktop 1280 px: nenhuma das 4 telas tem rolagem horizontal", sem_rolagem
        )
        desk.close()

        mob = browser.new_context(
            viewport={"width": 375, "height": 812}, device_scale_factor=2, is_mobile=True
        )
        m = mob.new_page()
        mon_m = Monitor()
        mon_m.ligar(m)
        abrir(m, srv.base, "painel")
        # Só a janela visível: numa captura de página inteira a barra fixa do rodapé
        # apareceria no meio da imagem (artefato da captura, não do sistema).
        cap.tirar(
            m,
            "24-painel-mobile-375",
            "Painel em 375 px (celular): indicadores empilhados e navegação no rodapé",
        )
        m.locator("#graf-finalidade").scroll_into_view_if_needed()
        m.evaluate("window.scrollBy(0, -120)")
        cap.tirar(m, "24b-painel-mobile-375-graficos", "Painel em 375 px: gráficos de barras")
        sem_rolagem_m = {}
        for t in ("painel", "veiculos", "motoristas", "deslocamentos"):
            abrir(m, srv.base, t)
            sem_rolagem_m[t] = m.evaluate("document.documentElement.scrollWidth <= innerWidth")
        reg.verificar(
            "RESP-2",
            "Celular 375 px: nenhuma das 4 telas tem rolagem horizontal",
            all(sem_rolagem_m.values()),
            str(sem_rolagem_m),
        )
        abrir(m, srv.base, "deslocamentos")
        cap.tirar(
            m, "25-deslocamentos-mobile-375", "Histórico em 375 px: linhas viram cartões", False
        )
        m.click("#deslocamentos-novo")
        cap.tirar(
            m, "26-formulario-mobile-375", "Formulário de deslocamento em tela cheia no celular"
        )
        mob.close()
        browser.close()
        return mon, mon_m, srv, banco
    except Exception:
        srv.parar()
        raise


# --------------------------------------------------------------------------- #
# Aceite da entrega, segredos e instalação a partir de clone limpo
# --------------------------------------------------------------------------- #
def executar(cmd, cwd: Path = RAIZ, limite: int = 900) -> tuple[int, str]:
    r = subprocess.run(
        [str(c) for c in cmd],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=limite,
    )
    return r.returncode, (r.stdout + r.stderr)


def contagem_pytest(saida: str) -> tuple[int, int]:
    passou = re.search(r"(\d+) passed", saida)
    falhou = re.search(r"(\d+) failed", saida)
    return (int(passou.group(1)) if passou else 0, int(falhou.group(1)) if falhou else 0)


def entregaveis(python: Path, reg: Registro) -> None:
    """Validação de entrega: o que foi prometido existe e funciona."""
    obrigatorios = [
        "README.md", "CLAUDE.md", "CONTEXTO.md", ".gitignore", "ruff.toml", "pytest.ini",
        "backend/requirements.txt", "backend/app/main.py", "frontend/index.html",
        "docs/Requisitos.md", "docs/Arquitetura.md", "docs/backlog.md", "docs/teste.md",
        "docs/execucao.md", "scripts/configurar.ps1", "scripts/iniciar.ps1",
        "scripts/verificar.ps1", "scripts/seed.ps1", "scripts/homologar.ps1",
    ]  # fmt: skip
    faltam = [f for f in obrigatorios if not (RAIZ / f).exists()]
    reg.verificar(
        "ENT-1",
        f"Entregáveis obrigatórios presentes ({len(obrigatorios)} arquivos)",
        not faltam,
        str(faltam),
    )

    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    secoes = [
        "Pré-requisitos",
        "Instalação e execução",
        "Exemplos de uso",
        "Limitações atuais",
        "Solução de problemas",
    ]
    ausentes = [x for x in secoes if f"## {x}" not in readme]
    reg.verificar(
        "ENT-2",
        "README: instalação e execução local (PowerShell), exemplos de uso e limitações",
        not ausentes,
        str(ausentes),
    )

    fontes = " ".join(f.read_text(encoding="utf-8") for f in (RAIZ / "tests").rglob("test_*.py"))
    nomes_ca = ["test_ca1_a_", "test_ca1_b_", "test_ca1_c_", "test_ca2_a_", "test_ca2_b_",
                "test_ca2_c_", "test_ca2_d_", "test_ca3_a_", "test_ca3_b_"]  # fmt: skip
    sem_teste = [n for n in nomes_ca if n not in fontes]
    reg.verificar(
        "ENT-3",
        "Critérios de aceite CA01, CA02 e CA03 têm teste automatizado",
        not sem_teste,
        str(sem_teste),
    )

    cod, saida = executar([python, "-m", "pytest", "-q", "-p", "no:warnings"])
    passou, falhou = contagem_pytest(saida)
    reg.verificar(
        "ENT-4",
        f"Suíte automatizada: {passou} passaram, {falhou} falharam",
        cod == 0 and passou > 0 and falhou == 0,
        saida[-300:],
    )

    c1, _ = executar([python, "-m", "ruff", "check", "."])
    c2, _ = executar([python, "-m", "ruff", "format", "--check", "."])
    reg.verificar(
        "ENT-5",
        "Lint (ruff check) e formatação (ruff format --check) sem pendências",
        c1 == 0 and c2 == 0,
    )


def segredos(reg: Registro) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "verificar_segredos", RAIZ / "homologacao" / "verificar_segredos.py"
    )
    vs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vs)
    arquivos = len([n for n in vs.git(RAIZ, "ls-files", "-z").split("\0") if n])
    commits = len(vs.git(RAIZ, "rev-list", "--all").split())
    achados = vs.verificar(RAIZ)
    reg.verificar("SEG-1", f"Git: {arquivos} arquivos versionados e {commits} commits (histórico inteiro) sem segredos, banco, chave, .env ou e-mail fora da lista permitida",
                  not achados, "; ".join(str(a) for a in achados[:3]))  # fmt: skip
    ignorados = [
        n
        for n in (".env", "backend/data/x.db", "chave.pem", ".venv/x")
        if executar(["git", "check-ignore", "-q", n])[0] != 0
    ]
    reg.verificar(
        "SEG-2",
        ".gitignore cobre .env, bancos .db, chaves .pem e ambientes virtuais",
        not ignorados,
        str(ignorados),
    )
    _, email = executar(["git", "config", "--local", "user.email"])
    reg.verificar("SEG-3", "Autor dos commits configurado só neste repositório com e-mail noreply", email.strip().endswith("@users.noreply.github.com"), email.strip())  # fmt: skip


def _apagar_arvore(pasta: Path) -> None:
    import shutil
    import stat

    def destravar(func, caminho, _):
        os.chmod(caminho, stat.S_IWRITE)
        func(caminho)

    if pasta.exists():
        shutil.rmtree(pasta, onexc=destravar)


def clone_limpo(porta: int, reg: Registro) -> None:
    """Instala e roda a partir de um clone do que foi COMMITADO (prova que nada falta no git)."""
    destino = (
        Path(tempfile.gettempdir()) / "rodagem-hml-clone"
    )  # caminho curto (limite de 260 do Windows)
    _apagar_arvore(destino)
    cod, saida = executar(["git", "clone", "-q", str(RAIZ), str(destino)])
    if not reg.verificar(
        "CLONE-1", "git clone do repositório local (só o que foi commitado)", cod == 0, saida[-200:]
    ):
        return
    try:
        cod, saida = executar(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                destino / "scripts" / "configurar.ps1",
            ],
            cwd=destino,
        )
        py = destino / ".venv" / "Scripts" / "python.exe"
        if not reg.verificar(
            "CLONE-2",
            "scripts\\configurar.ps1 cria o ambiente virtual e instala as dependências",
            cod == 0 and py.exists(),
            saida[-300:],
        ):
            return
        cod, saida = executar([py, "-m", "pytest", "-q", "-p", "no:warnings"], cwd=destino)
        passou, falhou = contagem_pytest(saida)
        reg.verificar(
            "CLONE-3",
            f"Testes no clone limpo: {passou} passaram, {falhou} falharam",
            cod == 0 and passou > 0 and falhou == 0,
            saida[-300:],
        )
        banco = Path(tempfile.mkdtemp(prefix="rodagem-clone-")) / "clone.db"
        reg.verificar(
            "CLONE-4",
            "Seed fictício no clone (banco temporário)",
            "criados" in semear(py, banco, destino),
        )
        srv = Servidor(py, porta, banco, banco.parent / "servidor.log", raiz=destino)
        srv.iniciar()
        try:
            with urllib.request.urlopen(srv.base + "/", timeout=10) as r:
                pagina = r.read().decode("utf-8")
            ind = srv.api("/api/dashboard/indicadores")
            reg.verificar("CLONE-5", "Servidor do clone sobe: página inicial e painel respondem com os dados do seed",
                          "Rodagem" in pagina and ind["total_veiculos"] == 6 and ind["total_deslocamentos"] > 0, str(ind)[:200])  # fmt: skip
        finally:
            srv.parar()
    finally:
        _apagar_arvore(destino)


def escrever_indice(pasta: Path, resultado: dict) -> None:
    def esc(t: str) -> str:
        return t.replace("|", "\\|").replace("\n", " ")

    linhas = [
        "# Evidências de homologação",
        "",
        f"Geradas em {resultado['gerado_em']} por `.\\scripts\\homologar.ps1` (servidor real, banco SQLite **temporário**, "
        "Chromium via Playwright). Todos os dados são fictícios. O banco do usuário não é tocado.",
        "",
        f"**Resultado: {resultado['ok']} OK · {resultado['falhas']} FALHA · {resultado['nao_testado']} NÃO TESTADO** "
        "— detalhes em [`resultado.json`](resultado.json).",
        "",
        "## Capturas de tela",
        "",
        "| Arquivo | O que mostra |",
        "|---|---|",
    ]
    for c in resultado["capturas"]:
        linhas.append(f"| [{c['arquivo']}]({c['arquivo']}) | {esc(c['descricao'])} |")
    linhas += ["", "## Verificações", "", "| ID | Verificação | Resultado |", "|---|---|---|"]
    for i in resultado["verificacoes"]:
        marca = {"OK": "✅ OK", "FALHA": "❌ FALHA", "NAO_TESTADO": "⚠️ NÃO TESTADO"}[i["resultado"]]
        linhas.append(f"| {i['id']} | {esc(i['descricao'])} | {marca} |")
    (pasta / "README.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Programa principal
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python-projeto", default=str(RAIZ / ".venv" / "Scripts" / "python.exe"))
    ap.add_argument("--evidencias", default=str(RAIZ / "docs" / "evidencias"))
    ap.add_argument("--porta", type=int, default=8780)
    ap.add_argument(
        "--sem-clone", action="store_true", help="pula a instalação a partir de clone limpo"
    )
    args = ap.parse_args()
    python = Path(args.python_projeto)
    reg = Registro()
    pasta = Path(args.evidencias)
    cap = Capturas(pasta, reg)
    for antigo in pasta.glob("*.png"):
        antigo.unlink()
    tmp = Path(tempfile.mkdtemp(prefix="rodagem-hml-"))
    log = tmp / "servidor.log"
    banco = tmp / "homologacao.db"
    srv = Servidor(python, args.porta, banco, log)
    inicio = datetime.now()

    dados = {
        "veiculos": [
            {
                "placa": f"{PREFIXO[:3]}1A11",
                "marca": "Fiat",
                "modelo": "Strada",
                "ano": 2022,
                "km": 1000,
            },
            {
                "placa": f"{PREFIXO[:3]}2B22",
                "marca": "Chevrolet",
                "modelo": "Spin",
                "ano": 2021,
                "km": 2000,
            },
        ],
        "motoristas": [
            {
                "nome": "Ana Homolog",
                "cnh": "00000000011",
                "cnh_mascarada": "000.000.000-11",
                "setor": "Testes",
            },
            {
                "nome": "Bruno Homolog",
                "cnh": "00000000022",
                "cnh_mascarada": "000.000.000-22",
                "setor": "Testes",
            },
        ],
    }
    srv.iniciar()
    mon = Monitor()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            mon.ligar(page)

            cenario_lista_vazia(page, srv.base, srv, reg, cap)
            contexto = cenario_crud(page, srv.base, srv, reg, cap, dados)
            cenario_indicadores(page, srv.base, srv, reg, cap, contexto)
            cenario_exclusoes(page, srv.base, srv, reg, contexto)
            ctx.close()
            cenario_persistencia(browser, srv.base, srv, reg, cap)
            browser.close()

            mon2, mon3, srv2, banco2 = cenario_populado(
                pw, python, args.porta + 1, reg, cap, tmp, log
            )
            srv2.parar()

        # --- Integração frontend ↔ API (todas as páginas e ações acima) ---
        todas = mon.respostas + mon2.respostas + mon3.respostas
        erros_5xx = [r for r in todas if r[0] >= 500]
        erros_estaticos = [r for r in todas if r[0] >= 400 and not r[2].startswith("/api/")]
        excecoes = mon.excecoes + mon2.excecoes + mon3.excecoes
        chamadas_api = [r for r in todas if r[2].startswith("/api/")]
        recusas = sorted(
            {(r[0], r[1], re.sub(r"/\d+", "/{id}", r[2])) for r in chamadas_api if r[0] >= 400}
        )
        reg.verificar(
            "INT-1",
            f"Integração: {len(chamadas_api)} chamadas à API feitas pela interface, nenhuma resposta 5xx",
            not erros_5xx,
            str(erros_5xx),
        )
        reg.verificar(
            "INT-2",
            "Integração: nenhum arquivo estático/página com erro 4xx (CSS, JS, HTML)",
            not erros_estaticos,
            str(erros_estaticos),
        )
        reg.verificar(
            "INT-3",
            "Integração: nenhuma exceção JavaScript não tratada nas páginas",
            not excecoes,
            str(excecoes),
        )
        outros_console = [
            c
            for c in mon.console + mon2.console + mon3.console
            if "Failed to load resource" not in c
        ]
        reg.verificar(
            "INT-4",
            "Integração: erros de console limitados às recusas 4xx esperadas da API",
            not outros_console,
            str(outros_console),
        )
        reg.verificar(
            "INT-5",
            "Integração: recusas 4xx vieram só de ações deliberadas (validação, conflito, exclusão bloqueada)",
            all(s in (404, 409, 422) for s, _, _ in recusas),
            str(recusas),
        )
        print("  recusas 4xx observadas:", recusas)
    finally:
        srv.parar()

    entregaveis(python, reg)
    segredos(reg)
    if args.sem_clone:
        reg.nao_testado("CLONE-0", "Instalação a partir de clone limpo", "pulado com --sem-clone")
    else:
        clone_limpo(args.porta + 2, reg)

    for id_, descricao, motivo in [
        ("NT-1", "Deploy no Vercel", "não feito por decisão da usuária; exige login pessoal e o SQLite em arquivo não persiste em funções serverless"),
        ("NT-2", "GitHub CLI (gh) e criação de repositório privado novo", "gh não está instalado; a usuária escolheu manter o repositório atual"),
        ("NT-3", "Login / autenticação", "extensão opcional, não implementada (pós-MVP)"),
        ("NT-4", "Lint de JavaScript", "exigiria Node/ESLint (ADR-006); cobertura parcial por testes estáticos e pelo navegador"),
        ("NT-5", "Leitor de tela (acessibilidade assistiva)", "só rótulos, aria-* e foco foram conferidos"),
        ("NT-6", "Firefox, Safari/WebKit e celular físico", "só Chromium (Playwright e navegador embutido), em largura emulada"),
        ("NT-7", "Uso simultâneo por várias pessoas (corrida na checagem de agenda)", "risco aceito no MVP (D-11 no backlog)"),
        ("NT-8", "Python 3.11–3.14 e outros sistemas operacionais", "validado só em Windows 11 com Python 3.15.1"),
    ]:  # fmt: skip
        reg.nao_testado(id_, descricao, motivo)

    fim = datetime.now()
    falhas = [i for i in reg.itens if i["resultado"] == "FALHA"]
    resultado = {
        "gerado_em": fim.isoformat(timespec="seconds"),
        "duracao_s": round((fim - inicio).total_seconds(), 1),
        "total": len(reg.itens),
        "ok": sum(i["resultado"] == "OK" for i in reg.itens),
        "falhas": len(falhas),
        "nao_testado": sum(i["resultado"] == "NAO_TESTADO" for i in reg.itens),
        "verificacoes": reg.itens,
        "capturas": reg.capturas,
    }
    (pasta / "resultado.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    escrever_indice(pasta, resultado)
    print(
        f"\nRESUMO: {resultado['ok']} OK · {resultado['falhas']} FALHA · {resultado['nao_testado']} NÃO TESTADO "
        f"· {len(reg.capturas)} capturas em {pasta}"
    )
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
