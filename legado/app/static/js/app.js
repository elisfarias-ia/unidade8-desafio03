/* Rodagem — camada de interface. Vanilla JS, sem build. */

const API = "/api";

const estado = {
  veiculos: [],
  motoristas: [],
  deslocamentos: [],
  indicadores: null,
};

const ROTULOS = {
  disponivel: "Disponível",
  em_viagem: "Em viagem",
  manutencao: "Em manutenção",
  inativo: "Inativo",
  previsto: "Prevista",
  em_andamento: "Em andamento",
  realizado: "Realizada",
  cancelado: "Cancelada",
  administrativa: "Administrativa",
  operacional: "Operacional",
  entrega: "Entrega",
  visita_tecnica: "Visita técnica",
  outros: "Outros",
};

const rotulo = (v) => ROTULOS[v] || v || "—";
const esc = (t) =>
  String(t ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
const dataBR = (iso) => (iso ? iso.split("-").reverse().join("/") : "—");
const num = (v, casas = 0) =>
  Number(v ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });

/* ───────────────────────────── infraestrutura ───────────────────────────── */

async function api(caminho, opcoes = {}) {
  const resposta = await fetch(API + caminho, {
    headers: { "Content-Type": "application/json" },
    ...opcoes,
  });
  if (resposta.status === 204) return null;
  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    throw new Error(mensagemDeErro(corpo, resposta.status));
  }
  return corpo;
}

function mensagemDeErro(corpo, status) {
  if (!corpo) return `A requisição falhou (${status}).`;
  const d = corpo.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((e) => {
        const campo = (e.loc || []).filter((p) => p !== "body").join(" › ");
        return campo ? `${campo}: ${e.msg}` : e.msg;
      })
      .join(" | ");
  }
  return `A requisição falhou (${status}).`;
}

function avisar(texto, tipo = "ok") {
  const area = document.getElementById("avisos");
  const el = document.createElement("div");
  el.className = `aviso aviso--${tipo}`;
  el.textContent = texto;
  area.appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

function abrirModal(titulo, html) {
  document.getElementById("modal-titulo").textContent = titulo;
  document.getElementById("modal-corpo").innerHTML = html;
  document.getElementById("modal").hidden = false;
  const primeiro = document.querySelector("#modal-corpo input, #modal-corpo select");
  if (primeiro) primeiro.focus();
}
function fecharModal() {
  document.getElementById("modal").hidden = true;
  document.getElementById("modal-corpo").innerHTML = "";
}
document.getElementById("modal").addEventListener("click", (e) => {
  if (e.target.hasAttribute("data-fechar")) fecharModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") fecharModal();
});

/* ─────────────────────────────── navegação ─────────────────────────────── */

function navegar(pagina) {
  document.querySelectorAll(".pagina").forEach((p) => p.classList.remove("is-ativa"));
  document.getElementById(`pagina-${pagina}`).classList.add("is-ativa");
  document
    .querySelectorAll("[data-pagina]")
    .forEach((b) => b.classList.toggle("is-ativo", b.dataset.pagina === pagina));
  window.scrollTo({ top: 0 });
  if (pagina === "painel") carregarPainel();
  if (pagina === "deslocamentos") carregarDeslocamentos();
  if (pagina === "veiculos") carregarVeiculos();
  if (pagina === "motoristas") carregarMotoristas();
}
document
  .querySelectorAll("[data-pagina]")
  .forEach((b) => b.addEventListener("click", () => navegar(b.dataset.pagina)));

/* ──────────────────────────────── painel ──────────────────────────────── */

async function carregarPainel() {
  const inicio = document.getElementById("periodo-inicio").value;
  const fim = document.getElementById("periodo-fim").value;
  const params = new URLSearchParams();
  if (inicio) params.set("data_inicio", inicio);
  if (fim) params.set("data_fim", fim);

  try {
    const [ind, proximas] = await Promise.all([
      api(`/dashboard/indicadores?${params}`),
      api(`/deslocamentos?status=previsto&limite=6`),
    ]);
    estado.indicadores = ind;
    desenharIndicadores(ind);
    desenharGraficos(ind);
    desenharQuadro(proximas);
    document.getElementById("painel-periodo").textContent =
      `Dados de ${dataBR(ind.periodo_inicio)} a ${dataBR(ind.periodo_fim)}.`;
  } catch (e) {
    avisar(e.message, "erro");
  }
}

function desenharQuadro(lista) {
  const alvo = document.getElementById("quadro-lista");
  const hoje = new Date();
  document.getElementById("quadro-hoje").textContent = hoje.toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
  });

  const ordenada = [...lista].sort((a, b) => a.data_saida.localeCompare(b.data_saida));
  if (!ordenada.length) {
    alvo.innerHTML = `<li class="quadro__vazio">Nenhuma saída prevista. Registre um deslocamento para abrir a agenda da frota.</li>`;
    return;
  }
  alvo.innerHTML = ordenada
    .map((d) => {
      const [, mes, dia] = d.data_saida.split("-");
      return `<li class="quadro__item">
        <div class="quadro__data">${dia}<span>${mesCurto(mes)}</span></div>
        <div>
          <div class="quadro__destino">${esc(d.destino)}</div>
          <div class="quadro__detalhe">${esc(d.veiculo.placa)} · ${esc(d.motorista.nome)} · ${rotulo(d.finalidade)}</div>
        </div>
        <span class="marca marca--${d.status}">${rotulo(d.status)}</span>
      </li>`;
    })
    .join("");
}
const mesCurto = (mm) =>
  ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][
    Number(mm) - 1
  ];

