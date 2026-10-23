# Registro de execução

Resultados reais das verificações, por sprint. Só entra aqui o que foi executado e observado.

---

## Sprint 0 — 2026-10-23

### 1. Ambiente verificado

| Item | Resultado | Como |
|---|---|---|
| Sistema | Windows 11 Pro 10.0.26200 | `platform.platform()` |
| Python | 3.15.1 (único instalado; `py -0p`) | `python --version` |
| pip | 26.2.2 | `pip --version` |
| Git | 2.55.0.windows.5 | `git --version` |
| Node / npm | v22.10.0 / 10.9.0 — não usado (ADR-006) | `node --version` |
| PowerShell | 5.1.26100.9444, ExecutionPolicy `RemoteSigned` (CurrentUser) | `$PSVersionTable` |

### 2. Verificações executadas

| # | Verificação | Resultado |
|---|---|---|
| V1 | Instalar dependências como wheel no Python 3.15 | ❌ → ✅ (ver problema P1) |
| V2 | `.\scripts\configurar.ps1` | ✅ cria `.venv` e instala `backend\requirements.txt` |
| V3 | `.\scripts\verificar.ps1` → `pytest -v` | ✅ **4 passed**, 0 failed, 1 warning (P3) |
| V4 | Servidor real (uvicorn, porta 8765): `GET /api/saude` | ✅ `{"status":"ok","banco":"ok","versao":"0.0.1"}` |
| V5 | Servidor real: `GET /` e `GET /docs` | ✅ 200 e 200 |
| V6 | Banco em arquivo criado na inicialização | ✅ `backend/data/gestao_veiculos.db` (0 bytes — ainda sem tabelas) |
| V7 | Interface no navegador (porta 8000) | ✅ exibe "API: ok · Banco: ok · versão 0.0.1"; console sem erros |
| V8 | Clone limpo do repositório + configurar + pytest + servidor | ❌ → ✅ (ver P2) |
| V9 | Varredura de segredos nos arquivos versionados | ✅ nenhuma ocorrência (ver §4) |
| V10 | `.gitignore` | ✅ ignora `.venv/`, `.pytest_cache/`, `__pycache__/`, `*.db` |

Testes que passaram (V3, saída do `pytest -v`):

```
tests/backend/test_saude.py::test_t0_01_saude_responde_com_banco_ok PASSED
tests/backend/test_saude.py::test_t0_02_interface_e_servida_na_raiz PASSED
tests/backend/test_saude.py::test_t0_03_arquivos_estaticos_sao_servidos PASSED
tests/backend/test_saude.py::test_t0_04_documentacao_openapi_disponivel PASSED
4 passed, 1 warning in 0.16s
```

### 3. Problemas encontrados e correções

| ID | Problema | Causa | Correção | Situação |
|---|---|---|---|---|
| P1 | `pip install uvicorn[standard]` → `ResolutionImpossible` | Os extras compilados (`uvloop`, `httptools`, `watchfiles`) não têm wheel para Python 3.15 | `uvicorn` sem `[standard]`; versões atuais fixadas em `backend/requirements.txt` (ADR-004) | ✅ Corrigido |
| P2 | Clone em pasta temporária profunda: `ImportError: DLL load failed … _collections_cy: O nome do arquivo ou a extensão é muito grande` | Caminho da DLL do SQLAlchemy dentro do `.venv` com 275 caracteres, acima do limite de 260 do Windows | Repetido em caminho curto (`%TEMP%\rodagem-clone`): 4 passed, API ok, banco criado. Na pasta atual o mesmo arquivo tem 171 caracteres. Registrado no README (Solução de problemas) | ✅ Contornado; não altera o código |
| P3 | Aviso `StarletteDeprecationWarning`: `httpx` no TestClient está obsoleto, recomenda `httpx2` | Mudança recente no Starlette 1.9 | Nenhuma ainda — trocar exige nova dependência (débito D-02 no backlog) | ⏳ Aberto, não bloqueia |
| P4 | Risco de o pytest coletar `legado/tests/` | Testes antigos importam `app.*` com outra estrutura | `pytest.ini` com `testpaths = tests` | ✅ Prevenido |
| P5 | Scripts `.ps1` com acento seriam lidos errado no PowerShell 5.1 | PS 5.1 lê `.ps1` sem BOM como ANSI | Textos dos scripts sem acentos | ✅ Prevenido |

### 4. Segurança e dados

