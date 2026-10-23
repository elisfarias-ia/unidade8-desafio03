"use strict";

// Escapa strings vindas da API antes de inseri-las no HTML.
function esc(valor) {
  return String(valor ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function verificarSaude() {
  const alvo = document.getElementById("saude-status");
  try {
    const resposta = await fetch("/api/saude");
    if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
    const dados = await resposta.json();
    alvo.innerHTML = `API: ${esc(dados.status)} · Banco: ${esc(dados.banco)} · versão ${esc(dados.versao)}`;
    alvo.classList.add("saude__status--ok");
  } catch (erro) {
    alvo.textContent = "Não foi possível falar com a API. Confira se o servidor está rodando.";
    alvo.classList.add("saude__status--erro");
  }
}

verificarSaude();
