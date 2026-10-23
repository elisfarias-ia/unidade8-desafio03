# Requisitos — Rodagem

Fonte: `CONTEXTO.md` §1–3 (ver ADR-001 em `Arquitetura.md`). Este arquivo é a referência de requisitos do projeto; mudanças de escopo exigem ADR.

## 1. Problema e escopo

Frotas institucionais controlam saídas de veículos em planilhas e papel: não se sabe qual veículo está livre, o mesmo carro é prometido a dois setores e não há base confiável de quilometragem e de viagens realizadas.

**Dentro do MVP:** CRUD de veículos e de motoristas, registro e conclusão de deslocamentos, histórico com filtros, painel com indicadores calculados, persistência em SQLite, interface web responsiva.

**Fora do MVP (Sprint 3 ou depois):** autenticação e perfis, fluxo de aprovação, combustível e custos, manutenção preventiva, anexos, telemetria/GPS, exportação PDF/Excel, multiunidade.

## 2. Perfis

| Perfil | Uso principal |
|---|---|
| Gestor de frota | Confere saídas do dia e disponibilidade |
| Agente administrativo | Registra deslocamentos solicitados |
| Portaria / operação | Fecha a viagem com km final |
| Coordenação / auditoria | Consulta histórico filtrado |

No MVP não há login: todos os perfis usam a mesma interface (ver Limitações no README).

## 3. Requisitos funcionais

| ID | Requisito | Prioridade | Sprint (ADR-008) |
|---|---|---|---|
| RF01 | Cadastrar veículo (placa, marca, modelo, ano, cor, tipo, km, situação) | Obrigatório | 1 (API) · 2 (tela) |
| RF02 | Listar, filtrar, editar e excluir veículos | Obrigatório | 1 (API) · 2 (tela) |
| RF03 | Recusar placa duplicada ou fora dos padrões `ABC1234` / `ABC1D23` | Obrigatório | 1 (API) · 2 (tela) |
| RF04 | Cadastrar e editar motoristas (nome, CNH, categoria, validade, telefone, setor, situação) | Obrigatório | 1 (API) · 2 (tela) |
| RF05 | Registrar deslocamento (veículo, motorista, destino, saída, retorno, finalidade, km, observação) | Obrigatório | 1 (API) · 2 (tela) |
| RF06 | Classificar deslocamento: previsto, em andamento, realizado, cancelado | Obrigatório | 1 (API) · 2 (tela) |
| RF07 | Concluir viagem com km final e data de retorno, atualizando o km do veículo | Obrigatório | 1 (API) · 2 (tela) |
| RF08 | Histórico com filtros por veículo, motorista, destino, finalidade, situação e período | Obrigatório | 1 (API) · 2 (tela) |
| RF09 | Painel com indicadores calculados a partir dos registros | Obrigatório | 3 |
| RF10 | Bloquear o mesmo veículo em intervalos sobrepostos | Desejável | 1 (API) · 2 (tela) |
| RF11 | Bloquear veículo em manutenção/inativo e motorista inativo | Desejável | 1 (API) · 2 (tela) |
| RF12 | Impedir exclusão de veículo/motorista com histórico | Desejável | 1 (API) · 2 (tela) |
| RF13 | Quadro das próximas saídas previstas no painel | Desejável | 3 |

## 4. Indicadores do painel (RF09)

Sempre calculados por consulta; nada é armazenado pré-calculado.

| Indicador | Fórmula |
|---|---|
| Veículos cadastrados | `COUNT(veiculos)` com quebra por disponíveis e em viagem |
| Deslocamentos no período | `COUNT(deslocamentos)` por `data_saida` |
| Previstas e realizadas | `COUNT` por `status` |
| Taxa de realização (%) | `realizadas ÷ (previstas + realizadas) × 100` |
| Distância percorrida (km) | `SUM(km_final − km_inicial)` com ambos preenchidos |
| Média de km por viagem | `km_total ÷ realizadas` |
| Utilização da frota (%) | `COUNT(DISTINCT veiculo_id) ÷ COUNT(veiculos) × 100` |
| Por finalidade / top 5 destinos / série mensal | `GROUP BY` |

Janela padrão: 90 dias de histórico + 30 dias de agenda futura, ajustável.

## 5. Requisitos não funcionais

| ID | Requisito | Situação (após S1) |
|---|---|---|
| RNF01 | Backend e frontend com um único comando, sem build | Atendido (`scripts\iniciar.ps1`) |
| RNF02 | SQLite local com `PRAGMA foreign_keys=ON` | Configurado em `backend/app/database.py` |
| RNF03 | Responsivo de 320 px ao desktop | Pendente (S2) |
| RNF04 | API ≤ 500 ms com até 10 mil deslocamentos | Atendido em memória (indicadores: 22 ms de mediana); arquivo e HTTP reais não medidos |
| RNF05 | OpenAPI em `/docs` | Atendido |
| RNF06 | Mensagens de erro em português, específicas | Atendido na API (S1); exibição na S2 |
| RNF07 | Acessibilidade mínima (foco, rótulos, contraste, reduced-motion) | Parcial (foco visível) |
| RNF08 | Validação em duas camadas (Pydantic + rotas) | Atendido (S1) |
| RNF09 | Nenhum segredo, credencial real ou dado institucional no repositório | Atendido (ver `execucao.md`) |

RNF09 foi incluído na Sprint 0 a partir da instrução do projeto (ADR-007).

## 6. Regras de negócio

1. Placa única, normalizada para maiúsculas sem hífen, nos padrões `ABC1234` ou `ABC1D23`.
2. CNH única por motorista.
3. `data_retorno >= data_saida` e `km_final >= km_inicial`.
4. Deslocamento `realizado` exige `data_retorno`.
5. Sem dois deslocamentos `previsto`/`em_andamento` sobrepostos para o mesmo veículo.
6. Veículo em `manutencao`/`inativo` e motorista inativo não são escalados.
7. Veículo ou motorista com histórico não é excluído — passa a inativo.
8. Concluir viagem atualiza `km_atual` e devolve o veículo para `disponivel`.
9. Indicadores sempre calculados por consulta.

## 7. Critérios de aceite

- **CA01 — Cadastro de veículo com placa única.** Cadastro aparece na lista como "Disponível" e persiste; placa duplicada → 409; formato inválido → 422 antes de gravar.
- **CA02 — Registro e histórico de deslocamento.** Criação → 201 e aparece no histórico com veículo e motorista; retorno antes da saída → 422; intervalo ocupado → 409 indicando o conflito; filtro por destino retorna só os correspondentes.
- **CA03 — Indicadores calculados.** Totais coerentes com a base; taxa de realização, distância, média e utilização corretas; mudar o período recalcula tudo considerando só `data_saida` no intervalo.

Plano de verificação de cada critério: `docs/teste.md`.
