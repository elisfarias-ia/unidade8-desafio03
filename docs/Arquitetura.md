# Arquitetura — Rodagem

## 1. Visão geral

```
┌────────────────────────────────────────────────────┐
│ Navegador — frontend/ (HTML, CSS, JS puro, sem build) │
└──────────────────────┬─────────────────────────────┘
                       │ fetch / JSON
┌──────────────────────▼─────────────────────────────┐
│ FastAPI — backend/app/main.py                       │
│  ├─ /static e /  → arquivos de frontend/            │
│  └─ /api/...     → routers (a partir da Sprint 1)   │
├─────────────────────────────────────────────────────┤
│ schemas.py (Pydantic v2) — formato e coerência      │
│ routers/   — regras de negócio que consultam o banco│
├─────────────────────────────────────────────────────┤
│ models.py (SQLAlchemy) · sessão por requisição      │
├─────────────────────────────────────────────────────┤
│ SQLite — backend/data/gestao_veiculos.db (FK ativas)│
└─────────────────────────────────────────────────────┘
```

Um único processo (uvicorn) serve API e interface, sem CORS e sem etapa de build.

## 2. Estrutura de pastas

```
Desafio03_Gestao_Veiculos/
├── CLAUDE.md               Instruções para o Claude Code
├── CONTEXTO.md             Concepção original (fonte dos requisitos)
├── README.md               Instalação e execução (Windows/PowerShell)
├── pytest.ini              testpaths=tests, pythonpath=backend
├── ruff.toml               Lint e formatação (ADR-009)
├── backend/
│   ├── requirements.txt    Dependências com versões fixas
│   ├── data/               Banco SQLite local (não versionado)
│   └── app/
│       ├── main.py         FastAPI, routers, /api/saude, frontend estático
│       ├── database.py     Engine, SessionLocal, get_db, PRAGMA FK
│       ├── models.py       Veiculo, Motorista, Deslocamento e enums
│       ├── schemas.py      Contratos, normalização e validações de coerência
│       ├── erros.py        Respostas 422 em português ({detail, erros[]})
│       ├── seed.py         Dados fictícios de demonstração (só com banco vazio)
│       └── routers/        veiculos · motoristas · deslocamentos  (dashboard: S3)
├── frontend/               (telas de CRUD: S2)
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js
├── tests/
│   ├── conftest.py         SQLite em memória + trava contra o banco real
│   └── backend/            Testes de API (pytest + TestClient)
├── scripts/                configurar · iniciar · verificar · seed · homologar (.ps1)
├── homologacao/            homologar.py (Playwright) · verificar_segredos.py · requirements.txt
├── docs/                   Requisitos, Arquitetura, backlog, teste, execucao, evidencias/
└── legado/                 MVP anterior, só referência (ADR-003)
```

## 3. Stack e versões validadas

| Componente | Versão | Observação |
|---|---|---|
| Python | 3.15.1 | Único interpretador instalado na máquina |
| FastAPI | 0.161.1 | |
| Starlette | 1.9.0 | Dependência do FastAPI |
| SQLAlchemy | 2.1.6 | API 2.0 (`CONTEXTO.md` cita 2.0) |
| Pydantic | 2.14.1 | |
| uvicorn | 0.54.0 | Sem o extra `[standard]` (ADR-004) |
| pytest / httpx | 9.1.1 / 0.28.1 | |
| ruff | 0.17.2 | Lint + formatação (ADR-009) |
| Git | 2.55.0 | |
| Node | 22.10.0 | Instalado, **não** é dependência (ADR-006) |

## 4. Convenções

- Domínio, rotas, mensagens e comentários em português.
- Erros HTTP: `422` formato · `404` inexistente · `409` conflito de regra. Todo erro tem `detail` (texto pronto para exibir); o 422 traz também `erros: [{campo, mensagem}]` para marcar campos no formulário.
- Frontend: toda string da API passa por `esc()`; CSS `.bloco__elemento` / `.bloco--variante`; cores apenas via variáveis de `:root`.
- Testes nunca tocam o banco real (`dependency_overrides` + SQLite em memória).
- Sem migrações até a Sprint 3: `Base.metadata.create_all`.

## 5. Registro de decisões (ADR)

Formato: contexto → decisão → consequência. Status: **Aceita** salvo indicação.

### ADR-001 — Fonte de verdade sem o handoff
- **Contexto:** a instrução pedia leitura do `Handoff_claude_code.md`, que não existe na pasta nem nos `.zip` da pasta pai.
- **Decisão:** usar `CONTEXTO.md` (e o README antigo, em `legado/`) como fonte de requisitos, confirmado pela usuária em 2026-10-23.
- **Consequência:** se o handoff aparecer, comparar com `docs/Requisitos.md` e abrir ADR para cada divergência.