- Varredura com `git grep` por `password`, `senha`, `secret`, `api_key`, `token`, chaves privadas, `ghp_` e domínios institucionais nos arquivos versionados: **nenhuma ocorrência**.
- Banco, `.venv` e caches confirmados como ignorados por `git status --ignored`.
- Autor dos commits: `elisfarias-ia <elisfarias-ia@users.noreply.github.com>`, configurado só neste repositório (`git config` local). O e-mail global institucional não foi alterado nem usado.
- O `seed.py` do legado usa nomes, CNHs e telefones fictícios; ainda não foi portado.

### 5. Git

| Passo | Resultado |
|---|---|
| `git init -b main` | ✅ |
| Remoto `origin` → `https://github.com/elisfarias-ia/unidade8-desafio03.git` | ✅ acessível e vazio antes do primeiro push (`git ls-remote` sem refs) |
| Commits | `chore: arquivar MVP anterior em legado/` · `feat: estrutura e documentação da Sprint 0` · `docs: registro de execução da Sprint 0` |
| Push | ✅ `git push -u origin main` — `origin/main` em `46f0d98`, igual ao local (`git ls-remote`) |

### 6. O que **não** foi validado na Sprint 0

- Nenhuma regra de negócio (não existe código de domínio ainda).
- Responsividade e acessibilidade da interface (só há uma página de status).
- Outras versões de Python além da 3.15.1 e outros sistemas além do Windows 11.
- Código em `legado/` — não foi executado nem testado neste repositório.

---

## Sprint 1 — Entidades, persistência e API — 2026-10-23

Escopo conforme ADR-008 (S1 = API + persistência + testes de API; telas na S2).

### 1. Gate — comandos e resultados

| # | Comando / verificação | Resultado |
|---|---|---|
| G1 | `ruff check .` | 1ª execução: ❌ 10 × E501 (linha longa) → corrigido → ✅ `All checks passed!` |
| G2 | `ruff format --check .` | ✅ `27 files already formatted` (após `ruff format .`) |
| G3 | `pytest -v` | 1ª execução: ❌ `1 failed, 38 passed` (P7) → corrigido → ✅ **`41 passed`**, 0 failed |
| G4 | Isolamento: banco real tirado do lugar, suíte inteira rodada | 1ª tentativa: ❌ arquivo recriado (P6/P8) → corrigido → ✅ `banco criado pelos testes? False` |
| G5 | `.\scripts\seed.ps1` em banco novo, depois de novo | ✅ `Dados fictícios criados: 6 veículos, 4 motoristas, 156 deslocamentos.` / 2ª vez: `O banco já possui dados. Nada foi alterado.` |
| G6 | Roteiro HTTP no **servidor real** (uvicorn, porta 8770, SQLite em `backend/data/`) | ✅ `FALHAS: 0` — detalhes em §2 |
| G7 | Parar o servidor, subir de novo, buscar o registro criado antes | ✅ `encontrado: [(7, 'PER1S00', 'Persistencia')]` — persistência confirmada |
| G8 | Log do uvicorn procurando respostas 500 | ✅ `erros 500 no log: 0` |
| G9 | `.\scripts\verificar.ps1` (ferramentas + lint + formato + testes) | ✅ `Resumo: lint=0 formato=0 testes=0` |

Distribuição do seed (consulta SQL direta): `cancelado 6 · em_andamento 1 · previsto 30 · realizado 119`; veículo `TST6006` em `manutencao`, `TST2B02` em `em_viagem` (o deslocamento em andamento). Invariante conferida via API: **0** pares de deslocamentos ativos sobrepostos no mesmo veículo.

### 2. Funções conferidas na prática (servidor real, respostas observadas)

