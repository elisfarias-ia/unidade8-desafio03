// Tela de deslocamentos: histórico com filtros, registro, edição, conclusão e exclusão.

import { api } from "./api.js";
import {
  FINALIDADES,
  SITUACAO_DESLOCAMENTO,
  SITUACAO_VEICULO,
  adiar,
  aoEnviar,
  avisar,
  confirmar,
  esc,
  formatarData,
  formatarKm,
  hojeIso,
  limparErros,
  ligarFechar,
  linhaVazia,
  preencherFormulario,
  preencherOpcoes,
  selo,
  semNulos,
} from "./ui.js";

const $ = (id) => document.getElementById(id);
const LIMITE = 200;
const COLUNAS = 9;
let lista = [];
let veiculos = [];
let motoristas = [];
let editandoId = null;
let concluindo = null;

export function iniciar() {
  const finalidades = Object.entries(FINALIDADES);
  const situacoes = Object.entries(SITUACAO_DESLOCAMENTO).map(([k, v]) => [k, v.rotulo]);
  preencherOpcoes($("filtro-finalidade"), finalidades, { vazio: "Todas" });
  preencherOpcoes($("filtro-status"), situacoes, { vazio: "Todas" });
  preencherOpcoes($("desl-finalidade"), finalidades, { vazio: "Selecione…" });
  preencherOpcoes($("desl-status"), situacoes);

  const filtros = $("deslocamentos-filtros");
  filtros.addEventListener("submit", (e) => e.preventDefault());
  filtros.addEventListener("input", adiar(carregarHistorico));
  filtros.addEventListener("change", adiar(carregarHistorico));
  filtros.addEventListener("reset", () => setTimeout(carregarHistorico));
  $("deslocamentos-novo").addEventListener("click", () => abrirFormulario());
  $("deslocamentos-linhas").addEventListener("click", aoClicarLinha);

  ligarFechar($("dialogo-deslocamento"));
  ligarFechar($("dialogo-concluir"));
  aoEnviar($("form-deslocamento"), salvar);
  aoEnviar($("form-concluir"), concluir);
}

export async function carregar() {
  await Promise.all([carregarCadastros(), carregarHistorico()]);
}

// Veículos e motoristas alimentam os filtros e o formulário.
async function carregarCadastros() {
  try {
    [veiculos, motoristas] = await Promise.all([api("/api/veiculos"), api("/api/motoristas")]);
  } catch (erro) {
    avisar(erro.message, "erro");
    return;
  }
  manterSelecao($("filtro-veiculo"), () =>
    preencherOpcoes($("filtro-veiculo"), veiculos.map(rotuloVeiculo), { vazio: "Todos" }),
  );
  manterSelecao($("filtro-motorista"), () =>
    preencherOpcoes($("filtro-motorista"), motoristas.map(rotuloMotorista), { vazio: "Todos" }),
  );
  preencherOpcoes($("desl-veiculo"), veiculos.map(rotuloVeiculo), { vazio: "Selecione…" });
  preencherOpcoes($("desl-motorista"), motoristas.map(rotuloMotorista), { vazio: "Selecione…" });
}

function manterSelecao(select, recriar) {
  const valor = select.value;
  recriar();
  select.value = valor;
}

function rotuloVeiculo(v) {
  const situacao = v.status === "disponivel" ? "" : ` (${SITUACAO_VEICULO[v.status]?.rotulo ?? v.status})`;
  return [v.id, `${v.placa} — ${v.marca} ${v.modelo}${situacao}`];
}

function rotuloMotorista(m) {
  return [m.id, m.ativo ? m.nome : `${m.nome} (inativo)`];
}

async function carregarHistorico() {
  const form = $("deslocamentos-filtros");
  const parametros = Object.fromEntries(new FormData(form));
  parametros.limite = LIMITE;
  const aviso = $("deslocamentos-filtro-erro");
  aviso.hidden = true;
  try {
    lista = await api("/api/deslocamentos", { parametros });
  } catch (erro) {
    aviso.textContent = erro.message;
    aviso.hidden = false;
    $("deslocamentos-linhas").innerHTML = linhaVazia(COLUNAS, "Corrija os filtros para ver o histórico.");
    $("deslocamentos-contagem").textContent = "";
    return;
  }
  const total = lista.length;
  $("deslocamentos-contagem").textContent =
    total >= LIMITE
      ? `Mostrando os ${LIMITE} mais recentes. Use os filtros para refinar.`
      : `${total} deslocamento${total === 1 ? "" : "s"} encontrado${total === 1 ? "" : "s"}`;
  $("deslocamentos-linhas").innerHTML = total
    ? lista.map(linha).join("")
    : linhaVazia(COLUNAS, "Nenhum deslocamento encontrado com esses filtros.");
}

