# Rodagem — Gestão de Veículos e Deslocamentos

Sistema web para controlar a frota de uma organização: cadastro de veículos e motoristas, registro de deslocamentos, histórico e painel de indicadores.

> **Situação: Sprint 4 (homologação) concluída.** API, interface e painel de indicadores funcionando, com dados em SQLite, homologados de ponta a ponta com capturas de tela em [`docs/evidencias/`](docs/evidencias/README.md). Resultado e limites do que foi (e do que não foi) testado: [`docs/execucao.md`](docs/execucao.md).

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

## Homologação e evidências

```powershell
.\scripts\homologar.ps1            # ~3 min; use -SemClone para pular a instalação em clone limpo
```

Sobe o servidor **real** com um banco temporário (variável opcional `RODAGEM_DB`; seus dados não são tocados), exercita a interface num navegador (Playwright em Python, em ambiente separado: não é dependência do sistema) e grava as capturas e o resultado em [`docs/evidencias/`](docs/evidencias/README.md). Cobre: criar/ler/editar/excluir, aceite da entrega, listas vazias, indicadores após mudanças, persistência ao reiniciar o servidor, integração frontend ↔ API e ausência de segredos no Git (arquivos **e** histórico). A primeira execução baixa o Playwright e o Chromium (~700 MB, fora do projeto). `python homologacao/verificar_segredos.py` roda só a varredura de segredos.

## Painel de indicadores

A página inicial (**Painel**) mostra, para o período escolhido (padrão: 90 dias atrás a 30 dias à frente, pela data de saída):

| Indicador | Como é calculado |
|---|---|
| **Veículos** | total cadastrado e quebra por situação atual (disponível, em viagem, manutenção, inativo) |
| **Deslocamentos** | total no período = previstos + em andamento + realizados + cancelados |
| **Viagens previstas × realizadas** | contagem de cada uma, com barra de proporção |
| Taxa de realização | realizadas ÷ (previstas + realizadas) |
| Distância e média | soma e média de `km final − km inicial` das viagens realizadas com km informado |
| Utilização da frota | veículos com ao menos uma viagem não cancelada ÷ total de veículos |

Também mostra deslocamentos por finalidade, os 5 destinos mais frequentes, a série mensal e as próximas saídas previstas. Tudo é calculado na hora a partir do banco; nada é guardado pré-calculado. Definições completas: ADR-010 em [`docs/Arquitetura.md`](docs/Arquitetura.md).

## Como usar a interface

1. Rode `.\scripts\seed.ps1` (dados fictícios) e `.\scripts\iniciar.ps1`; abra http://127.0.0.1:8000 (abre no **Painel**).
2. **Veículos** e **Motoristas**: "Novo …" abre o formulário; a busca filtra enquanto você digita; **Editar** e **Excluir** ficam em cada linha (a exclusão pede confirmação).
3. **Deslocamentos**: "Registrar deslocamento" → escolha veículo, motorista, destino, datas e finalidade. Os 7 filtros combinam entre si. **Concluir** informa o km final e o retorno e atualiza o km do veículo.
4. Erros da API (placa repetida, agenda ocupada, veículo em manutenção…) aparecem no próprio formulário, com o campo marcado.
5. No celular a navegação vai para o rodapé e as tabelas viram cartões.

## Exemplos de uso

### Pela interface
Abra http://127.0.0.1:8000, vá em **Veículos** → *Novo veículo*, depois **Motoristas** → *Novo motorista* e **Deslocamentos** → *Registrar deslocamento*. Quando a viagem terminar, clique em **Concluir** e informe o km final; o **Painel** se atualiza sozinho.

### Pela API (PowerShell, com o servidor no ar)

