# Evidências de homologação

Geradas em 2026-10-23T14:45:15 por `.\scripts\homologar.ps1` (servidor real, banco SQLite **temporário**, Chromium via Playwright). Todos os dados são fictícios. O banco do usuário não é tocado.

**Resultado: 64 OK · 0 FALHA · 8 NÃO TESTADO** — detalhes em [`resultado.json`](resultado.json).

## Capturas de tela

| Arquivo | O que mostra |
|---|---|
| [01-painel-vazio-desktop.png](01-painel-vazio-desktop.png) | Painel com banco vazio: zeros e aviso de estado vazio |
| [02-veiculos-vazio-desktop.png](02-veiculos-vazio-desktop.png) | Tela de veiculos com banco vazio |
| [03-motoristas-vazio-desktop.png](03-motoristas-vazio-desktop.png) | Tela de motoristas com banco vazio |
| [04-deslocamentos-vazio-desktop.png](04-deslocamentos-vazio-desktop.png) | Tela de deslocamentos com banco vazio |
| [05-deslocamento-sem-cadastros-422.png](05-deslocamento-sem-cadastros-422.png) | Formulário de deslocamento sem veículos/motoristas: erros de validação nos campos |
| [06-veiculo-validacao-422.png](06-veiculo-validacao-422.png) | Cadastro de veículo com placa inválida e campos obrigatórios vazios |
| [07-veiculo-placa-duplicada-409.png](07-veiculo-placa-duplicada-409.png) | Cadastro de veículo com placa já existente (409) |
| [08-veiculo-edicao.png](08-veiculo-edicao.png) | Edição de veículo com os dados atuais preenchidos |
| [09-motorista-validacao-cnh.png](09-motorista-validacao-cnh.png) | Cadastro de motorista com CNH inválida |
| [10-motoristas-lista.png](10-motoristas-lista.png) | Lista de motoristas: um ativo e um inativo |
| [11-deslocamento-formulario.png](11-deslocamento-formulario.png) | Formulário de registro de deslocamento |
| [12-deslocamento-conflito-409.png](12-deslocamento-conflito-409.png) | Registro de deslocamento com conflito de agenda (409) |
| [13-deslocamentos-lista.png](13-deslocamentos-lista.png) | Histórico de deslocamentos com os dois registros |
| [14-painel-apos-criar.png](14-painel-apos-criar.png) | Painel após criar um deslocamento em andamento e um previsto |
| [14b-veiculo-situacao-bloqueada-409.png](14b-veiculo-situacao-bloqueada-409.png) | Tentativa de tornar 'Disponível' um veículo com viagem em andamento (409) |
| [15-deslocamento-concluir.png](15-deslocamento-concluir.png) | Diálogo de conclusão de viagem com km final |
| [16-painel-apos-concluir.png](16-painel-apos-concluir.png) | Painel após concluir a viagem: previstas × realizadas e km atualizados |
| [17-confirmacao-exclusao.png](17-confirmacao-exclusao.png) | Diálogo de confirmação antes de excluir |
| [18-painel-apos-excluir.png](18-painel-apos-excluir.png) | Painel após excluir a viagem prevista |
| [19-exclusao-bloqueada-historico.png](19-exclusao-bloqueada-historico.png) | Exclusão de veículo com histórico bloqueada (409): o aviso é a evidência |
| [20-persistencia-apos-reiniciar.png](20-persistencia-apos-reiniciar.png) | Veículos após reiniciar o servidor: dados mantidos |
| [21-painel-seed-desktop.png](21-painel-seed-desktop.png) | Painel com dados de demonstração (desktop 1280 px) |
| [22-veiculos-seed-desktop.png](22-veiculos-seed-desktop.png) | Veículos com dados de demonstração |
| [23-deslocamentos-seed-desktop.png](23-deslocamentos-seed-desktop.png) | Histórico de deslocamentos com filtros e dados |
| [24-painel-mobile-375.png](24-painel-mobile-375.png) | Painel em 375 px (celular): indicadores empilhados e navegação no rodapé |
| [24b-painel-mobile-375-graficos.png](24b-painel-mobile-375-graficos.png) | Painel em 375 px: gráficos de barras |
| [25-deslocamentos-mobile-375.png](25-deslocamentos-mobile-375.png) | Histórico em 375 px: linhas viram cartões |
| [26-formulario-mobile-375.png](26-formulario-mobile-375.png) | Formulário de deslocamento em tela cheia no celular |

