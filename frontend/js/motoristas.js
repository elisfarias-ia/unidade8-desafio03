// Tela de motoristas: listagem com filtros, cadastro, edição e exclusão.

import { api } from "./api.js";
import {
  CATEGORIAS_CNH,
  adiar,
  aoEnviar,
  avisar,
  confirmar,
  esc,
  formatarData,
  limparErros,
  ligarFechar,
  linhaVazia,
  preencherFormulario,
  preencherOpcoes,
  semNulos,
} from "./ui.js";

const $ = (id) => document.getElementById(id);
let lista = [];
let editandoId = null;
let versao = 0; // Descarta respostas antigas que chegam depois de uma mais nova (achado da revisão).

export function iniciar() {
  preencherOpcoes(
    $("motorista-categoria"),
    CATEGORIAS_CNH.map((c) => [c, c]),
  );

  const filtros = $("motoristas-filtros");
  filtros.addEventListener("submit", (e) => e.preventDefault());
  filtros.addEventListener("input", adiar(carregar));
  $("motoristas-novo").addEventListener("click", () => abrirFormulario());
  $("motoristas-linhas").addEventListener("click", aoClicarLinha);

  ligarFechar($("dialogo-motorista"));
  aoEnviar($("form-motorista"), salvar);
}

export async function carregar() {
  const minha = ++versao;
  const parametros = {
    busca: $("motoristas-busca").value.trim(),
    apenas_ativos: $("motoristas-ativos").checked ? "true" : "",
  };
  let resposta;
  try {
    resposta = await api("/api/motoristas", { parametros });
  } catch (erro) {
    if (minha !== versao) return;
    $("motoristas-linhas").innerHTML = linhaVazia(8, erro.message);
    $("motoristas-contagem").textContent = "";
    return;
  }
  if (minha !== versao) return;
  lista = resposta;
  $("motoristas-contagem").textContent =
    `${lista.length} motorista${lista.length === 1 ? "" : "s"} encontrado${lista.length === 1 ? "" : "s"}`;
  $("motoristas-linhas").innerHTML = lista.length
    ? lista.map(linha).join("")
    : linhaVazia(8, "Nenhum motorista encontrado com esses filtros.");
}

function linha(m) {
  const situacao = m.ativo
    ? '<span class="selo selo--ok">Ativo</span>'
    : '<span class="selo selo--neutro">Inativo</span>';
  return `<tr>
    <td data-rotulo="Nome"><strong>${esc(m.nome)}</strong></td>
    <td data-rotulo="CNH">${esc(m.cnh)}</td>
    <td data-rotulo="Categoria">${esc(m.categoria_cnh)}</td>
    <td data-rotulo="Validade">${esc(formatarData(m.validade_cnh))}</td>
    <td data-rotulo="Setor">${esc(m.setor ?? "—")}</td>
    <td data-rotulo="Telefone">${esc(m.telefone ?? "—")}</td>
    <td data-rotulo="Situação">${situacao}</td>
    <td class="tabela__celula-acoes"><div class="tabela__acoes">
      <button type="button" class="botao botao--pequeno" data-acao="editar" data-id="${esc(m.id)}"
        aria-label="Editar ${esc(m.nome)}">Editar</button>
      <button type="button" class="botao botao--pequeno botao--texto-perigo" data-acao="excluir"
        data-id="${esc(m.id)}" aria-label="Excluir ${esc(m.nome)}">Excluir</button>
    </div></td>
  </tr>`;
}

function abrirFormulario(motorista = null) {
  const form = $("form-motorista");
  editandoId = motorista?.id ?? null;
  limparErros(form);
  preencherFormulario(form, motorista ?? { categoria_cnh: "B", ativo: true });
  $("dialogo-motorista-titulo").textContent = motorista
    ? `Editar ${motorista.nome}`
    : "Novo motorista";
  $("dialogo-motorista").showModal();
  $("motorista-nome").focus();
}

async function salvar(dados) {
  if (editandoId) {
    const salvo = await api(`/api/motoristas/${editandoId}`, { metodo: "PUT", corpo: dados });
    avisar(`Cadastro de ${salvo.nome} atualizado.`);
  } else {
    const salvo = await api("/api/motoristas", { metodo: "POST", corpo: semNulos(dados) });
    avisar(`${salvo.nome} cadastrado(a).`);
  }
  await carregar();
}

async function aoClicarLinha(evento) {
  const botao = evento.target.closest("button[data-acao]");
  if (!botao) return;
  const motorista = lista.find((m) => String(m.id) === botao.dataset.id);
  if (!motorista) return;

  if (botao.dataset.acao === "editar") {
    abrirFormulario(motorista);
    return;
  }
  const ok = await confirmar(`Excluir o cadastro de ${motorista.nome}? Esta ação não pode ser desfeita.`);
  if (!ok) return;
  try {
    await api(`/api/motoristas/${motorista.id}`, { metodo: "DELETE" });
    avisar(`Cadastro de ${motorista.nome} excluído.`);
    await carregar();
  } catch (erro) {
    avisar(erro.message, "erro");
  }
}