function desenharIndicadores(i) {
  const cartoes = [
    {
      valor: num(i.total_veiculos),
      nome: "Veículos cadastrados",
      nota: `${num(i.veiculos_disponiveis)} disponíveis · ${num(i.veiculos_em_viagem)} em viagem`,
    },
    {
      valor: num(i.total_deslocamentos),
      nome: "Deslocamentos no período",
      nota: `${num(i.viagens_previstas)} previstas · ${num(i.viagens_realizadas)} realizadas`,
    },
    {
      valor: `${num(i.taxa_realizacao, 1)}<small>%</small>`,
      nome: "Viagens realizadas",
      nota: "Realizadas ÷ (previstas + realizadas)",
      destaque: true,
    },
    {
      valor: `${num(i.km_total_percorrido, 1)}<small> km</small>`,
      nome: "Distância percorrida",
      nota: `Média de ${num(i.media_km_por_viagem, 1)} km por viagem`,
    },
    {
      valor: `${num(i.taxa_utilizacao_frota, 1)}<small>%</small>`,
      nome: "Frota utilizada",
      nota: "Veículos com ao menos uma viagem no período",
    },
  ];
  document.getElementById("indicadores").innerHTML = cartoes
    .map(
      (c) => `<article class="indicador ${c.destaque ? "indicador--destaque" : ""}">
        <div class="indicador__valor">${c.valor}</div>
        <div class="indicador__nome">${c.nome}</div>
        <div class="indicador__nota">${c.nota}</div>
      </article>`
    )
    .join("");
}

function barras(itens, variante = "") {
  if (!itens.length) return `<p class="vazio-bloco">Sem dados no período selecionado.</p>`;
  const maximo = Math.max(...itens.map((i) => i.valor), 1);
  return itens
    .map(
      (i) => `<div class="barra-linha">
        <div class="barra-linha__topo">
          <span>${esc(i.rotulo)}</span>
          <span class="barra-linha__valor">${num(i.valor)}</span>
        </div>
        <div class="barra-trilho">
          <div class="barra-preenchida ${variante}" style="width:${(i.valor / maximo) * 100}%"></div>
        </div>
      </div>`
    )
    .join("");
}

function desenharGraficos(i) {
  document.getElementById("grafico-status").innerHTML = barras(
    [
      { rotulo: "Previstas", valor: i.viagens_previstas },
      { rotulo: "Realizadas", valor: i.viagens_realizadas },
    ],
    "barra-preenchida--verde"
  );
  document.getElementById("grafico-finalidade").innerHTML = barras(
    i.deslocamentos_por_finalidade
  );
  document.getElementById("grafico-destinos").innerHTML = barras(
    i.top_destinos,
    "barra-preenchida--faixa"
  );
}

document.getElementById("form-periodo").addEventListener("submit", (e) => {
  e.preventDefault();
  carregarPainel();
});

/* ─────────────────────────────── veículos ─────────────────────────────── */

async function carregarVeiculos() {
  const f = document.getElementById("filtros-veiculo");
  const params = new URLSearchParams(
    Object.fromEntries(
      [...new FormData(f).entries()].filter(([, v]) => v !== "")
    )
  );
  try {
    estado.veiculos = await api(`/veiculos?${params}`);
    desenharVeiculos();
    preencherSelects();
  } catch (e) {
    avisar(e.message, "erro");
  }
}

