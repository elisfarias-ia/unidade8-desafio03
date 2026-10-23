# Rodagem — Gestão de Veículos e Deslocamentos

Sistema web para controlar a frota de uma organização: cadastro de veículos e motoristas, registro de deslocamentos, histórico e painel de indicadores.

> **Situação: Sprint 0 concluída.** Existe apenas o esqueleto executável (verificação de saúde da API e do banco + página inicial). Cadastros, deslocamentos e painel entram nas Sprints 1 e 2 — ver [`docs/backlog.md`](docs/backlog.md).

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

# 3. verificar ferramentas e rodar os testes
.\scripts\verificar.ps1
```

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
```

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
scripts/   configurar.ps1 · iniciar.ps1 · verificar.ps1
docs/      Requisitos · Arquitetura (ADRs) · backlog · teste · execucao
legado/    MVP anterior, mantido só como referência
```

## Documentação

- [Requisitos](docs/Requisitos.md) · [Arquitetura e ADRs](docs/Arquitetura.md) · [Backlog](docs/backlog.md) · [Plano de testes](docs/teste.md) · [Registro de execução](docs/execucao.md)

## Limitações atuais

- Nenhuma funcionalidade de negócio ainda (Sprint 0).
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
