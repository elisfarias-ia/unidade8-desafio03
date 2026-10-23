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
├── backend/
│   ├── requirements.txt    Dependências com versões fixas
│   ├── data/               Banco SQLite local (não versionado)
│   └── app/
│       ├── main.py         FastAPI, /api/saude, frontend estático
│       ├── database.py     Engine, SessionLocal, get_db, PRAGMA FK
│       ├── models.py       (Sprint 1) Veiculo, Motorista, Deslocamento
│       ├── schemas.py      (Sprint 1) Contratos e validações
│       ├── seed.py         (Sprint 1) Dados fictícios de demonstração
│       └── routers/        (Sprint 1–2) veiculos, motoristas, deslocamentos, dashboard
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js
├── tests/
│   ├── conftest.py         Cliente de teste com SQLite em memória
│   └── backend/            Testes de API (pytest + TestClient)
├── scripts/                configurar.ps1 · iniciar.ps1 · verificar.ps1
├── docs/                   Requisitos, Arquitetura, backlog, teste, execucao
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
| Git | 2.55.0 | |
| Node | 22.10.0 | Instalado, **não** é dependência (ADR-006) |

## 4. Convenções

- Domínio, rotas, mensagens e comentários em português.
- Erros HTTP: `422` formato · `404` inexistente · `409` conflito de regra.
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