function desenharVeiculos() {
  const alvo = document.getElementById("lista-veiculos");
  if (!estado.veiculos.length) {
    alvo.innerHTML = `<p class="linha-vazia">Nenhum veículo encontrado. Cadastre o primeiro veículo da frota para começar.</p>`;
    return;
  }
  alvo.innerHTML = `<table>
    <thead><tr>
      <th>Placa</th><th>Veículo</th><th>Ano</th><th>Tipo</th>
      <th>Km atual</th><th>Situação</th><th></th>
    </tr></thead>
    <tbody>${estado.veiculos
      .map(
        (v) => `<tr>
        <td><span class="placa">${esc(v.placa)}</span></td>
        <td>${esc(v.marca)} ${esc(v.modelo)}${v.cor ? ` <span class="indicador__nota">${esc(v.cor)}</span>` : ""}</td>
        <td>${v.ano}</td>
        <td>${esc(v.tipo || "—")}</td>
        <td>${num(v.km_atual, 1)}</td>
        <td><span class="marca marca--${v.status}">${rotulo(v.status)}</span></td>
        <td><div class="celula-acoes">
          <button class="btn btn--claro btn--mini" onclick="formVeiculo(${v.id})">Editar</button>
          <button class="btn btn--texto btn--mini" onclick="excluirVeiculo(${v.id})">Excluir</button>
        </div></td>
      </tr>`
      )
      .join("")}</tbody></table>`;
}

function formVeiculo(id = null) {
  const v = id ? estado.veiculos.find((x) => x.id === id) : null;
  abrirModal(v ? `Editar ${v.placa}` : "Cadastrar veículo", `
    <form id="form-veiculo" class="form-grade">
      <label>Placa
        <input name="placa" required maxlength="8" placeholder="ABC1D23"
          value="${v ? esc(v.placa) : ""}" ${v ? "readonly" : ""}>
      </label>
      <label>Marca <input name="marca" required value="${v ? esc(v.marca) : ""}"></label>
      <label>Modelo <input name="modelo" required value="${v ? esc(v.modelo) : ""}"></label>
      <label>Ano <input name="ano" type="number" required min="1950" max="${new Date().getFullYear() + 1}" value="${v ? v.ano : new Date().getFullYear()}"></label>
      <label>Cor <input name="cor" value="${v ? esc(v.cor || "") : ""}"></label>
      <label>Tipo
        <select name="tipo">
          ${["Sedan", "Hatch", "SUV", "Van", "Caminhonete", "Ônibus", "Caminhão"]
            .map((t) => `<option ${v && v.tipo === t ? "selected" : ""}>${t}</option>`)
            .join("")}
        </select>
      </label>
      <label>Quilometragem atual <input name="km_atual" type="number" step="0.1" min="0" value="${v ? v.km_atual : 0}"></label>
      <label>Situação
        <select name="status">
          ${["disponivel", "em_viagem", "manutencao", "inativo"]
            .map((s) => `<option value="${s}" ${v && v.status === s ? "selected" : ""}>${rotulo(s)}</option>`)
            .join("")}
        </select>
      </label>
      <div class="campo-largo form-acoes">
        <button type="button" class="btn btn--texto" data-fechar>Cancelar</button>
        <button type="submit" class="btn btn--principal">${v ? "Salvar alterações" : "Cadastrar veículo"}</button>
      </div>
      <div class="campo-largo" id="erro-form"></div>
    </form>`);

  document.getElementById("form-veiculo").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = Object.fromEntries(new FormData(e.target));
    dados.ano = Number(dados.ano);
    dados.km_atual = Number(dados.km_atual);
    try {
      if (v) {
        delete dados.placa;
        await api(`/veiculos/${v.id}`, { method: "PUT", body: JSON.stringify(dados) });
        avisar("Veículo atualizado.");
      } else {
        await api("/veiculos", { method: "POST", body: JSON.stringify(dados) });
        avisar("Veículo cadastrado.");
      }
      fecharModal();
      carregarVeiculos();
    } catch (err) {
      document.getElementById("erro-form").innerHTML =
        `<p class="form-erro">${esc(err.message)}</p>`;
    }
  });
}

async function excluirVeiculo(id) {
  const v = estado.veiculos.find((x) => x.id === id);
  if (!confirm(`Excluir o veículo ${v.placa}? Essa ação não pode ser desfeita.`)) return;
  try {
    await api(`/veiculos/${id}`, { method: "DELETE" });
    avisar("Veículo excluído.");
    carregarVeiculos();
  } catch (e) {
    avisar(e.message, "erro");
  }
}

