// Roteador por #hash: mostra uma tela por vez e pede a ela que recarregue os dados.

import { api } from "./api.js";
import * as deslocamentos from "./deslocamentos.js";
import * as motoristas from "./motoristas.js";
import { esc } from "./ui.js";
import * as veiculos from "./veiculos.js";

const inicio = {
  iniciar() {},
  async carregar() {
    const alvo = document.getElementById("saude-status");
    try {
      const dados = await api("/api/saude");
      alvo.innerHTML = `API: ${esc(dados.status)} · Banco: ${esc(dados.banco)} · versão ${esc(dados.versao)}`;
      alvo.className = "saude saude--ok";
    } catch (erro) {
      alvo.textContent = erro.message;
      alvo.className = "saude saude--erro";
    }
  },
};

const TELAS = { inicio, veiculos, motoristas, deslocamentos };
const PADRAO = "inicio";

function telaAtual() {
  const nome = location.hash.replace("#", "");
  return nome in TELAS ? nome : PADRAO;
}

async function mostrar() {
  const nome = telaAtual();
  for (const secao of document.querySelectorAll(".tela")) {
    secao.hidden = secao.id !== `tela-${nome}`;
  }
  for (const link of document.querySelectorAll(".navegacao__link")) {
    if (link.dataset.tela === nome) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  const secao = document.getElementById(`tela-${nome}`);
  document.title = `${secao.dataset.titulo} — Rodagem`;
  await TELAS[nome].carregar();
}

for (const tela of Object.values(TELAS)) tela.iniciar();

window.addEventListener("hashchange", () => {
  mostrar();
  document.getElementById("conteudo").focus({ preventScroll: true });
});
mostrar();
