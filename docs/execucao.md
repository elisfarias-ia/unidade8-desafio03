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
| Push | Ver resultado no relatório final da sessão |

### 6. O que **não** foi validado na Sprint 0

- Nenhuma regra de negócio (não existe código de domínio ainda).
- Responsividade e acessibilidade da interface (só há uma página de status).
- Outras versões de Python além da 3.15.1 e outros sistemas além do Windows 11.
- Código em `legado/` — não foi executado nem testado neste repositório.