document.getElementById("btn-novo-veiculo").addEventListener("click", () => formVeiculo());
document.getElementById("filtros-veiculo").addEventListener("submit", (e) => {
  e.preventDefault();
  carregarVeiculos();
});
document.getElementById("filtros-veiculo").addEventListener("reset", () =>
  setTimeout(carregarVeiculos, 0)
);

/* ────────────────────────────── motoristas ────────────────────────────── */

async function carregarMotoristas() {
  try {
    estado.motoristas = await api("/motoristas");
    desenharMotoristas();
    preencherSelects();
  } catch (e) {
    avisar(e.message, "erro");
  }
}

function desenharMotoristas() {
  const alvo = document.getElementById("lista-motoristas");
  if (!estado.motoristas.length) {
    alvo.innerHTML = `<p class="linha-vazia">Nenhum motorista cadastrado. Cadastre um condutor para poder registrar deslocamentos.</p>`;
    return;
  }
  alvo.innerHTML = `<table>
    <thead><tr><th>Nome</th><th>CNH</th><th>Categoria</th><th>Validade</th><th>Setor</th><th>Situação</th><th></th></tr></thead>
    <tbody>${estado.motoristas
      .map(
        (m) => `<tr>
          <td>${esc(m.nome)}</td>
          <td>${esc(m.cnh)}</td>
          <td>${esc(m.categoria_cnh)}</td>
          <td>${dataBR(m.validade_cnh)}</td>
          <td>${esc(m.setor || "—")}</td>
          <td><span class="marca marca--${m.ativo ? "disponivel" : "inativo"}">${m.ativo ? "Ativo" : "Inativo"}</span></td>
          <td><div class="celula-acoes">
            <button class="btn btn--claro btn--mini" onclick="formMotorista(${m.id})">Editar</button>
          </div></td>
        </tr>`
      )
      .join("")}</tbody></table>`;
}

function formMotorista(id = null) {
  const m = id ? estado.motoristas.find((x) => x.id === id) : null;
  abrirModal(m ? `Editar ${m.nome}` : "Cadastrar motorista", `
    <form id="form-motorista" class="form-grade">
      <label class="campo-largo">Nome completo <input name="nome" required value="${m ? esc(m.nome) : ""}"></label>
      <label>CNH <input name="cnh" required value="${m ? esc(m.cnh) : ""}" ${m ? "readonly" : ""}></label>
      <label>Categoria
        <select name="categoria_cnh">
          ${["A", "B", "AB", "C", "D", "E"]
            .map((c) => `<option ${m && m.categoria_cnh === c ? "selected" : ""}>${c}</option>`)
            .join("")}
        </select>
      </label>
      <label>Validade da CNH <input type="date" name="validade_cnh" value="${m ? m.validade_cnh || "" : ""}"></label>
      <label>Telefone <input name="telefone" value="${m ? esc(m.telefone || "") : ""}"></label>
      <label>Setor <input name="setor" value="${m ? esc(m.setor || "") : ""}"></label>
      <label>Situação
        <select name="ativo">
          <option value="true" ${!m || m.ativo ? "selected" : ""}>Ativo</option>
          <option value="false" ${m && !m.ativo ? "selected" : ""}>Inativo</option>
        </select>
      </label>
      <div class="campo-largo form-acoes">
        <button type="button" class="btn btn--texto" data-fechar>Cancelar</button>
        <button type="submit" class="btn btn--principal">${m ? "Salvar alterações" : "Cadastrar motorista"}</button>
      </div>
      <div class="campo-largo" id="erro-form"></div>
    </form>`);

  document.getElementById("form-motorista").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = Object.fromEntries(new FormData(e.target));
    dados.ativo = dados.ativo === "true";
    if (!dados.validade_cnh) dados.validade_cnh = null;
    try {
      if (m) {
        delete dados.cnh;
        await api(`/motoristas/${m.id}`, { method: "PUT", body: JSON.stringify(dados) });
        avisar("Motorista atualizado.");
      } else {
        await api("/motoristas", { method: "POST", body: JSON.stringify(dados) });
        avisar("Motorista cadastrado.");
      }
      fecharModal();
      carregarMotoristas();
    } catch (err) {
      document.getElementById("erro-form").innerHTML =
        `<p class="form-erro">${esc(err.message)}</p>`;
    }
  });
}

document.getElementById("btn-novo-motorista").addEventListener("click", () => formMotorista());

/* ──────────────────────────── deslocamentos ──────────────────────────── */

