// Acesso à API. Toda regra de negócio fica no backend; aqui só transporte e erros.

export class ErroApi extends Error {
  constructor(status, detalhe, erros = []) {
    super(detalhe);
    this.status = status;
    this.erros = erros; // [{campo, mensagem}] nas respostas 422
  }
}

export async function api(caminho, { metodo = "GET", corpo, parametros } = {}) {
  let url = caminho;
  if (parametros) {
    const consulta = new URLSearchParams();
    for (const [chave, valor] of Object.entries(parametros)) {
      if (valor !== null && valor !== undefined && valor !== "") consulta.set(chave, valor);
    }
    const texto = consulta.toString();
    if (texto) url += `?${texto}`;
  }

  let resposta;
  try {
    resposta = await fetch(url, {
      method: metodo,
      headers: corpo === undefined ? {} : { "Content-Type": "application/json" },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  } catch {
    throw new ErroApi(0, "Não foi possível falar com o servidor. Confira se a aplicação está rodando.");
  }

  if (resposta.status === 204) return null;
  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const detalhe = typeof dados?.detail === "string"
      ? dados.detail
      : `Erro inesperado do servidor (HTTP ${resposta.status}).`;
    throw new ErroApi(resposta.status, detalhe, dados?.erros ?? []);
  }
  return dados;
}
