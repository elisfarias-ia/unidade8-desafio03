# Documento de Contexto — Rodagem
## Sistema de Gestão de Veículos e Deslocamentos

> **Nota (2026-10-23, Sprint 0):** documento de concepção original, mantido como fonte dos requisitos. A estrutura de pastas (§4.3) e o status das sprints (§7) foram revistos: o MVP descrito aqui foi arquivado em `legado/` e as Sprints 1 e 2 voltaram a pendentes. Onde houver divergência, prevalecem `docs/Arquitetura.md` (ADR-002, ADR-003) e `docs/backlog.md`.

| | |
|---|---|
| **Projeto** | Desafio 03 — Gestão de Veículos e Deslocamentos |
| **Codinome** | Rodagem |
| **Versão** | 0.1.0 (MVP) |
| **Stack** | Python 3.11+ · FastAPI · SQLAlchemy · SQLite · HTML/CSS/JS sem framework |
| **Status** | MVP funcional entregue (Sprint 1 e 2 concluídas) |

---

## 1. Concepção do sistema

### 1.1 Problema
Organizações com frota própria registram as saídas de veículos em planilhas, cadernos de portaria ou formulários de papel. Como consequência: não se sabe qual veículo está disponível agora, o mesmo carro é prometido a dois setores no mesmo dia, a quilometragem só é conferida quando dá problema, e não existe base confiável para responder "quanto a frota rodou no trimestre?" ou "quantas viagens programadas realmente aconteceram?".

### 1.2 Proposta de valor
Um sistema web único onde o gestor de frota cadastra veículos e motoristas, agenda e registra cada deslocamento com destino, data e finalidade, e vê em um painel o que está programado, o que foi realizado e quanto a frota rodou — tudo calculado a partir dos próprios registros, sem planilha paralela.

### 1.3 Público e cenários de uso
| Perfil | Cenário principal |
|---|---|
| **Gestor de frota** | Abre o painel pela manhã, confere as saídas do dia, aprova um pedido novo verificando se há veículo livre. |
| **Agente administrativo** | Registra o deslocamento solicitado por um setor e informa destino e finalidade. |
| **Portaria / operação** | Fecha a viagem no retorno, informando km final. |
| **Coordenação / auditoria** | Consulta o histórico filtrado por período, veículo ou finalidade para prestar contas. |

### 1.4 Escopo do MVP
**Dentro:** CRUD de veículos, CRUD de motoristas, registro e conclusão de deslocamentos, consulta de histórico com filtros, painel com indicadores calculados, persistência em SQLite, interface web responsiva.

**Fora (evolução futura):** autenticação e perfis de acesso, aprovação de solicitações em fluxo, controle de combustível e custos, manutenção preventiva, anexo de documentos, integração com telemetria/GPS, exportação em PDF/Excel, multi-unidade.

---

## 2. Requisitos

### 2.1 Requisitos funcionais

| ID | Requisito | Prioridade |
|---|---|---|
| RF01 | Cadastrar veículo com placa, marca, modelo, ano, cor, tipo, quilometragem e situação. | Obrigatório |
| RF02 | Listar, filtrar, editar e excluir veículos (CRUD completo). | Obrigatório |
| RF03 | Impedir cadastro de placa duplicada ou em formato inválido (padrão antigo ABC1234 e Mercosul ABC1D23). | Obrigatório |
| RF04 | Cadastrar e editar motoristas com nome, CNH, categoria, validade, telefone, setor e situação. | Obrigatório |
| RF05 | Registrar deslocamento informando veículo, motorista, destino, data de saída, data de retorno, finalidade, quilometragem e observação. | Obrigatório |
| RF06 | Classificar o deslocamento em prevista, em andamento, realizada ou cancelada. | Obrigatório |
| RF07 | Concluir uma viagem informando km final e data de retorno, atualizando a quilometragem do veículo. | Obrigatório |
| RF08 | Consultar histórico de deslocamentos com filtros por veículo, motorista, destino, finalidade, situação e intervalo de datas. | Obrigatório |
| RF09 | Exibir painel com indicadores calculados a partir dos dados registrados. | Obrigatório |
| RF10 | Bloquear agendamento do mesmo veículo em dois deslocamentos com intervalos sobrepostos. | Desejável |
| RF11 | Bloquear escalonamento de veículo em manutenção/inativo e de motorista inativo. | Desejável |
| RF12 | Impedir exclusão de veículo ou motorista com histórico de deslocamentos. | Desejável |
| RF13 | Exibir quadro das próximas saídas previstas na abertura do painel. | Desejável |