| Operação | Requisição | Status | Observado |
|---|---|---|---|
| Criar veículo | `POST /api/veiculos` placa `zzz-9a99` | 201 | placa salva como `ZZZ9A99`, `disponivel` |
| Placa duplicada | `POST /api/veiculos` `ZZZ9A99` | 409 | "Já existe um veículo com a placa ZZZ9A99. Confira a placa ou edite o cadastro existente." |
| Placa inválida | `POST /api/veiculos` `12ABCDE` | 422 | "placa: Placa inválida. Use o padrão ABC1234 ou ABC1D23." |
| Consultar / editar | `GET` / `PUT /api/veiculos/7` | 200 / 200 | após editar: km `1000.0`, cor `Azul` |
| Excluir / consultar | `DELETE` / `GET /api/veiculos/7` | 204 / 404 | "Veículo #7 não encontrado." |
| Motorista: criar, duplicar, consultar, editar, excluir | `/api/motoristas` | 201 / 409 / 200 / 200 / 204 | CNH `000.000.009-99` salva como `00000000999`; categoria `b` → `B` |
| Registrar deslocamento | `POST /api/deslocamentos` | 201 | km inicial herdado do veículo (`22802.0`) |
| Conflito de agenda | mesmo veículo e datas | 409 | "Conflito de agenda: o veículo já está no deslocamento #157 … Escolha outras datas ou outro veículo." |
| Retorno antes da saída | | 422 | "A data de retorno não pode ser anterior à data de saída." |
| Veículo em manutenção | `TST6006` | 409 | "O veículo TST6006 está em manutenção e não pode ser escalado. …" |
| Motorista inativo | `Diego Exemplo` | 409 | "Diego Exemplo está inativo(a) e não pode ser escalado(a). …" |
| Filtro por destino | `GET /api/deslocamentos?destino=destino teste` | 200 | 1 resultado |
| Editar / concluir | `PUT` / `POST …/157/concluir` | 200 / 200 | `realizado`, `km_percorrido 42.5`, km do veículo `22844.5` |
| Excluir veículo com histórico | `DELETE /api/veiculos/3` | 409 | "O veículo TST3C03 tem 28 deslocamento(s) registrado(s) e não pode ser excluído. Mude a situação para inativo." |
| Excluir deslocamento | `DELETE /api/deslocamentos/157` | 204 | |

Ao final, os registros de teste foram removidos e o km do veículo restaurado: totais voltaram a `veiculos 6 | deslocamentos 156`.

### 3. Problemas encontrados e correções

| ID | Problema | Causa | Correção | Situação |
|---|---|---|---|---|
| P6 | **Os testes criavam tabelas no banco real.** `backend/data/gestao_veiculos.db` apareceu com 45 KB e 3 tabelas vazias, gravado no horário do `pytest` | O `TestClient` executa o `lifespan`, que chamava `criar_tabelas()` no engine real | `conftest.py` substitui `criar_tabelas` no teste e registra uma **trava** que reprova qualquer conexão com o engine real. Prova: com a substituição desligada de propósito, a trava gerou `1 passed, 40 errors`; religada, `41 passed` e nenhum arquivo criado | ✅ Corrigido + teste de regressão T1-32/T1-33 |
| P7 | Mensagem "Deve ser maior ou igual a **0.0**." em campo decimal | Limite `float` formatado direto | `erros.py` formata limites decimais (`0.0` → `0`, vírgula decimal) | ✅ Corrigido (T1-02) |
| P8 | Após P6, o arquivo do banco ainda aparecia (0 bytes) | O primeiro teste da trava conectava no engine real; o SQLite cria o arquivo antes do evento `connect` disparar | Teste reescrito para conferir que o arquivo não muda, sem abrir o engine real | ✅ Corrigido |
| P9 | Mensagem de conflito com código interno ("está em **manutencao**") | `enum.value` exibido direto | Rótulos legíveis ("em manutenção", "inativo") | ✅ Corrigido (T1-24) |
| P10 | 10 avisos E501 do ruff | Mensagens longas | Quebra de linhas + `ruff format` | ✅ Corrigido |
| — | Corrigidos em relação ao `legado/` | PUT com veículo inexistente → 500; campo obrigatório editado para `null` → 500; conclusão aceitava retorno antes da saída corrigindo sem avisar; não permitia editar placa/CNH; conflito de agenda checado mesmo para deslocamento cancelado/realizado | Regras reescritas com testes T1-07, T1-27, T1-29, T1-05, T1-13, T1-20 | ✅ |
| P3 | Aviso `httpx` → `httpx2` do Starlette (da Sprint 0) | — | Continua aberto (D-02) | ⏳ Não bloqueia |

### 4. Dados e banco

- O banco com as 3 tabelas vazias criado por P6 não continha dados de ninguém (contagem 0 em todas as tabelas). Ele foi movido, não apagado, para a pasta temporária da sessão. O banco atual foi criado do zero pelo seed com dados **fictícios**: placas `TST…`, CNHs `000…`, telefones DDD `00`, nomes "… Exemplo".
- `backend/data/gestao_veiculos.db` continua fora do git.

### 5. O que **não** foi validado na Sprint 1

- Nenhuma tela de CRUD (escopo da S2, ADR-008); a página inicial só mostra a situação da API.
- Indicadores/painel (S3) e desempenho com 10 mil deslocamentos (RNF04, S3).
- Concorrência de escrita (dois usuários ao mesmo tempo): fora do uso monoposto do MVP.
- Outras versões de Python além da 3.15.1.
