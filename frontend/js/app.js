// Roteador por #hash: mostra uma tela por vez e pede a ela que recarregue os dados.

import * as deslocamentos from "./deslocamentos.js";
import * as motoristas from "./motoristas.js";
import * as painel from "./painel.js";
import * as veiculos from "./veiculos.js";

const TELAS = { painel, deslocamentos, veiculos, motoristas };
const PADRAO = "painel";

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