```powershell
$api = "http://127.0.0.1:8000/api"
$json = @{ "Content-Type" = "application/json" }

# 1) cadastrar um veículo e um motorista (dados fictícios)
$veiculo = Invoke-RestMethod -Method Post "$api/veiculos" -Headers $json -Body (@{
    placa = "ABC1D23"; marca = "Fiat"; modelo = "Strada"; ano = 2022; km_atual = 1000 } | ConvertTo-Json)
$motorista = Invoke-RestMethod -Method Post "$api/motoristas" -Headers $json -Body (@{
    nome = "Ana Exemplo"; cnh = "00000000001"; categoria_cnh = "B" } | ConvertTo-Json)

# 2) registrar um deslocamento em andamento
$hoje = (Get-Date).ToString("yyyy-MM-dd")
$desl = Invoke-RestMethod -Method Post "$api/deslocamentos" -Headers $json -Body (@{
    veiculo_id = $veiculo.id; motorista_id = $motorista.id; destino = "Unidade Centro"
    data_saida = $hoje; finalidade = "entrega"; status = "em_andamento" } | ConvertTo-Json)

# 3) concluir a viagem com 120 km percorridos
Invoke-RestMethod -Method Post "$api/deslocamentos/$($desl.id)/concluir" -Headers $json -Body (@{
    km_final = $desl.km_inicial + 120; data_retorno = $hoje } | ConvertTo-Json)

# 4) consultar: histórico filtrado e indicadores
Invoke-RestMethod "$api/deslocamentos?destino=Centro&status=realizado"
Invoke-RestMethod "$api/dashboard/indicadores" | Select-Object total_veiculos, total_deslocamentos, viagens_realizadas, taxa_realizacao, km_total_percorrido

# 5) erros têm mensagem em português: placa repetida -> 409
try { Invoke-RestMethod -Method Post "$api/veiculos" -Headers $json -Body (@{
        placa = "ABC1D23"; marca = "Fiat"; modelo = "Uno"; ano = 2022 } | ConvertTo-Json) }
catch { ($_.ErrorDetails.Message | ConvertFrom-Json).detail }
```

A documentação interativa de todas as rotas fica em http://127.0.0.1:8000/docs.

## API

| Recurso | Rotas | Observações |
|---|---|---|
| Veículos | `GET/POST /api/veiculos` · `GET/PUT/DELETE /api/veiculos/{id}` | Filtros `busca`, `status`. Placa `ABC1234`/`ABC1D23`, única. |
| Motoristas | `GET/POST /api/motoristas` · `GET/PUT/DELETE /api/motoristas/{id}` | Filtros `busca`, `apenas_ativos`. CNH com 11 dígitos, única. |
| Deslocamentos | `GET/POST /api/deslocamentos` · `GET/PUT/DELETE /api/deslocamentos/{id}` | Filtros `veiculo_id`, `motorista_id`, `destino`, `finalidade`, `status`, `data_inicio`, `data_fim`, `limite`. |
| Painel | `GET /api/dashboard/indicadores` · `GET /api/dashboard/proximas-saidas` | Parâmetros `data_inicio`, `data_fim` (período invertido → 422); `limite` (1–50). |
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
frontend/  HTML, CSS e JS puro (módulos ES, sem build) servidos pelo FastAPI
tests/     pytest (banco em memória)
scripts/   configurar.ps1 · iniciar.ps1 · verificar.ps1 · seed.ps1 · homologar.ps1
homologacao/  homologar.py (Playwright) e verificar_segredos.py — só para homologar; o sistema roda sem eles
docs/      Requisitos · Arquitetura (ADRs) · backlog · teste · execucao · evidencias (capturas)
legado/    MVP anterior, mantido só como referência
```

## Documentação

- [Requisitos](docs/Requisitos.md) · [Arquitetura e ADRs](docs/Arquitetura.md) · [Backlog](docs/backlog.md) · [Plano de testes](docs/teste.md) · [Registro de execução](docs/execucao.md)

## Limitações atuais

- Indicadores sem exportação (CSV/PDF) e sem gráficos interativos: as barras são simples e mostram os valores em texto.
- Em celular (375 px) os 7 filtros de deslocamentos ocupam a primeira tela antes da lista.
- Sem autenticação nem controle de permissões: qualquer pessoa com acesso à página altera os dados.
- Interface testada só no Chromium embutido, em larguras emuladas; sem teste com leitor de tela, Firefox ou Safari.
- Destino em texto livre: "Centro" e "Unidade Centro" contam como destinos diferentes.
- Ids de registros excluídos podem ser reaproveitados pelo SQLite.
- Sem autenticação: use só na própria máquina ou rede local.
- **Sem deploy**: o sistema roda localmente. Publicar no Vercel **não foi feito nem testado**; além disso, o SQLite em arquivo não persiste em funções serverless, então a persistência exigiria trocar o banco (fora do escopo).
- Homologação só no Chromium (Playwright) e no Chromium embutido do app; **JavaScript sem lint** (sem Node no projeto) e **sem teste com leitor de tela, Firefox ou Safari**.
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
