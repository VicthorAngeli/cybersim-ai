# Modelo dimensional e granularidade

O exportador constrói dimensões e fatos separados do modelo transacional. Chaves inteiras são determinísticas na ordem UUID do snapshot; `*_id` mantém a chave natural. Atualize o pacote completo junto para que os fatos e dimensões preservem correspondência.

| Tabela | Granularidade |
|---|---|
| dim_empresa | Uma linha por empresa incluída no escopo |
| dim_exercicio | Uma linha por exercício |
| dim_cenario | Uma linha por cenário |
| dim_agente | Uma linha por nome de agente |
| dim_participante | Uma linha por participante/slot, sem nome |
| dim_objetivo | Uma linha por objetivo de exercício |
| dim_data | Uma linha por data usada em fatos |
| fato_exercicios | Uma linha por exercício |
| fato_injects | Uma linha por acontecimento liberado |
| fato_decisoes | Uma linha por decisão |
| fato_execucoes_agente | Uma linha por execução |
| fato_achados | Uma linha por achado |
| fato_acoes_melhoria | Uma linha por ação |
| fato_comunicacoes | Uma linha por rascunho |
| fato_avaliacao_objetivos | Uma linha por avaliação do objetivo |

## Relacionamentos no Power BI

Criar relações 1:N, filtro unidirecional de dimensão para fato:

- `dim_empresa[company_key]` para `[company_key]` em todas as tabelas fato.
- `dim_exercicio[exercise_key]` para `[exercise_key]` em todas as tabelas fato.
- `dim_cenario[scenario_key]` para `[scenario_key]` em todas as tabelas fato.
- `dim_agente[agent_key]` → `fato_execucoes_agente[agent_key]`.
- `dim_objetivo[objective_key]` → `fato_avaliacao_objetivos[objective_key]`.
- `dim_exercicio[exercise_key]` → `dim_participante[exercise_key]`.
- `dim_data[date_key]` para `[date_key]` em cada fato. Cada relação é ativa em sua própria tabela de fatos.

Não conectar `dim_empresa` diretamente a `dim_exercicio` nem `dim_cenario` a `dim_exercicio`: todas as fatos já têm suas próprias chaves, evitando caminhos ambíguos. `dim_exercicio` também carrega company/scenario como atributos informativos, não como relação ativa.
