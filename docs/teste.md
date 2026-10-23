# Plano de testes — Rodagem

## 1. Estratégia

| Nível | Ferramenta | Onde | O que cobre |
|---|---|---|---|
| API / integração | pytest + `TestClient` | `tests/backend/` | Rotas, validação, regras de negócio, critérios de aceite |
| Execução real | uvicorn + requisições HTTP | manual/script, registrado em `execucao.md` | Servidor sobe, cria o banco em arquivo, serve a interface |
| Interface | navegador | registrado em `execucao.md` | Tela carrega, chama a API, sem erro no console |

Regras:
- Os testes usam SQLite em memória (`tests/conftest.py`, `StaticPool` + `dependency_overrides`) e nunca tocam `backend/data/`. Uma trava no `conftest.py` reprova qualquer teste que tente conectar no arquivo real.
- Toda nova regra de negócio ganha teste; o nome do teste carrega o ID abaixo (`test_t0_01_…`, `test_ca1_…`).
- Dados de teste são fictícios (placas e CNHs inventadas, nomes genéricos).

## 2. Como executar (PowerShell)

```powershell
.\scripts\verificar.ps1          # versões + pytest -v
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m ruff check .
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

### Sprint 1 — entidades, persistência e API ✅

Arquivos: `tests/backend/test_veiculos.py`, `test_motoristas.py`, `test_deslocamentos.py`, `test_isolamento.py`.

| ID | Caso | Esperado |
|---|---|---|
| CA01-a | Criar veículo válido | 201, situação `disponivel`, aparece na listagem |
| CA01-b | Placa duplicada (com hífen/minúscula) | 409 citando a placa |
| CA01-c | Placas fora de `ABC1234`/`ABC1D23` | 422 no campo `placa`, nada gravado |
| T1-01 | Placa nos dois padrões | aceita e normalizada (`abc-1234` → `ABC1234`) |
| T1-02 | Campos ausentes/fora de faixa | 422 com mensagens em português por campo |
| T1-03 | Consultar por id / inexistente | 200 / 404 |
| T1-04 | Busca por texto e filtro de situação | só os correspondentes |
| T1-05 | Editar veículo (inclusive placa) | 200; campos não enviados ficam iguais |
| T1-06 | Editar para placa de outro veículo | 409 |
| T1-07 | Editar campo obrigatório para `null` | 422 (antes viraria erro 500) |
| T1-08 | Editar inexistente | 404 |
| T1-09 | Excluir sem histórico | 204, depois 404 |
| T1-10 | Cadastrar e listar motorista | 201, `ativo=true` |
| T1-11 | CNH normalizada e duplicada | `000.000.000-01` → `00000000001`; duplicada 409 |
| T1-12 | CNH ≠ 11 dígitos, categoria inválida | 422 com mensagem específica |
| T1-13 | Consultar/editar/inexistente | 200 / 404 |
| T1-14 | Filtro `apenas_ativos` e busca | só os correspondentes |
| T1-15 | Editar para CNH de outro | 409 |
| T1-16 | Excluir motorista sem histórico | 204 |
| CA02-a | Registrar deslocamento | 201, km inicial herdado, histórico traz veículo e motorista |
| CA02-b | Retorno antes da saída | 422 |
| CA02-c | Mesmo veículo em intervalo ocupado | 409 citando o deslocamento conflitante; dia seguinte livre |
| CA02-d | Filtro por destino | só os correspondentes |
| T1-20 | Filtros combinados (finalidade, período, situação, veículo, motorista) | corretos; período invertido 422 |
| T1-21 | Obrigatórios e finalidade inválida | 422 com opções aceitas |
| T1-22 | km final < inicial (informado ou herdado) | 422 |
| T1-23 | `realizado` sem data de retorno | 422 |
| T1-24 | Veículo em manutenção / motorista inativo | 409 com mensagem legível |
| T1-25 | Veículo/motorista inexistente | 404 |
| T1-26 | `em_andamento` ocupa o veículo; concluir libera e atualiza km | `em_viagem` → `disponivel`, km do veículo = km final; concluir de novo 409 |
| T1-27 | Concluir com km/data incoerentes, sem km, cancelado, inexistente | 422 / 422 / 422 / 409 / 404 |
| T1-28 | Editar deslocamento; edição recusada não grava | 200; 422/409 sem efeito colateral |
| T1-29 | Editar para veículo inexistente | 404 (no legado gerava 500) |
| T1-30 | Excluir veículo/motorista com histórico; excluir deslocamento | 409; 204; depois exclusão liberada |
| T1-31 | Excluir deslocamento em andamento | veículo volta a `disponivel` |
| T1-32 | Gravar pela API durante o teste | arquivo `backend/data/*.db` não muda |
| T1-33 | Trava de conexão ativa | listener registrado no engine real |
| T1-M | Roteiro HTTP no servidor real + reinício | ver `execucao.md` (manual, reproduzível) |

### Sprint 2 — interface ✅

Automatizados em `tests/backend/test_frontend.py`; os demais, manuais no navegador (registrados em `execucao.md`).

| ID | Caso | Tipo | Esperado |
|---|---|---|---|
| T2-01 | Cada tela carrega dados reais da API | manual | tabelas preenchidas com o seed (6 / 4 / 156) |
| T2-02 | Criar, editar e excluir veículo, motorista e deslocamento pela tela | manual | refletido na API e na tabela |
| T2-03 | Erros 409/422 aparecem no formulário | manual | `detail` no topo, campo marcado |
| T2-04 | Concluir viagem pela tela | manual | km do veículo atualizado (22802 → 22889,5) |
| T2-05 | 375 px, 800 px e 1280 px | manual | sem rolagem horizontal; navegação adequada |
| T2-06 | Teclado e rótulos | manual + T2-12 | foco visível, todo campo com `<label for>` |
| T2-07 | Arquivos do `index.html` servidos | auto | 200 |
| T2-08 | Imports dos módulos JS | auto | arquivos existem; `Content-Type` JavaScript |
| T2-09 | Nomes importados são exportados | auto | nenhum import quebrado |
| T2-10 | Cores só nas variáveis do `:root` | auto | sem hex/rgb fora do `:root` |
| T2-11 | Navegação cobre as 4 telas | auto | links e seções presentes |
| T2-12 | Rótulos associados | auto | nenhum campo sem `<label for>` |
| T2-13 | Cancelar e Esc na confirmação | manual | não excluem (Esc: **NÃO TESTADO** após P15) |

### Sprint 3 — dashboard (planejado)

| ID | Caso | Esperado |
|---|---|---|
| CA03-a | Indicadores com base conhecida | totais e taxas iguais ao cálculo manual |
| CA03-b | Mudar período | tudo recalculado só com `data_saida` no intervalo |
| T3-01 | Base vazia | zeros, sem divisão por zero |
| T3-02 | 10 mil deslocamentos | resposta ≤ 500 ms (RNF04) |

## 4. Resultados

Os resultados de cada execução (passou, falhou, corrigido) ficam em `docs/execucao.md`.
