# Plano de testes — Rodagem

## 1. Estratégia

| Nível | Ferramenta | Onde | O que cobre |
|---|---|---|---|
| API / integração | pytest + `TestClient` | `tests/backend/` | Rotas, validação, regras de negócio, critérios de aceite |
| Execução real | uvicorn + requisições HTTP | manual/script, registrado em `execucao.md` | Servidor sobe, cria o banco em arquivo, serve a interface |
| Interface | navegador | registrado em `execucao.md` | Tela carrega, chama a API, sem erro no console |

Regras:
- Os testes usam SQLite em memória (`tests/conftest.py`, `StaticPool` + `dependency_overrides`) e nunca tocam `backend/data/`.
- Toda nova regra de negócio ganha teste; o nome do teste carrega o ID abaixo (`test_t0_01_…`, `test_ca1_…`).
- Dados de teste são fictícios (placas e CNHs inventadas, nomes genéricos).

## 2. Como executar (PowerShell)

```powershell
.\scripts\verificar.ps1          # versões + pytest -v
.\.venv\Scripts\python.exe -m pytest -v
```

## 3. Casos

### Sprint 0 — fumaça

| ID | Caso | Esperado | Arquivo |
|---|---|---|---|
| T0-01 | `GET /api/saude` | 200, `status=ok`, `banco=ok` (executa `SELECT 1`) | `tests/backend/test_saude.py` |
| T0-02 | `GET /` | 200, HTML contendo "Rodagem" | idem |
| T0-03 | `GET /static/css/styles.css` e `/static/js/app.js` | 200 | idem |
| T0-04 | `GET /openapi.json` | 200, contém `/api/saude` | idem |
| T0-05 | Servidor real | sobe, cria `backend/data/gestao_veiculos.db`, `/docs` 200 | manual, `execucao.md` |
| T0-06 | Interface no navegador | mostra "API: ok · Banco: ok", console sem erros | manual, `execucao.md` |

### Sprint 1 — cadastros (planejado)

| ID | Caso | Esperado |
|---|---|---|
| CA01-a | Criar veículo válido | 201, situação `disponivel`, aparece na listagem |
| CA01-b | Placa duplicada (inclusive com hífen/minúscula) | 409 com mensagem de duplicidade |
| CA01-c | Placa fora de `ABC1234`/`ABC1D23` | 422, nada gravado |
| T1-01 | Consultar veículo inexistente | 404 |
| T1-02 | Editar veículo | 200, campos alterados persistidos |
| T1-03 | Excluir veículo sem histórico | 204, some da listagem |
| T1-04 | CRUD de motorista + CNH duplicada | 201/200/204; duplicada → 409 |

### Sprint 2 — deslocamentos e painel (planejado)

| ID | Caso | Esperado |
|---|---|---|
| CA02-a | Registrar deslocamento válido | 201, histórico traz veículo e motorista |
| CA02-b | Retorno antes da saída | 422 |
| CA02-c | Mesmo veículo em intervalo ocupado | 409 citando o conflito |
| CA02-d | Filtro por destino | só registros correspondentes |
| T2-01 | Veículo em manutenção / motorista inativo | 409 |
| T2-02 | Concluir viagem | km do veículo atualizado, situação `disponivel` |
| T2-03 | Excluir veículo/motorista com histórico | 409 |
| CA03-a | Indicadores com base conhecida | totais e taxas conferem com cálculo manual |
| CA03-b | Mudar período | tudo recalculado só com `data_saida` no intervalo |

## 4. Resultados

Os resultados de cada execução (passou, falhou, corrigido) ficam em `docs/execucao.md`.