### 2.2 Indicadores do painel

Todos derivam das tabelas `veiculos` e `deslocamentos`; nenhum valor é armazenado pré-calculado.

| Indicador | Fórmula |
|---|---|
| Veículos cadastrados | `COUNT(veiculos)`, com quebra por disponíveis e em viagem |
| Deslocamentos no período | `COUNT(deslocamentos)` filtrado por `data_saida` |
| Viagens previstas e realizadas | `COUNT` por `status` |
| **Taxa de realização (%)** | `realizadas ÷ (previstas + realizadas) × 100` |
| **Distância percorrida (km)** | `SUM(km_final − km_inicial)` dos registros com ambos preenchidos |
| **Média de km por viagem** | `km_total ÷ viagens_realizadas` |
| **Taxa de utilização da frota (%)** | `COUNT(DISTINCT veiculo_id no período) ÷ COUNT(veiculos) × 100` |
| Deslocamentos por finalidade | `GROUP BY finalidade` |
| Destinos mais frequentes | `GROUP BY destino`, top 5 |
| Série mensal | `GROUP BY strftime('%Y-%m', data_saida)` |

Janela padrão do painel: 90 dias de histórico + 30 dias de agenda futura, para que previstas e realizadas apareçam no mesmo recorte. O período é ajustável na interface.

### 2.3 Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF01 | Backend e frontend executáveis com um único comando, sem etapa de build. |
| RNF02 | Persistência em arquivo SQLite local, com integridade referencial ativa (`PRAGMA foreign_keys=ON`). |
| RNF03 | Interface responsiva de 320 px a desktop; navegação lateral no desktop e barra inferior no celular. |
| RNF04 | Respostas da API em até 500 ms para bases de até 10 mil deslocamentos. |
| RNF05 | Documentação de API gerada automaticamente em `/docs` (OpenAPI). |
| RNF06 | Mensagens de erro em português, específicas sobre o que ocorreu e como corrigir. |
| RNF07 | Acessibilidade mínima: foco visível, rótulos associados, contraste adequado, `prefers-reduced-motion` respeitado. |
| RNF08 | Validação em duas camadas: formato e coerência no Pydantic, regras de negócio na camada de rotas. |

---

## 3. Critérios de aceite

### CA01 — Cadastro de veículo com identificação única
**Dado** que estou na tela de veículos,
**quando** eu cadastrar um veículo informando placa, marca, modelo e ano,
**então** o veículo deve aparecer na listagem com situação "Disponível" e ser persistido no banco;
**e** se a placa já existir, o sistema deve recusar com HTTP 409 e mensagem indicando a duplicidade;
**e** se a placa não seguir o padrão ABC1234 ou ABC1D23, o sistema deve recusar com HTTP 422 antes de gravar.

> Teste automatizado: `tests/test_api.py::test_ca1_cadastro_de_veiculo_com_placa_unica`

### CA02 — Registro de deslocamento e consulta de histórico
**Dado** que existem ao menos um veículo em operação e um motorista ativo,
**quando** eu registrar um deslocamento com veículo, motorista, destino, data de saída e finalidade,
**então** o registro deve ser criado com HTTP 201 e aparecer no histórico com os dados do veículo e do motorista;
**e** uma data de retorno anterior à data de saída deve ser recusada com HTTP 422;
**e** o mesmo veículo em um intervalo já ocupado deve ser recusado com HTTP 409 indicando o deslocamento conflitante;
**e** a consulta filtrada por destino deve retornar apenas os registros correspondentes.

