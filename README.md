# Rodagem — Gestão de Veículos e Deslocamentos

Sistema web para controlar a frota de uma organização: cadastro de veículos e motoristas, registro de deslocamentos, histórico e painel de indicadores.

> **Situação: Sprint 1 concluída — API pronta, sem telas.** Veículos, motoristas e deslocamentos já funcionam pela API (CRUD, regras de negócio, histórico com filtros), com dados em SQLite. As telas entram na Sprint 2 e o painel de indicadores na Sprint 3 — ver [`docs/backlog.md`](docs/backlog.md). Até lá, use a API pela documentação interativa em http://127.0.0.1:8000/docs.

## Pré-requisitos

| Ferramenta | Versão | Necessária? |
|---|---|---|
| Python | 3.11+ (validado em 3.15.1) | Sim — marque "Add Python to PATH" na instalação |
| Git | qualquer recente | Para clonar/versionar |
| Node | — | **Não** (o projeto não tem etapa de build) |

## Instalação e execução — Windows / PowerShell

Na raiz do projeto:

```powershell
# 1. ambiente virtual + dependências
.\scripts\configurar.ps1

# 2. subir API + interface em http://127.0.0.1:8000
.\scripts\iniciar.ps1

# 3. verificar ferramentas, lint e testes
.\scripts\verificar.ps1

# opcional: dados FICTÍCIOS de demonstração (só age com o banco vazio)
.\scripts\seed.ps1
```

O seed cria 6 veículos (placas `TST…`), 4 motoristas (`… Exemplo`, CNHs `000…`, telefones com DDD 00) e cerca de 150 deslocamentos entre 90 dias atrás e 30 dias à frente.

Se o PowerShell bloquear scripts ("execução de scripts foi desabilitada"), libere só para o seu usuário:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Sem os scripts

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload
pytest -v
ruff check .
```

## API (Sprint 1)

| Recurso | Rotas | Observações |
|---|---|---|
| Veículos | `GET/POST /api/veiculos` · `GET/PUT/DELETE /api/veiculos/{id}` | Filtros `busca`, `status`. Placa `ABC1234`/`ABC1D23`, única. |
| Motoristas | `GET/POST /api/motoristas` · `GET/PUT/DELETE /api/motoristas/{id}` | Filtros `busca`, `apenas_ativos`. CNH com 11 dígitos, única. |
| Deslocamentos | `GET/POST /api/deslocamentos` · `GET/PUT/DELETE /api/deslocamentos/{id}` | Filtros `veiculo_id`, `motorista_id`, `destino`, `finalidade`, `status`, `data_inicio`, `data_fim`, `limite`. |
| Concluir viagem | `POST /api/deslocamentos/{id}/concluir` | Corpo `{"km_final": 1250, "data_retorno": "2026-10-23"}`; atualiza o km do veículo. |

Erros: `422` dado inválido · `404` não encontrado · `409` conflito de regra (placa/CNH repetida, agenda ocupada, veículo em manutenção, exclusão com histórico). Toda resposta de erro traz `detail` em português; o 422 traz também `erros` com campo e mensagem.

Regras aplicadas: retorno não pode ser antes da saída; km final não pode ser menor que o inicial; viagem realizada exige data de retorno; mesmo veículo não fica em dois deslocamentos ativos no mesmo período; veículo em manutenção/inativo e motorista inativo não são escalados; quem tem histórico não é excluído (mude para inativo); concluir a viagem atualiza o km e devolve o veículo para "disponível".

| Endereço | O que é |
|---|---|
| http://127.0.0.1:8000 | Interface web |
| http://127.0.0.1:8000/docs | Documentação interativa da API |
| http://127.0.0.1:8000/api/saude | Verificação de API e banco |

O banco SQLite é criado em `backend/data/gestao_veiculos.db` na primeira execução e não vai para o git.

## Estrutura

```
backend/   API FastAPI (backend/app) e requirements.txt
frontend/  HTML, CSS e JS puro servidos pelo FastAPI
tests/     pytest (banco em memória)
scripts/   configurar.ps1 · iniciar.ps1 · verificar.ps1 · seed.ps1
docs/      Requisitos · Arquitetura (ADRs) · backlog · teste · execucao
legado/    MVP anterior, mantido só como referência
```

## Documentação

- [Requisitos](docs/Requisitos.md) · [Arquitetura e ADRs](docs/Arquitetura.md) · [Backlog](docs/backlog.md) · [Plano de testes](docs/teste.md) · [Registro de execução](docs/execucao.md)

## Limitações atuais

- Ainda sem telas de cadastro e sem painel: a API só é usada por `/docs` ou outro cliente HTTP (telas na Sprint 2, painel na Sprint 3).
- Destino em texto livre: "Centro" e "Unidade Centro" contam como destinos diferentes.
- Ids de registros excluídos podem ser reaproveitados pelo SQLite.
- Sem autenticação: use só na própria máquina ou rede local.
- Validado apenas em Windows 11 com Python 3.15.1.
- `uvicorn` sem extras de desempenho (`[standard]`), que não instalam no Python 3.15 — sem impacto em uso local.

## Solução de problemas

| Sintoma | O que fazer |
|---|---|
| `'python' não é reconhecido` | Reinstale o Python marcando "Add Python to PATH", ou use `py`. |
| Porta 8000 ocupada | `.\scripts\iniciar.ps1 -Porta 8001` |
| `ModuleNotFoundError` | Rode `.\scripts\configurar.ps1` de novo. |
| Página mostra "Não foi possível falar com a API" | O servidor não está rodando ou caiu; veja o terminal. |
| `DLL load failed … O nome do arquivo ou a extensão é muito grande` | O caminho da pasta é longo demais (limite de 260 caracteres do Windows). Mova o projeto para uma pasta mais curta, ex.: `C:\projetos\rodagem`. |