### ADR-002 — Estrutura `backend/` + `frontend/` + `tests/`
- **Contexto:** `CONTEXTO.md` §4.3 define tudo dentro de `app/` (frontend em `app/static/`). A instrução da Sprint 0 pede `backend/`, `frontend/` e pasta de testes separadas.
- **Decisão:** adotar `backend/app/` para a API e `frontend/` na raiz; o FastAPI continua servindo o frontend (mantém "um processo, sem CORS, sem build"). Testes em `tests/` na raiz, com `pythonpath=backend` no `pytest.ini`.
- **Consequência:** comandos mudam para `uvicorn app.main:app --app-dir backend`. Caminhos do `CONTEXTO.md` §4.3 ficam desatualizados — esta seção prevalece.

### ADR-003 — MVP anterior arquivado em `legado/`
- **Contexto:** a pasta não estava vazia: havia um MVP completo (do `Desafio03_Gestao_Veiculos.zip`) que o `CONTEXTO.md` marca como Sprint 1 e 2 "concluídas", mas que nunca foi verificado neste repositório.
- **Decisão:** mover `app/`, `tests/`, `run.*`, `requirements.txt`, `README.md` e `CLAUDE.md` antigos para `legado/` sem alterar o conteúdo (`CLAUDE.md` renomeado para `CLAUDE_original.md`, para não ser carregado como instrução). As Sprints 1 e 2 voltam a ser **pendentes** e serão portadas para a nova estrutura com testes reexecutados.
- **Consequência:** `legado/` é só referência; não é executado nem coletado pelo pytest (`testpaths = tests`). Deve ser removido quando o porte terminar.

### ADR-004 — Python 3.15 e versões atualizadas
- **Contexto:** só o Python 3.15.1 está instalado. As versões fixadas no MVP antigo (ex.: `pydantic==2.10.4`) são anteriores ao 3.15, e `uvicorn[standard]` falhou na instalação (extras compilados sem pacote para 3.15).
- **Decisão:** fixar as versões atuais que instalam como wheel no 3.15 e usar `uvicorn` sem `[standard]`. O `--reload` continua funcionando (detecção de mudança por polling, sem `watchfiles`).
- **Consequência:** sem `uvloop`/`httptools` — irrelevante para uso monoposto. Requisito mínimo documentado passa a ser Python 3.11+, validado apenas em 3.15.1.

### ADR-005 — Local do banco
- **Decisão:** `backend/data/gestao_veiculos.db`, criado na inicialização e ignorado pelo git (`*.db`). Só a pasta (`.gitkeep`) é versionada.

### ADR-006 — Node não é dependência
- **Contexto:** pediu-se verificar Node; o projeto proíbe build e gerenciador Node.
- **Decisão:** Node é verificado e registrado, mas não usado. Ferramentas Node (ex.: Playwright para capturas de tela) só entram com ADR própria.

### ADR-007 — Sem segredos e sem dados institucionais
- **Decisão:** nenhum `.env`, chave ou credencial é versionado (`.gitignore` cobre `.env*`, `*.pem`, `*.key`, `*.db`). Dados de demonstração serão fictícios. O autor dos commits usa o e-mail noreply do GitHub configurado **só neste repositório**, em vez do e-mail institucional global.

### ADR-008 — Replanejamento das sprints do MVP
- **Contexto:** em 2026-10-23 a usuária redefiniu as sprints: **S1** = entidades Veículo, Motorista e Deslocamento (destino, data, finalidade) + persistência SQLite + API CRUD com validações e testes de API; **S2** = páginas responsivas, formulários, tabelas e integração com a API; **S3** = dashboard calculado (veículos, deslocamentos, viagens previstas e realizadas). O backlog anterior previa cadastros com tela na S1, deslocamentos + painel na S2 e autenticação/exportação na S3.
- **Decisão:** adotar a nova divisão. Os itens da antiga Sprint 3 (autenticação, auditoria, exportação, alertas, manutenção, Alembic, Docker) passam a **Pós-MVP** e continuam fora do escopo. "Destino" segue como texto livre no Deslocamento (não é entidade própria), como no `CONTEXTO.md` §5.
- **Exceção registrada:** a regra "API e interface na mesma entrega" fica suspensa na S1 — a API é entregue sem telas de CRUD e é exercitada por testes e por `/docs`. A S2 só é considerada pronta quando todas as rotas da S1 tiverem tela.
- **Consequência:** entre a S1 e a S2, a página inicial continua sendo só a de situação do sistema.