> Teste automatizado: `tests/test_api.py::test_ca2_registro_e_historico_de_deslocamento`

### CA03 — Indicadores calculados a partir dos dados
**Dado** um conjunto conhecido de veículos e deslocamentos registrados,
**quando** eu abrir o painel para um período,
**então** o sistema deve apresentar totais de veículos, deslocamentos, viagens previstas e realizadas coerentes com a base;
**e** deve calcular taxa de realização, distância total percorrida, média de km por viagem e taxa de utilização da frota;
**e** ao alterar o período, todos os indicadores devem ser recalculados considerando apenas os deslocamentos com `data_saida` dentro do intervalo.

> Teste automatizado: `tests/test_api.py::test_ca3_indicadores_do_dashboard`

---

## 4. Arquitetura

### 4.1 Visão geral

```
┌──────────────────────────────────────────────────────────────┐
│  Navegador — interface responsiva                            │
│  index.html · styles.css · app.js (vanilla, sem build)       │
│  Painel │ Deslocamentos │ Veículos │ Motoristas              │
└───────────────────────────┬──────────────────────────────────┘
                            │ fetch / JSON sobre HTTP
┌───────────────────────────▼──────────────────────────────────┐
│  FastAPI (app/main.py)                                       │
│  ├── StaticFiles  → serve o frontend em "/"                  │
│  └── Routers      → /api/veiculos, /api/motoristas,          │
│                     /api/deslocamentos, /api/dashboard       │
├──────────────────────────────────────────────────────────────┤
│  Validação e contratos — schemas.py (Pydantic v2)            │
│  Regras de negócio    — nas rotas (conflito de agenda,       │
│                         sincronização de status e km)        │
├──────────────────────────────────────────────────────────────┤
│  ORM — models.py (SQLAlchemy 2.0)                            │
│  Sessão por requisição via dependência get_db                │
├──────────────────────────────────────────────────────────────┤
│  SQLite — gestao_veiculos.db (arquivo local, FK ativadas)    │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Decisões de arquitetura

| Decisão | Motivo | Alternativa descartada |
|---|---|---|
| FastAPI | Validação declarativa com Pydantic, OpenAPI automática, tipagem nativa. | Flask (exigiria validação e docs manuais). |
| SQLite | Requisito do desafio; zero configuração, banco em arquivo versionável. | PostgreSQL (infraestrutura desnecessária no MVP). |
| SQLAlchemy ORM | Abstrai o banco e permite migrar para PostgreSQL trocando a URL de conexão. | SQL puro (mais verboso e acoplado). |
| Frontend sem framework | Sem Node, sem build; o mesmo comando sobe API e interface. | React/Vue (etapa de build e tooling extra). |
| Frontend servido pelo FastAPI | Elimina CORS em produção e reduz a execução a um processo. | Servidor estático separado. |
| Indicadores calculados por consulta | Sempre coerentes com a base; sem tabela de agregados a sincronizar. | Materialização em tabela própria. |
| Regras de negócio nas rotas | Proporcional ao MVP; isolar em camada de serviço quando crescer. | Camada `services/` desde o início. |

### 4.3 Estrutura de pastas

```
Desafio03_Gestao_Veiculos/
├── CONTEXTO.md              Este documento
├── CLAUDE.md                Instruções para o Claude Code
├── README.md                Instalação, execução, funcionalidades, limitações
├── requirements.txt
├── run.bat / run.sh         Execução em um comando
├── gestao_veiculos.db       Banco SQLite (gerado na primeira execução)
├── app/
│   ├── main.py              Aplicação FastAPI, montagem de rotas e estáticos
│   ├── database.py          Engine, sessão, PRAGMA de chaves estrangeiras
│   ├── models.py            Veiculo, Motorista, Deslocamento e enums
│   ├── schemas.py           Contratos de entrada/saída e validações
│   ├── seed.py              Carga de dados de demonstração
│   ├── routers/
│   │   ├── veiculos.py      CRUD completo
│   │   ├── motoristas.py    CRUD completo
│   │   ├── deslocamentos.py Registro, conclusão, histórico
│   │   └── dashboard.py     Indicadores
│   └── static/
│       ├── index.html
│       ├── css/styles.css
│       └── js/app.js
└── tests/test_api.py        Critérios de aceite automatizados
```

---

## 5. Modelo de dados

### 5.1 Entidades

```
┌────────────────────┐          ┌──────────────────────────┐          ┌────────────────────┐
│ Veiculo            │          │ Deslocamento             │          │ Motorista          │
├────────────────────┤          ├──────────────────────────┤          ├────────────────────┤
│ id          PK     │─────┐    │ id             PK        │    ┌─────│ id          PK     │
│ placa       UNIQUE │  1  └───<│ veiculo_id     FK        │>───┘  1  │ nome               │
│ marca              │     N    │ motorista_id   FK        │     N    │ cnh         UNIQUE │
│ modelo             │          │ destino                  │          │ categoria_cnh      │
│ ano                │          │ data_saida      (índice) │          │ validade_cnh       │
│ cor                │          │ data_retorno             │          │ telefone           │
│ tipo               │          │ finalidade      (enum)   │          │ setor              │
│ km_atual           │          │ status          (enum)   │          │ ativo              │
│ status      (enum) │          │ km_inicial / km_final    │          │ criado_em          │
│ criado_em          │          │ observacao               │          └────────────────────┘
└────────────────────┘          │ criado_em                │
                                │ km_percorrido (derivado) │
                                └──────────────────────────┘