async function carregarDeslocamentos() {
  if (!estado.veiculos.length) {
    estado.veiculos = await api("/veiculos").catch(() => []);
    estado.motoristas = await api("/motoristas").catch(() => []);
    preencherSelects();
  }
  const f = document.getElementById("filtros-deslocamento");
  const params = new URLSearchParams(
    Object.fromEntries([...new FormData(f).entries()].filter(([, v]) => v !== ""))
  );
  try {
    estado.deslocamentos = await api(`/deslocamentos?${params}`);
    desenharDeslocamentos();
  } catch (e) {
    avisar(e.message, "erro");
  }
}

function desenharDeslocamentos() {
  const alvo = document.getElementById("lista-deslocamentos");
  if (!estado.deslocamentos.length) {
    alvo.innerHTML = `<p class="linha-vazia">Nenhum deslocamento encontrado com esses filtros.</p>`;
    return;
  }
  alvo.innerHTML = `<table>
    <thead><tr>
      <th>Saída</th><th>Retorno</th><th>Destino</th><th>Veículo</th>
      <th>Motorista</th><th>Finalidade</th><th>Km</th><th>Situação</th><th></th>
    </tr></thead>
    <tbody>${estado.deslocamentos
      .map(
        (d) => `<tr>
        <td>${dataBR(d.data_saida)}</td>
        <td>${dataBR(d.data_retorno)}</td>
        <td>${esc(d.destino)}</td>
        <td><span class="placa">${esc(d.veiculo.placa)}</span></td>
        <td>${esc(d.motorista.nome)}</td>
        <td>${rotulo(d.finalidade)}</td>
        <td>${d.km_percorrido != null ? num(d.km_percorrido, 1) : "—"}</td>
        <td><span class="marca marca--${d.status}">${rotulo(d.status)}</span></td>
        <td><div class="celula-acoes">
          ${
            d.status === "previsto" || d.status === "em_andamento"
              ? `<button class="btn btn--claro btn--mini" onclick="concluirViagem(${d.id})">Concluir</button>`
              : ""
          }
          <button class="btn btn--texto btn--mini" onclick="excluirDeslocamento(${d.id})">Excluir</button>
        </div></td>
      </tr>`
      )
      .join("")}</tbody></table>`;
}

function preencherSelects() {
  document.querySelectorAll('[data-fonte="veiculos"]').forEach((s) => {
    const atual = s.value;
    s.innerHTML =
      `<option value="">Todos</option>` +
      estado.veiculos
        .map((v) => `<option value="${v.id}">${esc(v.placa)} — ${esc(v.modelo)}</option>`)
        .join("");
    s.value = atual;
  });
  document.querySelectorAll('[data-fonte="motoristas"]').forEach((s) => {
    const atual = s.value;
    s.innerHTML =
      `<option value="">Todos</option>` +
      estado.motoristas.map((m) => `<option value="${m.id}">${esc(m.nome)}</option>`).join("");
    s.value = atual;
  });
}

