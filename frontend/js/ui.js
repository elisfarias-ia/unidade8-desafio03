// Utilidades de apresentação: escape, formatação, rótulos, formulários, diálogos e avisos.

// Escapa strings vindas da API antes de inseri-las no HTML.
export function esc(valor) {
  return String(valor ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// ---------- Rótulos de exibição dos códigos da API ----------
export const SITUACAO_VEICULO = {
  disponivel: { rotulo: "Disponível", selo: "ok" },
  em_viagem: { rotulo: "Em viagem", selo: "info" },
  manutencao: { rotulo: "Em manutenção", selo: "alerta" },
  inativo: { rotulo: "Inativo", selo: "neutro" },
};

export const SITUACAO_DESLOCAMENTO = {
  previsto: { rotulo: "Previsto", selo: "info" },
  em_andamento: { rotulo: "Em andamento", selo: "alerta" },
  realizado: { rotulo: "Realizado", selo: "ok" },
  cancelado: { rotulo: "Cancelado", selo: "neutro" },
};

export const FINALIDADES = {
  administrativa: "Administrativa",
  operacional: "Operacional",
  manutencao: "Manutenção",
  entrega: "Entrega",
  visita_tecnica: "Visita técnica",
  outros: "Outros",
};

export const CATEGORIAS_CNH = ["A", "B", "C", "D", "E", "AB", "AC", "AD", "AE"];

export function selo(mapa, codigo) {
  const item = mapa[codigo] ?? { rotulo: codigo, selo: "neutro" };
  return `<span class="selo selo--${item.selo}">${esc(item.rotulo)}</span>`;
}

// ---------- Formatação ----------
export function formatarData(iso) {
  if (!iso) return "—";
  const [ano, mes, dia] = String(iso).slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

export function formatarKm(valor) {
  if (valor === null || valor === undefined) return "—";
  return Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}

export function hojeIso() {
  const d = new Date();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

// ---------- Selects ----------
export function preencherOpcoes(select, itens, { vazio } = {}) {
  const opcoes = vazio === undefined ? [] : [`<option value="">${esc(vazio)}</option>`];
  for (const [valor, rotulo] of itens) {
    opcoes.push(`<option value="${esc(valor)}">${esc(rotulo)}</option>`);
  }
  select.innerHTML = opcoes.join("");
}

// ---------- Formulários ----------
// Lê os campos do formulário. Vazio vira null; data-tipo converte número/inteiro/bool.
export function lerFormulario(form) {
  const dados = {};
  for (const el of form.elements) {
    if (!el.name || el.disabled) continue;
    const tipo = el.dataset.tipo;
    if (tipo === "bool" || el.type === "checkbox") {
      dados[el.name] = el.checked;
      continue;
    }
    const texto = el.value.trim();
    if (texto === "") dados[el.name] = null;
    else if (tipo === "inteiro") dados[el.name] = Number.parseInt(texto, 10);
    else if (tipo === "numero") dados[el.name] = Number(texto.replace(",", "."));
    else dados[el.name] = texto;
  }
  return dados;
}

export function preencherFormulario(form, dados) {
  for (const el of form.elements) {
    if (!el.name) continue;
    const valor = dados?.[el.name];
    if (el.type === "checkbox") el.checked = Boolean(valor);
    else el.value = valor === null || valor === undefined ? "" : String(valor);
  }
}

export function semNulos(dados) {
  return Object.fromEntries(Object.entries(dados).filter(([, v]) => v !== null));
}

export function limparErros(form) {
  const alerta = form.querySelector("[data-alerta]");
  if (alerta) {
    alerta.hidden = true;
    alerta.textContent = "";
  }
  for (const el of form.querySelectorAll("[aria-invalid]")) {
    el.removeAttribute("aria-invalid");
    el.removeAttribute("aria-describedby");
  }
  for (const msg of form.querySelectorAll(".campo__erro")) msg.remove();
}

// Mostra o detail da API no topo e marca os campos citados em erros[].
export function mostrarErros(form, erro) {
  limparErros(form);
  const alerta = form.querySelector("[data-alerta]");
  if (alerta) {
    alerta.textContent = erro.message;
    alerta.hidden = false;
    alerta.tabIndex = -1; // permite levar o foco até a mensagem
  }
  let primeiro = null;
  for (const { campo, mensagem } of erro.erros ?? []) {
    const el = campo ? form.elements.namedItem(campo) : null;
    if (!el || !el.id) continue;
    const idMsg = `${el.id}-erro`;
    el.setAttribute("aria-invalid", "true");
    el.setAttribute("aria-describedby", idMsg);
    const p = document.createElement("p");
    p.className = "campo__erro";
    p.id = idMsg;
    p.textContent = mensagem;
    el.closest(".campo")?.append(p);
    primeiro ??= el;
  }
  (primeiro ?? alerta)?.focus?.();
  if (!primeiro && alerta) alerta.scrollIntoView({ block: "nearest" });
}

// ---------- Diálogos ----------
export function ligarFechar(dialogo) {
  for (const botao of dialogo.querySelectorAll("[data-fechar]")) {
    botao.addEventListener("click", () => dialogo.close());
  }
}

export function confirmar(mensagem, rotuloAcao = "Excluir") {
  const dialogo = document.getElementById("dialogo-confirmar");
  dialogo.querySelector("[data-mensagem]").textContent = mensagem;
  dialogo.querySelector('button[value="sim"]').textContent = rotuloAcao;
  dialogo.returnValue = "";
  dialogo.showModal();
  dialogo.querySelector('button[value="nao"]').focus();
  // Resolve no clique (imediato); o evento "close" cobre o Esc, que fecha sem clique.
  // O "close" é entregue junto com a renderização de quadros, então não é confiável sozinho.
  return new Promise((resolver) => {
    const ouvintes = new AbortController();
    const decidir = (confirmado) => {
      ouvintes.abort();
      resolver(confirmado);
    };
    const opcoes = { signal: ouvintes.signal };
    dialogo.querySelector('button[value="sim"]').addEventListener("click", () => decidir(true), opcoes);
    dialogo.querySelector('button[value="nao"]').addEventListener("click", () => decidir(false), opcoes);
    dialogo.addEventListener("close", () => decidir(dialogo.returnValue === "sim"), opcoes);
  });
}

// Envia um formulário em diálogo: trava o botão, mostra erros e só fecha se der certo.
export function aoEnviar(form, acao) {
  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const botao = form.querySelector('button[type="submit"]');
    botao.disabled = true;
    try {
      await acao(lerFormulario(form));
      form.closest("dialog")?.close();
    } catch (erro) {
      mostrarErros(form, erro);
    } finally {
      botao.disabled = false;
    }
  });
}

// ---------- Avisos ----------
export function avisar(mensagem, tipo = "ok") {
  const area = document.getElementById("avisos");
  const aviso = document.createElement("div");
  aviso.className = tipo === "erro" ? "aviso aviso--erro" : "aviso";
  aviso.textContent = mensagem;
  area.append(aviso);
  setTimeout(() => aviso.classList.add("aviso--saindo"), 3500);
  setTimeout(() => aviso.remove(), 4000);
}

export function linhaVazia(colunas, texto) {
  return `<tr><td class="tabela__vazia" colspan="${colunas}">${esc(texto)}</td></tr>`;
}

// Atrasa chamadas repetidas (busca enquanto digita).
export function adiar(funcao, ms = 300) {
  let id;
  return (...args) => {
    clearTimeout(id);
    id = setTimeout(() => funcao(...args), ms);
  };
}