```

### 5.2 Enumerações
- `StatusVeiculo`: `disponivel`, `em_viagem`, `manutencao`, `inativo`
- `StatusDeslocamento`: `previsto`, `em_andamento`, `realizado`, `cancelado`
- `Finalidade`: `administrativa`, `operacional`, `manutencao`, `entrega`, `visita_tecnica`, `outros`

### 5.3 Regras de integridade
1. `placa` e `cnh` são únicas.
2. `data_retorno >= data_saida`.
3. `km_final >= km_inicial`.
4. Deslocamento com status `realizado` exige `data_retorno`.
5. Um veículo não pode ter dois deslocamentos `previsto`/`em_andamento` com intervalos sobrepostos.
6. Veículo em `manutencao`/`inativo` e motorista inativo não podem ser escalados.
7. Veículo ou motorista com histórico não pode ser excluído (`ondelete=RESTRICT`); use a situação "inativo".
8. Concluir uma viagem atualiza `km_atual` do veículo e o devolve a `disponivel`.

---

## 6. API

Documentação interativa em `http://127.0.0.1:8000/docs`.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/saude` | Verificação de disponibilidade |
| `POST` | `/api/veiculos` | Cadastrar veículo |
| `GET` | `/api/veiculos` | Listar com `busca` e `status` |
| `GET` | `/api/veiculos/{id}` | Obter um veículo |
| `PUT` | `/api/veiculos/{id}` | Atualizar |
| `DELETE` | `/api/veiculos/{id}` | Excluir (bloqueado se houver histórico) |
| `POST` | `/api/motoristas` | Cadastrar motorista |
| `GET` | `/api/motoristas` | Listar com `busca` e `apenas_ativos` |
| `GET` · `PUT` · `DELETE` | `/api/motoristas/{id}` | Obter, atualizar, excluir |
| `POST` | `/api/deslocamentos` | Registrar deslocamento |
| `GET` | `/api/deslocamentos` | Histórico com filtros combináveis |
| `GET` · `PUT` · `DELETE` | `/api/deslocamentos/{id}` | Obter, atualizar, excluir |
| `POST` | `/api/deslocamentos/{id}/concluir` | Fechar viagem com `km_final` e `data_retorno` |
| `GET` | `/api/dashboard/indicadores` | Indicadores com `data_inicio` e `data_fim` |