async function formDeslocamento() {
  if (!estado.veiculos.length) estado.veiculos = await api("/veiculos").catch(() => []);
  if (!estado.motoristas.length) estado.motoristas = await api("/motoristas").catch(() => []);

  const disponiveis = estado.veiculos.filter(
    (v) => v.status === "disponivel" || v.status === "em_viagem"
  );
  const ativos = estado.motoristas.filter((m) => m.ativo);

  if (!disponiveis.length || !ativos.length) {
    abrirModal("Cadastros pendentes", `
      <p>Para registrar um deslocamento é preciso ter ao menos um veículo em operação e um motorista ativo.</p>
      <div class="form-acoes">
        <button class="btn btn--claro" onclick="fecharModal();navegar('veiculos')">Ir para veículos</button>
        <button class="btn btn--principal" onclick="fecharModal();navegar('motoristas')">Ir para motoristas</button>
      </div>`);
    return;
  }

  const hoje = new Date().toISOString().slice(0, 10);
  abrirModal("Registrar deslocamento", `
    <form id="form-deslocamento" class="form-grade">
      <label>Veículo
        <select name="veiculo_id" required>
          ${disponiveis
            .map((v) => `<option value="${v.id}">${esc(v.placa)} — ${esc(v.marca)} ${esc(v.modelo)}</option>`)
            .join("")}
        </select>
      </label>
      <label>Motorista
        <select name="motorista_id" required>
          ${ativos.map((m) => `<option value="${m.id}">${esc(m.nome)}</option>`).join("")}
        </select>
      </label>
      <label class="campo-largo">Destino
        <input name="destino" required placeholder="Cidade, órgão ou endereço">
      </label>
      <label>Data de saída <input type="date" name="data_saida" required value="${hoje}"></label>
      <label>Data de retorno <input type="date" name="data_retorno"></label>
      <label>Finalidade
        <select name="finalidade" required>
          ${["administrativa", "operacional", "manutencao", "entrega", "visita_tecnica", "outros"]
            .map((f) => `<option value="${f}">${rotulo(f)}</option>`)
            .join("")}
        </select>
      </label>
      <label>Situação
        <select name="status">
          <option value="previsto">Prevista</option>
          <option value="em_andamento">Em andamento</option>
          <option value="realizado">Realizada</option>
        </select>
      </label>
      <label>Km inicial <input type="number" step="0.1" min="0" name="km_inicial" placeholder="Km atual do veículo"></label>
      <label>Km final <input type="number" step="0.1" min="0" name="km_final"></label>
      <label class="campo-largo">Observação <textarea name="observacao" placeholder="Passageiros, carga, autorização…"></textarea></label>
      <div class="campo-largo form-acoes">
        <button type="button" class="btn btn--texto" data-fechar>Cancelar</button>
        <button type="submit" class="btn btn--principal">Registrar deslocamento</button>
      </div>
      <div class="campo-largo" id="erro-form"></div>
    </form>`);

  document.getElementById("form-deslocamento").addEventListener("submit", async (e) => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(e.target));
    d.veiculo_id = Number(d.veiculo_id);
    d.motorista_id = Number(d.motorista_id);
    d.km_inicial = d.km_inicial === "" ? null : Number(d.km_inicial);
    d.km_final = d.km_final === "" ? null : Number(d.km_final);
    if (!d.data_retorno) d.data_retorno = null;
    if (!d.observacao) d.observacao = null;
    try {
      await api("/deslocamentos", { method: "POST", body: JSON.stringify(d) });
      avisar("Deslocamento registrado.");
      fecharModal();
      carregarDeslocamentos();
    } catch (err) {
      document.getElementById("erro-form").innerHTML =
        `<p class="form-erro">${esc(err.message)}</p>`;
    }
  });
}

async function concluirViagem(id) {
  const d = estado.deslocamentos.find((x) => x.id === id);
  abrirModal(`Concluir viagem para ${d.destino}`, `
    <form id="form-concluir" class="form-grade">
      <label>Data de retorno
        <input type="date" name="data_retorno" required value="${new Date().toISOString().slice(0, 10)}">
      </label>
      <label>Km final
        <input type="number" step="0.1" name="km_final" required
          min="${d.km_inicial ?? 0}" value="${d.km_inicial ?? 0}">
      </label>
      <div class="campo-largo form-acoes">
        <button type="button" class="btn btn--texto" data-fechar>Cancelar</button>
        <button type="submit" class="btn btn--principal">Concluir viagem</button>
      </div>
      <div class="campo-largo" id="erro-form"></div>
    </form>`);

  document.getElementById("form-concluir").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const params = new URLSearchParams({
      km_final: f.get("km_final"),
      data_retorno: f.get("data_retorno"),
    });
    try {
      await api(`/deslocamentos/${id}/concluir?${params}`, { method: "POST" });
      avisar("Viagem concluída.");
      fecharModal();
      carregarDeslocamentos();
    } catch (err) {
      document.getElementById("erro-form").innerHTML =
        `<p class="form-erro">${esc(err.message)}</p>`;
    }
  });
}

async function excluirDeslocamento(id) {
  if (!confirm("Excluir este deslocamento do histórico?")) return;
  try {
    await api(`/deslocamentos/${id}`, { method: "DELETE" });
    avisar("Deslocamento excluído.");
    carregarDeslocamentos();
  } catch (e) {
    avisar(e.message, "erro");
  }
}

document.getElementById("btn-novo-deslocamento").addEventListener("click", formDeslocamento);
document.getElementById("filtros-deslocamento").addEventListener("submit", (e) => {
  e.preventDefault();
  carregarDeslocamentos();
});
document.getElementById("filtros-deslocamento").addEventListener("reset", () =>
  setTimeout(carregarDeslocamentos, 0)
);

/* ────────────────────────────────── início ────────────────────────────────── */
(async function iniciar() {
  estado.veiculos = await api("/veiculos").catch(() => []);
  estado.motoristas = await api("/motoristas").catch(() => []);
  preencherSelects();
  carregarPainel();
})();