## Verificações

| ID | Verificação | Resultado |
|---|---|---|
| LV-00 | Banco temporário realmente vazio (API) | ✅ OK |
| LV-01 | Painel sem dados: zeros, sem NaN/undefined e aviso de estado vazio | ✅ OK |
| LV-02 | Painel mostra 'Nenhuma saída prevista' na tabela de próximas saídas | ✅ OK |
| LV-03 | Lista de veiculos vazia mostra mensagem (sem linhas em branco) | ✅ OK |
| LV-04 | Lista de motoristas vazia mostra mensagem (sem linhas em branco) | ✅ OK |
| LV-05 | Lista de deslocamentos vazia mostra mensagem (sem linhas em branco) | ✅ OK |
| LV-06 | Registrar deslocamento sem cadastros: 422 em português com campo marcado | ✅ OK |
| CA01-c | Veículo: placa inválida → 422 com a mensagem no campo placa | ✅ OK |
| CRUD-V1 | Veículo: criar 2 pela tela → aparecem na API e na tabela (placa normalizada, 'Disponível') | ✅ OK |
| CA01-b | Veículo: placa duplicada → 409 com mensagem e diálogo aberto | ✅ OK |
| CRUD-V2 | Veículo: busca filtra a tabela | ✅ OK |
| RACE-1 | Respostas fora de ordem: a busca antiga e lenta não sobrescreve a mais nova | ✅ OK |
| CRUD-V3 | Veículo: editar modelo e cor → gravado; outros campos intactos | ✅ OK |
| CRUD-M0 | Motorista: CNH com 3 dígitos → 422 no campo cnh | ✅ OK |
| CRUD-M1 | Motorista: criar 2 pela tela → CNH normalizada para 11 dígitos | ✅ OK |
| CRUD-M2 | Motorista: editar (desativar + telefone) → API e selo 'Inativo' na tabela | ✅ OK |
| CRUD-M3 | Motorista: filtro 'Somente ativos' esconde o inativo | ✅ OK |
| CA02-b | Deslocamento: retorno antes da saída → 422 na tela | ✅ OK |
| CA02-a | Deslocamento: registrar pela tela → 201; histórico traz veículo e motorista; km inicial herdado | ✅ OK |
| CRUD-D1 | Veículo do deslocamento em andamento passa a 'em viagem' | ✅ OK |
| CA02-c | Deslocamento: mesmo veículo no mesmo período → 409 citando o conflito | ✅ OK |
| CRUD-D2 | Deslocamento: segundo registro (veículo 2, previsto) criado pela tela | ✅ OK |
| CA02-d | Deslocamento: filtro por destino retorna só os correspondentes | ✅ OK |
| BUSCA-1 | Filtro de deslocamentos: escolher uma opção dispara uma única busca (antes eram duas) | ✅ OK |
| CRUD-D3 | Deslocamento: editar observação → gravada | ✅ OK |
| IND-1 | Painel após criar 2 deslocamentos: bate com o SQL independente e com o cálculo manual | ✅ OK |
| REV-1 | Veículo com viagem em andamento não pode virar 'Disponível' pela tela (409); situação mantida | ✅ OK |
| CRUD-D4 | Concluir viagem com km final menor que o inicial → 422 na tela | ✅ OK |
| CRUD-D5 | Concluir viagem → realizada, 120 km, veículo disponível e km atualizado | ✅ OK |
| IND-2 | Painel após concluir: 1 × 1, 120 km, taxa 50%, nenhum veículo em viagem | ✅ OK |
| CRUD-D6 | Deslocamento: excluir pela tela → some da tabela e da API | ✅ OK |
| IND-3 | Painel após excluir a viagem prevista: 0 × 1, taxa 100%, utilização 50% | ✅ OK |
| IND-4 | Painel: período sem dados → zeros e estado vazio; veículos continuam contados | ✅ OK |
| IND-5 | Painel: voltar à tela sem ter escolhido datas usa o período padrão da API (requisição sem datas) | ✅ OK |
| IND-6 | Painel: as datas escolhidas pelo usuário são enviadas à API | ✅ OK |
| CRUD-V4 | Excluir veículo com histórico → 409 em aviso e veículo mantido | ✅ OK |
| CONF-1 | Confirmação de exclusão: Esc cancela, não exclui e o diálogo pode ser reaberto | ✅ OK |
| CRUD-X | Excluir veículo e motorista sem histórico pela tela → removidos da API | ✅ OK |
| PERS-0 | Servidor encerrado (processo terminado) | ✅ OK |
| PERS-1 | Após reiniciar: veículos, motoristas e deslocamentos idênticos (API) | ✅ OK |
| PERS-2 | Após reiniciar: o painel mostra os mesmos indicadores | ✅ OK |
| PERS-3 | Após reiniciar: a tabela de veículos mostra os dados gravados | ✅ OK |
| SEED-1 | Seed fictício carrega em banco novo | ✅ OK |
| SEED-2 | Painel com seed (156 deslocamentos): todos os números iguais ao SQL independente | ✅ OK |
| RESP-1 | Desktop 1280 px: nenhuma das 4 telas tem rolagem horizontal | ✅ OK |
| RESP-2 | Celular 375 px: nenhuma das 4 telas tem rolagem horizontal | ✅ OK |
| INT-1 | Integração: 138 chamadas à API feitas pela interface, nenhuma resposta 5xx | ✅ OK |
| INT-2 | Integração: nenhum arquivo estático/página com erro 4xx (CSS, JS, HTML) | ✅ OK |
| INT-3 | Integração: nenhuma exceção JavaScript não tratada nas páginas | ✅ OK |
| INT-4 | Integração: erros de console limitados às recusas 4xx esperadas da API | ✅ OK |
| INT-5 | Integração: recusas 4xx vieram só de ações deliberadas (validação, conflito, exclusão bloqueada) | ✅ OK |
| ENT-1 | Entregáveis obrigatórios presentes (19 arquivos) | ✅ OK |
| ENT-2 | README: instalação e execução local (PowerShell), exemplos de uso e limitações | ✅ OK |
| ENT-3 | Critérios de aceite CA01, CA02 e CA03 têm teste automatizado | ✅ OK |
| ENT-4 | Suíte automatizada: 64 passaram, 0 falharam | ✅ OK |
| ENT-5 | Lint (ruff check) e formatação (ruff format --check) sem pendências | ✅ OK |
| SEG-1 | Git: 75 arquivos versionados e 9 commits (histórico inteiro) sem segredos, banco, chave, .env ou e-mail fora da lista permitida | ✅ OK |
| SEG-2 | .gitignore cobre .env, bancos .db, chaves .pem e ambientes virtuais | ✅ OK |
| SEG-3 | Autor dos commits configurado só neste repositório com e-mail noreply | ✅ OK |
| CLONE-1 | git clone do repositório local (só o que foi commitado) | ✅ OK |
| CLONE-2 | scripts\configurar.ps1 cria o ambiente virtual e instala as dependências | ✅ OK |
| CLONE-3 | Testes no clone limpo: 64 passaram, 0 falharam | ✅ OK |
| CLONE-4 | Seed fictício no clone (banco temporário) | ✅ OK |
| CLONE-5 | Servidor do clone sobe: página inicial e painel respondem com os dados do seed | ✅ OK |
| NT-1 | Deploy no Vercel | ⚠️ NÃO TESTADO |
| NT-2 | GitHub CLI (gh) e criação de repositório privado novo | ⚠️ NÃO TESTADO |
| NT-3 | Login / autenticação | ⚠️ NÃO TESTADO |
| NT-4 | Lint de JavaScript | ⚠️ NÃO TESTADO |
| NT-5 | Leitor de tela (acessibilidade assistiva) | ⚠️ NÃO TESTADO |
| NT-6 | Firefox, Safari/WebKit e celular físico | ⚠️ NÃO TESTADO |
| NT-7 | Uso simultâneo por várias pessoas (corrida na checagem de agenda) | ⚠️ NÃO TESTADO |
| NT-8 | Python 3.11–3.14 e outros sistemas operacionais | ⚠️ NÃO TESTADO |