**Convenção de erros:** `422` validação de formato · `404` recurso inexistente · `409` conflito de regra de negócio.

---

## 7. Planejamento — MVP e sprints

### Sprint 1 — Fundação e cadastro *(concluída)*
**Objetivo:** base de dados e CRUD de veículos funcionando ponta a ponta.
- Estrutura do projeto, `database.py`, modelos e criação automática de tabelas.
- CRUD completo de veículos com validação de placa e unicidade.
- Cadastro de motoristas.
- Layout base responsivo com navegação entre seções.
- Script de carga de dados de demonstração.

**Entrega:** cadastrar e listar veículos pela interface, com dados persistidos.
**Aceite:** CA01.

### Sprint 2 — Deslocamentos, histórico e painel *(concluída)*
**Objetivo:** registrar viagens e medir a operação.
- Entidade `Deslocamento` com relacionamentos e enums.
- Registro, edição, conclusão e exclusão de deslocamentos.
- Regras de conflito de agenda, situação de veículo e sincronização de quilometragem.
- Histórico com sete filtros combináveis.
- Endpoint de indicadores e painel com quadro de próximas saídas, cartões e gráficos de barras.
- Testes automatizados dos três critérios de aceite.

**Entrega:** MVP completo e executável.
**Aceite:** CA02 e CA03.

### Sprint 3 — Controle, confiabilidade e operação *(próxima)*
**Objetivo:** preparar o sistema para uso real por mais de uma pessoa.

| Item | Entrega |
|---|---|
| Autenticação e perfis | Login com JWT; perfis de gestor (escrita) e consulta (leitura). |
| Auditoria | Registro de quem criou/alterou cada deslocamento. |
| Exportação | Histórico e indicadores em CSV e PDF para prestação de contas. |
| Alertas | Avisos de CNH vencendo e de viagens previstas em atraso. |
| Manutenção | Agenda de revisões por quilometragem com bloqueio automático do veículo. |
| Evolução do painel | Série temporal navegável e ranking por motorista e por setor. |
| Infraestrutura | Migrações com Alembic, variáveis de ambiente, cobertura de testes acima de 80%, empacotamento Docker. |

**Aceite da sprint:** usuário sem permissão não consegue alterar dados; relatório exportado confere com o painel; veículo com revisão vencida não pode ser escalado.

---

## 8. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| SQLite com escrita concorrente | Médio | Uso monoposto no MVP; migrar para PostgreSQL trocando a URL de conexão. |
| Ausência de autenticação | Alto | Restringir a rede interna até a Sprint 3. |
| Quilometragem informada manualmente | Médio | Validação `km_final >= km_inicial` e preenchimento automático do km inicial. |
| Destino em texto livre gera duplicatas no ranking | Baixo | Normalizar em tabela de destinos em evolução futura. |
| Dados de demonstração confundidos com reais | Médio | `seed.py` só roda com o banco vazio e está documentado no README. |

---

## 9. Glossário

| Termo | Definição |
|---|---|
| **Deslocamento** | Uma saída de veículo com motorista, destino, data e finalidade definidos. |
| **Viagem prevista** | Deslocamento agendado que ainda não ocorreu. |
| **Viagem realizada** | Deslocamento concluído, com data de retorno registrada. |
| **Taxa de realização** | Proporção de viagens programadas que efetivamente aconteceram. |
| **Taxa de utilização da frota** | Percentual de veículos que fizeram ao menos uma viagem no período. |
| **Conflito de agenda** | Tentativa de escalar o mesmo veículo em dois períodos sobrepostos. |