function linha(d) {
  const aberto = d.status === "previsto" || d.status === "em_andamento";
  const km = d.km_percorrido !== null ? `${formatarKm(d.km_percorrido)} km` : "—";
  return `<tr>
    <td data-rotulo="Saída">${esc(formatarData(d.data_saida))}</td>
    <td data-rotulo="Retorno">${esc(formatarData(d.data_retorno))}</td>
    <td data-rotulo="Veículo"><strong>${esc(d.veiculo.placa)}</strong>
      <span class="tabela__secundario">${esc(d.veiculo.marca)} ${esc(d.veiculo.modelo)}</span></td>
    <td data-rotulo="Motorista">${esc(d.motorista.nome)}</td>
    <td data-rotulo="Destino">${esc(d.destino)}</td>
    <td data-rotulo="Finalidade">${esc(FINALIDADES[d.finalidade] ?? d.finalidade)}</td>
    <td data-rotulo="Situação">${selo(SITUACAO_DESLOCAMENTO, d.status)}</td>
    <td data-rotulo="Km percorrido" class="tabela__num">${esc(km)}</td>
    <td class="tabela__celula-acoes"><div class="tabela__acoes">
      ${
        aberto
          ? `<button type="button" class="botao botao--pequeno botao--primario" data-acao="concluir"
              data-id="${esc(d.id)}" aria-label="Concluir viagem para ${esc(d.destino)}">Concluir</button>`
          : ""
      }
      <button type="button" class="botao botao--pequeno" data-acao="editar" data-id="${esc(d.id)}"
        aria-label="Editar deslocamento para ${esc(d.destino)}">Editar</button>
      <button type="button" class="botao botao--pequeno botao--texto-perigo" data-acao="excluir"
        data-id="${esc(d.id)}" aria-label="Excluir deslocamento para ${esc(d.destino)}">Excluir</button>
    </div></td>
  </tr>`;
}

function abrirFormulario(desl = null) {
  const form = $("form-deslocamento");
  editandoId = desl?.id ?? null;
  limparErros(form);
  preencherFormulario(form, desl ?? { status: "previsto", data_saida: hojeIso() });
  $("dialogo-deslocamento-titulo").textContent = desl
    ? `Editar deslocamento #${desl.id}`
    : "Registrar deslocamento";
  $("dialogo-deslocamento").showModal();
  $("desl-veiculo").focus();
}

async function salvar(dados) {
  if (editandoId) {
    await api(`/api/deslocamentos/${editandoId}`, { metodo: "PUT", corpo: dados });
    avisar("Deslocamento atualizado.");
  } else {
    const salvo = await api("/api/deslocamentos", { metodo: "POST", corpo: semNulos(dados) });
    avisar(`Deslocamento para ${salvo.destino} registrado.`);
  }
  await carregar();
}

function abrirConclusao(desl) {
  concluindo = desl;
  const form = $("form-concluir");
  limparErros(form);
  preencherFormulario(form, { km_final: "", data_retorno: hojeIso() });
  form.querySelector("[data-resumo]").textContent =
    `${desl.veiculo.placa} para ${desl.destino}, saída em ${formatarData(desl.data_saida)}. ` +
    `Km inicial: ${formatarKm(desl.km_inicial)}.`;
  $("dialogo-concluir").showModal();
  $("concluir-km").focus();
}

async function concluir(dados) {
  const salvo = await api(`/api/deslocamentos/${concluindo.id}/concluir`, {
    metodo: "POST",
    corpo: semNulos(dados),
  });
  avisar(`Viagem concluída: ${formatarKm(salvo.km_percorrido)} km percorridos.`);
  await carregar();
}

async function aoClicarLinha(evento) {
  const botao = evento.target.closest("button[data-acao]");
  if (!botao) return;
  const desl = lista.find((d) => String(d.id) === botao.dataset.id);
  if (!desl) return;

  if (botao.dataset.acao === "editar") return abrirFormulario(desl);
  if (botao.dataset.acao === "concluir") return abrirConclusao(desl);

  const ok = await confirmar(
    `Excluir o deslocamento de ${desl.veiculo.placa} para ${desl.destino} ` +
      `(${formatarData(desl.data_saida)})? Esta ação não pode ser desfeita.`,
  );
  if (!ok) return;
  try {
    await api(`/api/deslocamentos/${desl.id}`, { metodo: "DELETE" });
    avisar("Deslocamento excluído.");
    await carregar();
  } catch (erro) {
    avisar(erro.message, "erro");
  }
}
