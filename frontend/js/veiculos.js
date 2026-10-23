// Tela de veículos: listagem com filtros, cadastro, edição e exclusão.

import { api } from "./api.js";
import {
  SITUACAO_VEICULO,
  adiar,
  aoEnviar,
  avisar,
  confirmar,
  esc,
  formatarKm,
  limparErros,
  ligarFechar,
  linhaVazia,
  preencherFormulario,
  preencherOpcoes,
  selo,
  semNulos,
} from "./ui.js";

const $ = (id) => document.getElementById(id);
let lista = [];
let editandoId = null;

export function iniciar() {
  const situacoes = Object.entries(SITUACAO_VEICULO).map(([k, v]) => [k, v.rotulo]);
  preencherOpcoes($("veiculos-status"), situacoes, { vazio: "Todas" });
  preencherOpcoes($("veiculo-status"), situacoes);

  const filtros = $("veiculos-filtros");
  filtros.addEventListener("submit", (e) => e.preventDefault());
  filtros.addEventListener("input", adiar(carregar));
  $("veiculos-novo").addEventListener("click", () => abrirFormulario());
  $("veiculos-linhas").addEventListener("click", aoClicarLinha);

  const dialogo = $("dialogo-veiculo");
  ligarFechar(dialogo);
  aoEnviar($("form-veiculo"), salvar);
}

export async function carregar() {
  const parametros = {
    busca: $("veiculos-busca").value.trim(),
    status: $("veiculos-status").value,
  };
  try {
    lista = await api("/api/veiculos", { parametros });
  } catch (erro) {
    $("veiculos-linhas").innerHTML = linhaVazia(7, erro.message);
    $("veiculos-contagem").textContent = "";
    return;
  }
  $("veiculos-contagem").textContent =
    `${lista.length} veículo${lista.length === 1 ? "" : "s"} encontrado${lista.length === 1 ? "" : "s"}`;
  $("veiculos-linhas").innerHTML = lista.length
    ? lista.map(linha).join("")
    : linhaVazia(7, "Nenhum veículo encontrado com esses filtros.");
}

function linha(v) {
  return `<tr>
    <td data-rotulo="Placa"><strong>${esc(v.placa)}</strong></td>
    <td data-rotulo="Veículo">${esc(v.marca)} ${esc(v.modelo)}${
      v.cor ? `<span class="tabela__secundario">${esc(v.cor)}</span>` : ""
    }</td>
    <td data-rotulo="Ano">${esc(v.ano)}</td>
    <td data-rotulo="Tipo">${esc(v.tipo ?? "—")}</td>
    <td data-rotulo="Km atual" class="tabela__num">${esc(formatarKm(v.km_atual))}</td>
    <td data-rotulo="Situação">${selo(SITUACAO_VEICULO, v.status)}</td>
    <td class="tabela__celula-acoes"><div class="tabela__acoes">
      <button type="button" class="botao botao--pequeno" data-acao="editar" data-id="${esc(v.id)}"
        aria-label="Editar veículo ${esc(v.placa)}">Editar</button>
      <button type="button" class="botao botao--pequeno botao--texto-perigo" data-acao="excluir"
        data-id="${esc(v.id)}" aria-label="Excluir veículo ${esc(v.placa)}">Excluir</button>
    </div></td>
  </tr>`;
}

function abrirFormulario(veiculo = null) {
  const form = $("form-veiculo");
  editandoId = veiculo?.id ?? null;
  limparErros(form);
  preencherFormulario(form, veiculo ?? { status: "disponivel", km_atual: 0 });
  $("dialogo-veiculo-titulo").textContent = veiculo
    ? `Editar veículo ${veiculo.placa}`
    : "Novo veículo";
  $("dialogo-veiculo").showModal();
  $("veiculo-placa").focus();
}

async function salvar(dados) {
  if (editandoId) {
    const salvo = await api(`/api/veiculos/${editandoId}`, { metodo: "PUT", corpo: dados });
    avisar(`Veículo ${salvo.placa} atualizado.`);
  } else {
    const salvo = await api("/api/veiculos", { metodo: "POST", corpo: semNulos(dados) });
    avisar(`Veículo ${salvo.placa} cadastrado.`);
  }
  await carregar();
}

async function aoClicarLinha(evento) {
  const botao = evento.target.closest("button[data-acao]");
  if (!botao) return;
  const veiculo = lista.find((v) => String(v.id) === botao.dataset.id);
  if (!veiculo) return;

  if (botao.dataset.acao === "editar") {
    abrirFormulario(veiculo);
    return;
  }
  const ok = await confirmar(
    `Excluir o veículo ${veiculo.placa} (${veiculo.marca} ${veiculo.modelo})? Esta ação não pode ser desfeita.`,
  );
  if (!ok) return;
  try {
    await api(`/api/veiculos/${veiculo.id}`, { metodo: "DELETE" });
    avisar(`Veículo ${veiculo.placa} excluído.`);
    await carregar();
  } catch (erro) {
    avisar(erro.message, "erro");
  }
}
