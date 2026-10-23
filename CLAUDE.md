# CLAUDE.md

Instruções para o Claude Code trabalhar neste repositório.

## O que é este projeto

**Rodagem** — sistema web de gestão de veículos e deslocamentos de uma frota institucional: cadastro de veículos e motoristas, registro de saídas com destino, data e finalidade, histórico e painel de indicadores.

Leia antes de propor mudanças:
- `docs/Requisitos.md` — requisitos, regras de negócio, critérios de aceite
- `docs/Arquitetura.md` — estrutura, stack e **ADRs** (decisões já tomadas)
- `docs/backlog.md` — o que pertence a cada sprint
- `docs/teste.md` — plano e IDs de teste
- `CONTEXTO.md` — concepção original; onde divergir de `docs/`, `docs/` prevalece

`legado/` contém o MVP anterior apenas como referência (ADR-003). Não execute, não edite e não importe nada de lá; porte o que for útil para `backend/`/`frontend/` e reteste.

## Situação atual

Sprint 0 concluída: esqueleto executável (`/api/saude` + página inicial), docs e git. Próxima: Sprint 1 (cadastros).

## Stack

- Python 3.11+ (validado em 3.15.1) · FastAPI · SQLAlchemy 2.x · Pydantic v2 · SQLite
- Frontend: HTML, CSS e JavaScript puro, **sem framework e sem build**
- Testes: pytest + TestClient

## Comandos (Windows / PowerShell, na raiz)

```powershell
.\scripts\configurar.ps1     # cria .venv e instala backend\requirements.txt
.\scripts\iniciar.ps1        # API + interface em http://127.0.0.1:8000
.\scripts\verificar.ps1      # versões das ferramentas + pytest -v

# equivalentes diretos
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
.\.venv\Scripts\python.exe -m pytest -v
```

Banco: `backend/data/gestao_veiculos.db` (não versionado). Ao alterar um modelo, **avise a usuária** antes de apagar o arquivo.

## Mapa do código

| Caminho | Responsabilidade |
|---|---|
| `backend/app/main.py` | FastAPI, routers, frontend em `/` e `/static` |
| `backend/app/database.py` | Engine, `SessionLocal`, `get_db`, `PRAGMA foreign_keys=ON` |
| `backend/app/models.py` | (Sprint 1) entidades e enums |
| `backend/app/schemas.py` | (Sprint 1) contratos e validações de formato/coerência |
| `backend/app/routers/` | (Sprint 1–2) regras de negócio que consultam o banco |
| `frontend/` | `index.html`, `css/styles.css`, `js/app.js` |
| `tests/conftest.py` | Fixture `client` com SQLite em memória |
| `tests/backend/` | Testes de API e critérios de aceite |
| `scripts/` | Scripts PowerShell (sem acentos: PS 5.1 lê `.ps1` como ANSI) |

## Convenções

- **Idioma:** domínio, rotas, variáveis, mensagens e comentários em português. Não renomeie campos para inglês. Interface sempre em português.
- **Camadas:** formato/coerência em `schemas.py`; regra que consulta o banco no router; nenhuma regra de negócio no frontend.
- **Erros HTTP:** `422` formato · `404` inexistente · `409` conflito de regra. Mensagem diz o que houve e como resolver, sem jargão.
- **Frontend:** sem dependências novas; toda string da API passa por `esc()`; CSS `.bloco__elemento` e `.bloco--variante`; cores só por variáveis de `:root`.
- **Banco:** sem migrações até a Sprint 3 (`create_all`).
- **Testes:** toda nova regra ganha teste com o ID de `docs/teste.md` no nome; nunca tocar o banco real.

## Regras de negócio que não podem quebrar

1. Placa única, válida em `ABC1234` ou `ABC1D23`, normalizada para maiúsculas sem hífen.
2. CNH única por motorista.
3. `data_retorno >= data_saida` e `km_final >= km_inicial`.
4. Deslocamento `realizado` exige `data_retorno`.
5. Veículo sem dois deslocamentos `previsto`/`em_andamento` sobrepostos.
6. Veículo em `manutencao`/`inativo` e motorista inativo não são escalados.
7. Com histórico não se exclui — muda para inativo.
8. Concluir viagem atualiza `km_atual` e devolve o veículo a `disponivel`.
9. Indicadores sempre calculados por consulta.

## Ao receber uma tarefa

1. Confira em `docs/backlog.md` a sprint do item; se for de sprint futura ou fora do MVP, avise antes.
2. Mudança de escopo, arquitetura ou modelo de dados → **registre ADR** em `docs/Arquitetura.md` antes de implementar.
3. Entregue API e interface juntas; funcionalidade sem tela não está pronta.
4. Rode `pytest -v`, suba o servidor e confira a tela; registre o que foi **realmente** validado em `docs/execucao.md`.
5. Atualize `README.md` se mudar funcionalidade ou limitação, e `docs/backlog.md` com a situação.

## O que não fazer

- Framework de frontend, bundler ou gerenciador Node (ADR-006).
- Trocar SQLite sem pedido explícito.
- Dependência nova sem justificar e atualizar `backend/requirements.txt`.
- Autenticação, exportação ou manutenção sem pedido — são da Sprint 3.
- Versionar `.env`, chaves, tokens, banco ou dados reais/institucionais (ADR-007).
- Apagar o banco da usuária sem avisar.
- Usar o e-mail institucional nos commits (o repositório tem `user.email` local noreply).
