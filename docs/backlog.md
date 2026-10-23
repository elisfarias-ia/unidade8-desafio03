# Backlog — Rodagem

Legenda: ✅ feito e verificado · ⏳ pendente · ⛔ fora do MVP.
Divisão das sprints conforme ADR-008 (replanejamento de 2026-10-23).

**Gate de cada sprint** — só avança se tudo passar, com evidência em `execucao.md`:
`ruff check` · `ruff format --check` · `pytest -v` · aplicação real com SQLite em arquivo · funções conferidas na prática.

## Sprint 0 — Fundação do repositório ✅

Estrutura `backend/` `frontend/` `tests/` `scripts/` `docs/`, MVP anterior em `legado/`, `.gitignore`, verificação de Python/Node/Git, scripts PowerShell, esqueleto FastAPI com `/api/saude`, 4 testes de fumaça, git publicado. Detalhes em `execucao.md`.

## Sprint 1 — Entidades, persistência e API ✅

**Objetivo:** Veículo, Motorista e Deslocamento (destino, data, finalidade) persistidos em SQLite, com API CRUD, validações e testes de API. **Aceite:** CA01 e CA02 (via API).

| ID | Item | Origem | Situação |
|---|---|---|---|
| S1-01 | Modelos `Veiculo`, `Motorista`, `Deslocamento` + enums, FK `RESTRICT` | RF01, RF04–06 | ✅ |
| S1-02 | Schemas: normalização de placa/CNH/categoria, coerência de datas e km | RF03, regras 1–4 | ✅ |
| S1-03 | CRUD `/api/veiculos` com busca e filtro de situação | RF01–03 | ✅ |
| S1-04 | CRUD `/api/motoristas` com busca e filtro de ativos | RF04 | ✅ |
| S1-05 | CRUD `/api/deslocamentos` + `POST /{id}/concluir` | RF05–07 | ✅ |
| S1-06 | Regras: agenda sobreposta, situação de veículo/motorista, km e retorno na conclusão | RF10–11, regras 5, 6, 8 | ✅ |
| S1-07 | Bloqueio de exclusão com histórico | RF12, regra 7 | ✅ |
| S1-08 | Histórico com filtros combináveis | RF08 | ✅ |
| S1-09 | Erros 422 em português com campo e mensagem | RNF06, RNF08 | ✅ |
| S1-10 | `seed.py` com dados fictícios, só com banco vazio | — | ✅ |
| S1-11 | Lint (ruff) e 37 testes novos de API | ADR-009 | ✅ |

## Sprint 2 — Interface ⏳ (próxima)

**Objetivo:** páginas responsivas, formulários, tabelas e integração com a API da S1. **Pronta só quando toda rota da S1 tiver tela** (ADR-008).

| ID | Item | Origem |
|---|---|---|
| S2-01 | Layout responsivo 320 px → desktop: navegação lateral / barra inferior | RNF03 |
| S2-02 | Veículos: tabela com busca e filtro, formulário de cadastro/edição, exclusão com confirmação | RF01–03 |
| S2-03 | Motoristas: tabela, formulário, ativar/desativar, exclusão | RF04 |
| S2-04 | Deslocamentos: tabela de histórico com filtros, formulário, concluir viagem, excluir | RF05–08 |
| S2-05 | Exibir `detail` e marcar campos com `erros[]` nos formulários | RNF06 |
| S2-06 | Acessibilidade mínima: rótulos, foco, contraste, `prefers-reduced-motion` | RNF07 |
| S2-07 | Verificação no navegador (desktop e 375 px) registrada em `execucao.md` | — |

## Sprint 3 — Dashboard ⏳

**Objetivo:** painel calculado a partir dos dados persistidos. **Aceite:** CA03.

| ID | Item | Origem |
|---|---|---|
| S3-01 | `GET /api/dashboard/indicadores?data_inicio&data_fim` (sempre por consulta) | RF09, regra 9 |
| S3-02 | Totais de veículos (disponíveis/em viagem), deslocamentos, previstas e realizadas | RF09 |
| S3-03 | Taxa de realização, km total, média por viagem, utilização da frota | RF09 |
| S3-04 | Por finalidade, top 5 destinos, série mensal | RF09 |
| S3-05 | Tela do painel com período ajustável e próximas saídas | RF09, RF13 |
| S3-06 | Testes CA03 com base conhecida + medição RNF04 (10 mil deslocamentos) | CA03, RNF04 |

## Pós-MVP ⛔

Autenticação e perfis · auditoria · exportação CSV/PDF · alertas de CNH e atraso · manutenção por km · Alembic e variáveis de ambiente · cobertura > 80% · Docker. (Antiga "Sprint 3", ver ADR-008.)

## Débitos e dúvidas em aberto

| ID | Item | Ação proposta |
|---|---|---|
| D-01 | `Handoff_claude_code.md` não encontrado | Se surgir, comparar e registrar ADR |
| D-02 | Aviso do Starlette: `httpx` no TestClient está obsoleto, recomenda `httpx2` | Avaliar quando houver versão estável; nova dependência exige justificativa |
| D-03 | Validado só em Python 3.15.1 | Testar em 3.11–3.13 se houver outra máquina |
| D-04 | Capturas de tela de evidência (Playwright) | Decidir na S2; exige ADR (Node/Playwright) |
| D-05 | Remover `legado/` ao fim do porte | Ao concluir a S3 |
| D-06 | SQLite reaproveita o id do último registro excluído (sem `AUTOINCREMENT`) | Inofensivo hoje; rever junto com auditoria (pós-MVP) |
| D-07 | Destino em texto livre gera variações ("Centro" × "Unidade Centro") | Previsto no `CONTEXTO.md`; normalizar no pós-MVP |
