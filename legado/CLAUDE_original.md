# CLAUDE.md

Instruções para o Claude Code trabalhar neste repositório.

## O que é este projeto

**Rodagem** — sistema web de gestão de veículos e deslocamentos de uma frota institucional. O gestor cadastra veículos e motoristas, registra as saídas com destino, data e finalidade, consulta o histórico e acompanha indicadores no painel.

A concepção completa — requisitos, critérios de aceite, decisões de arquitetura, modelo de dados e sprints — está em **`CONTEXTO.md`**. Leia esse arquivo antes de propor mudanças estruturais.

## Stack

- Python 3.11+ · FastAPI · SQLAlchemy 2.0 (ORM) · Pydantic v2 · SQLite
- Frontend: HTML, CSS e JavaScript puro, sem framework e **sem etapa de build**
- Testes: pytest + TestClient do FastAPI

## Comandos

```bash
# ambiente
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# dados de demonstração (só funciona com o banco vazio)
python -m app.seed

# executar (API + interface em http://127.0.0.1:8000)
uvicorn app.main:app --reload

# testes
pytest -v

# recomeçar do zero
rm gestao_veiculos.db && python -m app.seed
```

## Mapa do código

| Arquivo | Responsabilidade |
|---|---|
| `app/main.py` | Instancia o FastAPI, registra os routers, serve o frontend em `/` |
| `app/database.py` | Engine, `SessionLocal`, dependência `get_db`, `PRAGMA foreign_keys=ON` |
| `app/models.py` | `Veiculo`, `Motorista`, `Deslocamento` e os enums de domínio |
| `app/schemas.py` | Contratos de entrada/saída e validações de formato e coerência |
| `app/routers/veiculos.py` | CRUD de veículos |
| `app/routers/motoristas.py` | CRUD de motoristas |
| `app/routers/deslocamentos.py` | Registro, conclusão, histórico e regras de agenda |
| `app/routers/dashboard.py` | Consultas agregadas dos indicadores |
| `app/static/` | `index.html`, `css/styles.css`, `js/app.js` |
| `tests/test_api.py` | Critérios de aceite CA01, CA02 e CA03 automatizados |

## Convenções do projeto

**Idioma.** Domínio, rotas, variáveis, mensagens de erro e comentários em **português**. Palavras reservadas e bibliotecas permanecem em inglês. Não renomeie campos existentes para inglês.

**Camadas.** Validação de formato e coerência de campos vai em `schemas.py` (Pydantic). Regra de negócio que precisa consultar o banco vai no router. Não coloque lógica de negócio no frontend — ele apenas apresenta e chama a API.

**Erros HTTP.** `422` formato inválido · `404` recurso inexistente · `409` conflito de regra de negócio. A mensagem deve dizer o que aconteceu e como resolver, em português e sem jargão técnico.

**Frontend.** JavaScript puro, sem dependências novas e sem build. Toda string vinda da API passa pela função `esc()` antes de ir ao HTML. Os seletores CSS seguem o padrão `.bloco__elemento` e `.bloco--variante`. As cores saem das variáveis em `:root` — não escreva hex direto nas regras.

**Banco.** Não crie migrações; `Base.metadata.create_all` resolve no MVP. Ao alterar um modelo, apague o `.db` e rode o seed de novo. Alembic entra na Sprint 3.

**Testes.** Toda nova regra de negócio precisa de teste em `tests/test_api.py`. Os testes usam SQLite em memória com `dependency_overrides` — não deixe que toquem o banco real.

## Regras de negócio que não podem quebrar

1. Placa única e válida nos padrões `ABC1234` ou `ABC1D23`, normalizada para maiúsculas sem hífen.
2. CNH única por motorista.
3. `data_retorno >= data_saida` e `km_final >= km_inicial`.
4. Deslocamento `realizado` exige `data_retorno`.
5. Um veículo não pode ter dois deslocamentos `previsto`/`em_andamento` com datas sobrepostas.
6. Veículo em `manutencao`/`inativo` e motorista inativo não podem ser escalados.
7. Veículo ou motorista com histórico não é excluído — muda-se a situação para inativo.
8. Concluir viagem atualiza `km_atual` do veículo e o devolve para `disponivel`.
9. Indicadores são sempre calculados por consulta, nunca armazenados pré-calculados.

## Ao receber uma tarefa

1. Confira em `CONTEXTO.md` se o item pertence ao MVP ou à Sprint 3 — se for de sprint futura, avise antes de implementar.
2. Implemente API e interface na mesma entrega; funcionalidade sem tela não conta como pronta.
3. Rode `pytest -v` antes de considerar concluído.
4. Se a mudança afetar funcionalidades ou limitações, atualize o `README.md`.
5. Mudanças de escopo, modelo de dados ou arquitetura vão também para o `CONTEXTO.md`.

## O que não fazer

- Não adicionar framework de frontend, bundler ou gerenciador de pacotes Node.
- Não trocar o SQLite por outro banco sem pedido explícito.
- Não introduzir dependências novas sem justificar e atualizar `requirements.txt`.
- Não criar autenticação, exportação ou controle de manutenção sem que a tarefa peça — são itens da Sprint 3.
- Não apagar o banco do usuário sem avisar.
- Não traduzir a interface para inglês.
