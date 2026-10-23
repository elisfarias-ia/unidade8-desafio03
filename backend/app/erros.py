"""Respostas 422 em português, no mesmo formato dos erros 404/409.

Formato: {"detail": "<primeira mensagem>", "erros": [{"campo": ..., "mensagem": ...}]}
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

MENSAGENS = {
    "missing": "Campo obrigatório.",
    "string_too_short": "Deve ter pelo menos {min_length} caractere(s).",
    "string_too_long": "Deve ter no máximo {max_length} caracteres.",
    "string_type": "Informe um texto.",
    "greater_than_equal": "Deve ser maior ou igual a {ge}.",
    "less_than_equal": "Deve ser menor ou igual a {le}.",
    "int_parsing": "Informe um número inteiro.",
    "int_type": "Informe um número inteiro.",
    "int_from_float": "Informe um número inteiro.",
    "float_parsing": "Informe um número.",
    "float_type": "Informe um número.",
    "bool_parsing": "Informe verdadeiro ou falso.",
    "bool_type": "Informe verdadeiro ou falso.",
    "date_parsing": "Data inválida. Use o formato AAAA-MM-DD.",
    "date_from_datetime_parsing": "Data inválida. Use o formato AAAA-MM-DD.",
    "date_type": "Data inválida. Use o formato AAAA-MM-DD.",
    "enum": "Valor inválido. Opções aceitas: {expected}.",
    "json_invalid": "O corpo da requisição não é um JSON válido.",
    "model_attributes_type": "O corpo da requisição deve ser um objeto JSON.",
    "dict_type": "O corpo da requisição deve ser um objeto JSON.",
}


def _traduzir(erro: dict) -> dict:
    local = [str(p) for p in erro.get("loc", ()) if p not in ("body", "query", "path")]
    campo = ".".join(local) or None
    tipo = erro.get("type", "")
    if tipo == "value_error":
        # Mensagens dos nossos validadores já estão em português.
        mensagem = str(erro.get("ctx", {}).get("error", erro.get("msg", "")))
    elif tipo in MENSAGENS:
        # Limites decimais como 0.0 viram "0"; vírgula decimal no padrão brasileiro.
        ctx = {
            chave: (f"{valor:g}".replace(".", ",") if isinstance(valor, float) else valor)
            for chave, valor in erro.get("ctx", {}).items()
        }
        try:
            mensagem = MENSAGENS[tipo].format(**ctx)
        except (KeyError, IndexError):
            mensagem = MENSAGENS[tipo]
    else:
        mensagem = erro.get("msg", "Valor inválido.")
    return {"campo": campo, "mensagem": mensagem}


async def tratar_erro_validacao(_: Request, exc: RequestValidationError) -> JSONResponse:
    erros = [_traduzir(e) for e in exc.errors()]
    primeiro = erros[0] if erros else {"campo": None, "mensagem": "Dados inválidos."}
    resumo = primeiro["mensagem"]
    if primeiro["campo"]:
        resumo = f"{primeiro['campo']}: {resumo}"
    return JSONResponse(status_code=422, content={"detail": resumo, "erros": erros})