### ADR-009 — Ruff como lint
- **Contexto:** o gate de cada sprint pede lint, e o projeto não tinha nenhum.
- **Decisão:** adicionar `ruff` (wheel única, sem dependências, instala no Python 3.15) a `backend/requirements.txt`, configurado em `ruff.toml` na raiz, excluindo `legado/`.
- **Alternativa descartada:** flake8 + plugins (mais pacotes para o mesmo resultado). JavaScript continua sem lint, pois exigiria Node (ADR-006).

### ADR-010 — Definição dos indicadores do painel (S3)
- **Contexto:** o painel da S3 deve mostrar veículos, deslocamentos e viagens previstas × realizadas, calculados a partir dos dados persistidos. O `CONTEXTO.md` §2.2 dá as fórmulas, mas deixa pontos em aberto, e o dashboard do `legado/` os resolvia de forma inconsistente (soma de km de qualquer situação, período invertido trocado em silêncio, canceladas na utilização, sem as situações "em andamento" e "canceladas").
- **Decisão:** os **3 indicadores principais** são **Veículos**, **Deslocamentos** e **Viagens (previstas × realizadas)**. Definições (todas por consulta, nada armazenado, regra 9):
  - **Período** filtra por `data_saida`. Padrão: 90 dias atrás a 30 dias à frente. `data_fim < data_inicio` → **422** (não se troca em silêncio).
  - **Veículos:** total cadastrado e quebra por situação atual (disponível, em viagem, manutenção, inativo). Não depende do período.
  - **Deslocamentos no período:** todas as situações. `total = previstas + em andamento + realizadas + canceladas`. Por finalidade, destinos (top 5) e série mensal também contam todas as situações, então a soma de cada quebra é igual ao total.
  - **Taxa de realização** = realizadas ÷ (previstas + realizadas) × 100 (em andamento e canceladas ficam fora); 0 quando o denominador é 0.
  - **Km percorrido** = soma de `km_final − km_inicial` **só de viagens realizadas** com os dois km preenchidos. **Média por viagem** = km total ÷ viagens realizadas **com km informado**.
  - **Utilização da frota** = veículos distintos com ao menos um deslocamento **não cancelado** no período ÷ total de veículos × 100.
  - **Próximas saídas (RF13):** `previsto` com `data_saida >= hoje`, da mais próxima para a mais distante (padrão 5).
- **Consequência:** base vazia retorna zeros, sem divisão por zero. As definições valem para os testes CA03 e para a homologação (S4).

### ADR-011 — Sprint 4: homologação, Playwright (Python) e banco configurável
- **Contexto:** em 2026-10-23 a usuária pediu uma "Sprint 4" de homologação (CRUD, validação de entrega, lista vazia, indicadores após mudanças, persistência ao reiniciar, integração frontend/API, ausência de segredos no git) com **capturas de tela de evidência guardadas no projeto**. A ADR-008 só definia S1–S3, e a ADR-006 proíbe Node como dependência do projeto. Decisões da usuária no chat: S3 antes da S4; manter o repositório atual; Playwright **fora do projeto**; sem deploy no Vercel.
- **Decisão:**
  1. **S4 = homologação**, sem funcionalidade nova de negócio. "Validação de entrega" = aceite (CA01–CA03 + entregáveis + instalação a partir de clone limpo).
  2. **Playwright para Python** (`homologacao/requirements.txt`), instalado num ambiente virtual **separado** do de execução; não entra em `backend/requirements.txt` e o sistema roda sem ele. Isso mantém a ADR-006 (sem Node, sem `package.json`). Só os PNG e os scripts de homologação ficam no repositório; o navegador baixado fica fora (cache do Playwright).
  3. **`RODAGEM_DB`** (opcional): caminho do arquivo SQLite. Sem a variável, nada muda (`backend/data/gestao_veiculos.db`). Serve para a homologação rodar com banco temporário sem tocar nos dados da usuária. É a única variável de ambiente do MVP; o restante da "configuração por ambiente" segue pós-MVP.
  4. **Evidências** em `docs/evidencias/`, com um índice dizendo o que cada captura prova. Dados exclusivamente fictícios (seed).
- **Consequência:** a homologação é reproduzível com `.\scripts\homologar.ps1`. O que não for executado de fato é marcado **NÃO TESTADO**. O deploy no Vercel **não** faz parte desta entrega (decisão da usuária; SQLite em arquivo não persiste em funções serverless).
