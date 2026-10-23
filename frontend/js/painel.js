// Painel: indicadores calculados pela API (nada é calculado aqui, só apresentado).

import { api } from "./api.js";
import { FINALIDADES, esc, formatarData, formatarKm, linhaVazia } from "./ui.js";

const $ = (id) => document.getElementById(id);

const numero = (n) => Number(n).toLocaleString("pt-BR");
const porcento = (n) => `${Number(n).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
const plural = (n, um, varios) => `${numero(n)} ${n === 1 ? um : varios}`;

export function iniciar() {
  $("painel-periodo").addEventListener("submit", (e) => {
    e.preventDefault();
    carregar();
  });
  $("painel-padrao").addEventListener("click", () => {
    $("painel-inicio").value = "";
    $("painel-fim").value = "";
    carregar();
  });
}

export async function carregar() {
  verificarSaude();
  const erro = $("painel-erro");
  erro.hidden = true;
  const parametros = { data_inicio: $("painel-inicio").value, data_fim: $("painel-fim").value };
  let indicadores;
  let proximas;
  try {
    [indicadores, proximas] = await Promise.all([
      api("/api/dashboard/indicadores", { parametros }),
      api("/api/dashboard/proximas-saidas"),
    ]);
  } catch (e) {
    erro.textContent = e.message;
    erro.hidden = false;
    $("painel-conteudo").hidden = true;
    $("painel-vazio").hidden = true;
    return;
  }
  // As datas efetivas (inclusive o padrão) vêm da API.
  $("painel-inicio").value = indicadores.periodo_inicio;
  $("painel-fim").value = indicadores.periodo_fim;
  $("painel-periodo-texto").textContent =
    `Período: ${formatarData(indicadores.periodo_inicio)} a ${formatarData(indicadores.periodo_fim)} ` +
    "(pela data de saída)";
  desenhar(indicadores);
  desenharProximas(proximas);
}

function desenhar(i) {
  const vazio = i.total_deslocamentos === 0;
  $("painel-vazio").hidden = !vazio;
  $("painel-conteudo").hidden = false;

  // 1) Veículos
  $("ind-veiculos").textContent = numero(i.total_veiculos);
  $("ind-veiculos-d").textContent =
    `${plural(i.veiculos_disponiveis, "disponível", "disponíveis")} · ${numero(i.veiculos_em_viagem)} em viagem · ` +
    `${numero(i.veiculos_manutencao)} em manutenção · ${plural(i.veiculos_inativos, "inativo", "inativos")}`;

  // 2) Deslocamentos
  $("ind-desl").textContent = numero(i.total_deslocamentos);
  $("ind-desl-d").textContent =
    `${plural(i.viagens_previstas, "previsto", "previstos")} · ${numero(i.viagens_em_andamento)} em andamento · ` +
    `${plural(i.viagens_realizadas, "realizado", "realizados")} · ` +
    `${plural(i.viagens_canceladas, "cancelado", "cancelados")}`;

  // 3) Viagens previstas × realizadas
  $("ind-viag").textContent = `${numero(i.viagens_previstas)} × ${numero(i.viagens_realizadas)}`;
  const base = i.viagens_previstas + i.viagens_realizadas;
  $("ind-viag-barra").innerHTML = base
    ? `<span class="proporcao__parte proporcao__parte--realizada" style="width: ${(i.viagens_realizadas / base) * 100}%"></span>`
    : "";
  $("ind-viag-d").textContent = base
    ? `${plural(i.viagens_previstas, "prevista", "previstas")} e ` +
      `${plural(i.viagens_realizadas, "realizada", "realizadas")}`
    : "Nenhuma viagem prevista ou realizada no período";

  // Calculados
  $("ind-taxa").textContent = porcento(i.taxa_realizacao);
  $("ind-km").textContent = `${formatarKm(i.km_total_percorrido)} km`;
  $("ind-media").textContent = `${formatarKm(i.media_km_por_viagem)} km`;
  $("ind-uso").textContent = porcento(i.taxa_utilizacao_frota);

  barras($("graf-finalidade"), i.deslocamentos_por_finalidade);
  barras($("graf-destinos"), i.top_destinos);
  barras($("graf-meses"), i.serie_mensal.map((m) => ({ ...m, rotulo: rotuloMes(m.rotulo) })));
}

function rotuloMes(anoMes) {
  const [ano, mes] = anoMes.split("-");
  return `${mes}/${ano}`;
}

function barras(lista, itens) {
  if (!itens.length) {
    lista.innerHTML = '<li class="grafico__vazio">Sem dados no período.</li>';
    return;
  }
  const maior = Math.max(...itens.map((i) => i.valor));
  lista.innerHTML = itens
    .map(
      (i) => `<li class="grafico__linha">
        <span class="grafico__rotulo">${esc(i.rotulo)}</span>
        <span class="grafico__trilho" aria-hidden="true">
          <span class="grafico__barra" style="width: ${(i.valor / maior) * 100}%"></span>
        </span>
        <span class="grafico__valor">${esc(numero(i.valor))}</span>
      </li>`,
    )
    .join("");
}

function desenharProximas(lista) {
  $("proximas-linhas").innerHTML = lista.length
    ? lista
        .map(
          (d) => `<tr>
        <td data-rotulo="Saída">${esc(formatarData(d.data_saida))}</td>
        <td data-rotulo="Veículo"><strong>${esc(d.veiculo.placa)}</strong>
          <span class="tabela__secundario">${esc(d.veiculo.marca)} ${esc(d.veiculo.modelo)}</span></td>
        <td data-rotulo="Motorista">${esc(d.motorista.nome)}</td>
        <td data-rotulo="Destino">${esc(d.destino)}</td>
        <td data-rotulo="Finalidade">${esc(FINALIDADES[d.finalidade] ?? d.finalidade)}</td>
      </tr>`,
        )
        .join("")
    : linhaVazia(5, "Nenhuma saída prevista a partir de hoje.");
}

async function verificarSaude() {
  const alvo = $("saude-status");
  try {
    const dados = await api("/api/saude");
    alvo.textContent = `API ${dados.status} · banco ${dados.banco} · versão ${dados.versao}`;
    alvo.className = "saude saude--ok";
  } catch (erro) {
    alvo.textContent = erro.message;
    alvo.className = "saude saude--erro";
  }
}
