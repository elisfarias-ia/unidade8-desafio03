# Rodagem — Gestão de Veículos e Deslocamentos

Sistema web para controlar a frota de uma organização: cadastro de veículos e motoristas, registro de deslocamentos com destino, data e finalidade, consulta de histórico e painel de indicadores calculados a partir dos próprios registros.

Desafio 03 · MVP 0.1.0 · Python + FastAPI + SQLite + interface web responsiva.

---

## Instalação

**Pré-requisito:** Python 3.11 ou superior ([python.org/downloads](https://www.python.org/downloads/) — marque "Add Python to PATH" na instalação em Windows).

### Caminho rápido

**Windows** — dê um duplo clique em `run.bat`, ou no terminal:
```bat
run.bat
```

**Linux ou macOS:**
```bash
./run.sh
```

O script cria o ambiente virtual, instala as dependências, carrega os dados de demonstração na primeira vez e sobe a aplicação.

### Caminho manual

```bash
# 1. ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 2. dependências
pip install -r requirements.txt

# 3. dados de demonstração (opcional, recomendado na primeira execução)
python -m app.seed

# 4. executar
uvicorn app.main:app --reload
```

---

## Execução

Com a aplicação no ar:

| Endereço | O que é |
|---|---|
| http://127.0.0.1:8000 | Interface web |
| http://127.0.0.1:8000/docs | Documentação interativa da API (Swagger) |
| http://127.0.0.1:8000/redoc | Documentação alternativa |
| http://127.0.0.1:8000/api/saude | Verificação de disponibilidade |

Para encerrar, pressione `Ctrl + C` no terminal.

**Testes automatizados** (cobrem os três critérios de aceite):
```bash
pytest -v
```

**Recomeçar com o banco limpo:** apague o arquivo `gestao_veiculos.db` e rode `python -m app.seed`.

O seed cria 6 veículos, 4 motoristas e 47 deslocamentos distribuídos nos últimos 90 dias e nos próximos dias. Ele só roda se o banco estiver vazio, então não sobrescreve dados reais.

---

## Funcionalidades

### Painel
- Quadro das próximas saídas previstas, com destino, veículo, motorista e finalidade.
- Cinco indicadores calculados ao vivo a partir do banco:
  - **Veículos cadastrados**, com quebra entre disponíveis e em viagem
  - **Deslocamentos no período**, com quebra entre previstos e realizados
  - **Taxa de realização (%)** — realizadas ÷ (previstas + realizadas)
  - **Distância percorrida (km)** e média de km por viagem
  - **Taxa de utilização da frota (%)** — veículos com ao menos uma viagem no período
- Gráficos de barras: previstas × realizadas, deslocamentos por finalidade, destinos mais frequentes.
- Filtro de período que recalcula todos os indicadores. Por padrão o painel mostra 90 dias de histórico e 30 dias de agenda futura.

### Veículos (CRUD completo)
Cadastro com placa, marca, modelo, ano, cor, tipo, quilometragem e situação. Busca por placa, modelo ou marca, filtro por situação, edição e exclusão. A placa é validada nos padrões `ABC1234` e `ABC1D23` e não aceita duplicidade. Veículo com histórico de viagens não pode ser excluído — a situação muda para inativo.

### Motoristas
Cadastro com nome, CNH, categoria, validade da habilitação, telefone, setor e situação. CNH única. Motorista inativo não aparece para escalonamento.

### Deslocamentos
Registro com veículo, motorista, destino, data de saída, data de retorno, finalidade, quilometragem inicial e final e observação. Situações: prevista, em andamento, realizada e cancelada.

O sistema bloqueia:
- data de retorno anterior à data de saída;
- km final menor que o km inicial;
- conclusão de viagem sem data de retorno;
- o mesmo veículo em dois deslocamentos com datas sobrepostas;
- veículo em manutenção ou inativo e motorista inativo.

Ao concluir uma viagem, informando o km final, o sistema atualiza a quilometragem do veículo e o devolve para "disponível".

### Histórico
Consulta com sete filtros combináveis: destino, veículo, motorista, situação, finalidade e intervalo de datas de saída.

### Interface
Responsiva de 320 px ao desktop — navegação lateral no computador, barra inferior no celular. Foco de teclado visível, rótulos associados aos campos e `prefers-reduced-motion` respeitado.

---

## Como usar pela primeira vez

1. Abra http://127.0.0.1:8000 — o painel carrega com os dados de demonstração.
2. Vá em **Veículos** e cadastre um veículo da sua frota.
3. Vá em **Motoristas** e cadastre um condutor.
4. Em **Deslocamentos**, clique em "Registrar deslocamento", informe destino, data e finalidade.
5. Quando o veículo retornar, clique em **Concluir** na linha correspondente e informe o km final.
6. Volte ao **Painel** para ver os indicadores atualizados.

---

## Estrutura do projeto

```
Desafio03_Gestao_Veiculos/
├── CONTEXTO.md          Concepção: requisitos, critérios de aceite, arquitetura, sprints
├── CLAUDE.md            Instruções para desenvolvimento assistido por IA
├── README.md            Este arquivo
├── requirements.txt     Dependências
├── run.bat / run.sh     Execução em um comando
├── app/
│   ├── main.py          Aplicação FastAPI
│   ├── database.py      Conexão SQLite e sessão
│   ├── models.py        Entidades Veiculo, Motorista, Deslocamento
│   ├── schemas.py       Contratos e validações
│   ├── seed.py          Dados de demonstração
│   ├── routers/         veiculos · motoristas · deslocamentos · dashboard
│   └── static/          index.html · css · js
└── tests/test_api.py    Critérios de aceite automatizados
```

---

## Limitações conhecidas

Este é um MVP. O que ainda **não** existe:

| Limitação | Detalhe |
|---|---|
| **Sem autenticação** | Não há login, perfis ou controle de acesso. Qualquer pessoa com o endereço pode ver e alterar tudo. Use apenas em rede local ou na própria máquina. |
| **Sem auditoria** | O sistema não registra quem criou ou alterou cada registro. |
| **Monousuário na prática** | O SQLite não lida bem com escrita simultânea de vários usuários. Para uso compartilhado, migre para PostgreSQL (basta trocar a URL em `app/database.py`). |
| **Sem exportação** | Não há geração de CSV, Excel ou PDF do histórico e dos indicadores. |
| **Destino em texto livre** | Digitar "Campinas" e "Campinas - SP" cria dois destinos distintos no ranking. Não há cadastro de destinos. |
| **Sem fluxo de aprovação** | O deslocamento é registrado direto, sem etapa de solicitação e autorização. |
| **Sem controle de custos** | Combustível, pedágio, multas e manutenção estão fora do escopo. |
| **Sem alertas** | CNH vencendo e viagens previstas em atraso não geram aviso. |
| **Sem migrações** | As tabelas são criadas automaticamente. Alterar um modelo exige apagar o banco e recarregar os dados. |
| **Sem paginação na interface** | O histórico traz no máximo 200 registros por consulta. |
| **Quilometragem manual** | Não há integração com telemetria; os valores dependem do que for digitado. |
| **Fontes via internet** | A tipografia vem do Google Fonts; sem conexão, a interface usa fontes do sistema e continua funcionando. |

A Sprint 3, descrita em `CONTEXTO.md`, endereça autenticação, auditoria, exportação, alertas, controle de manutenção e migrações.

---

## Solução de problemas

| Sintoma | O que fazer |
|---|---|
| `'python' não é reconhecido` | Instale o Python e marque "Add Python to PATH", ou use `py` no lugar de `python`. |
| `Address already in use` | A porta 8000 está ocupada. Rode `uvicorn app.main:app --port 8001`. |
| Painel sem dados | Rode `python -m app.seed` ou cadastre veículos e deslocamentos pela interface. |
| Erro ao alterar um modelo | Apague `gestao_veiculos.db` e rode `python -m app.seed` novamente. |
| `ModuleNotFoundError` | Ative o ambiente virtual e rode `pip install -r requirements.txt`. |
| Execute sempre da raiz | Os comandos `uvicorn app.main:app` e `pytest` precisam ser rodados na pasta do projeto. |
