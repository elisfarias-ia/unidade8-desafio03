# Backlog — Rodagem

Legenda: ✅ feito e verificado · ⏳ pendente · ⛔ fora do MVP.

## Sprint 0 — Fundação do repositório *(esta entrega)*

**Objetivo:** projeto executável vazio, documentado e versionado, pronto para receber as funcionalidades.

| ID | Item | Situação |
|---|---|---|
| S0-01 | Ler documentos disponíveis e registrar decisões/dúvidas | ✅ ADR-001 a 007 |
| S0-02 | Arquivar o MVP anterior em `legado/` | ✅ |
| S0-03 | Estrutura `backend/`, `frontend/`, `tests/`, `scripts/`, `docs/` | ✅ |
| S0-04 | `.gitignore` sem segredos, banco ou ambiente virtual | ✅ |
| S0-05 | Verificar Python, Node, Git e PowerShell | ✅ |
| S0-06 | Instruções e scripts Windows/PowerShell | ✅ |
| S0-07 | Esqueleto FastAPI com `/api/saude` testando o banco | ✅ |
| S0-08 | Frontend mínimo que consome `/api/saude` | ✅ |
| S0-09 | pytest configurado com banco em memória + 4 testes de fumaça | ✅ |
| S0-10 | Docs: Requisitos, Arquitetura, backlog, teste, execucao, CLAUDE.md | ✅ |
| S0-11 | Git local, commits e publicação no GitHub | ✅ (ver `execucao.md`) |

**Pronto quando:** `.\scripts\verificar.ps1` passa e a página inicial mostra "API: ok · Banco: ok".

## Sprint 1 — Cadastros *(próxima)*

**Objetivo:** veículos e motoristas ponta a ponta. **Aceite:** CA01.

| ID | Item | Origem |
|---|---|---|
| S1-01 | Modelos `Veiculo` e `Motorista` + enums | RF01, RF04 |
| S1-02 | Schemas com validação e normalização de placa | RF03 |
| S1-03 | CRUD `/api/veiculos` (409 duplicada, 422 formato) | RF01–03 |
| S1-04 | CRUD `/api/motoristas` (CNH única) | RF04 |
| S1-05 | Bloqueio de exclusão com histórico (completa na S2) | RF12 |
| S1-06 | Layout responsivo com navegação + telas de veículos e motoristas | RNF03, RNF07 |
| S1-07 | `seed.py` com dados fictícios, só com banco vazio | — |
| S1-08 | Testes CA01 + CRUD (criar, consultar, editar, excluir) | CA01 |

## Sprint 2 — Deslocamentos e painel

**Objetivo:** registrar viagens e medir a operação. **Aceite:** CA02 e CA03.

| ID | Item | Origem |
|---|---|---|
| S2-01 | Modelo `Deslocamento` (FK `RESTRICT`) | RF05–06 |
| S2-02 | Registro, edição, exclusão e conclusão de viagem | RF05–07 |
| S2-03 | Regras: datas, km, conflito de agenda, situação | RF10–11, regras 3–8 |
| S2-04 | Histórico com filtros combináveis | RF08 |
| S2-05 | `/api/dashboard/indicadores` + painel e próximas saídas | RF09, RF13 |
| S2-06 | Testes CA02 e CA03; medição RNF04 | CA02, CA03 |

## Sprint 3 — Controle e operação ⛔ fora do MVP

Autenticação JWT e perfis · auditoria · exportação CSV/PDF · alertas de CNH e atraso · manutenção por km · Alembic e variáveis de ambiente · cobertura > 80% · Docker.

## Débitos e dúvidas em aberto

| ID | Item | Ação proposta |
|---|---|---|
| D-01 | `Handoff_claude_code.md` não encontrado | Se surgir, comparar e registrar ADR |
| D-02 | Aviso do Starlette: `httpx` no TestClient está obsoleto, recomenda `httpx2` | Avaliar troca na Sprint 1 (nova dependência → justificar) |
| D-03 | Validado só em Python 3.15.1 | Testar em 3.11–3.13 se houver outra máquina |
| D-04 | Capturas de tela de evidência (Playwright) foram pedidas numa instrução anterior | Decidir na Sprint 1; exige ADR (Node/Playwright) |
| D-05 | Remover `legado/` ao fim do porte | Sprint 2 |
