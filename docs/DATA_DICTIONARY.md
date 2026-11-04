# Dicionário de dados transacional

Todos os IDs usam UUID em texto. Tabelas de exercício incluem `company_id` e `exercise_id` quando aplicável. JSON contém listas/objetos validados pela aplicação. Datas são gravadas como `DateTime(timezone=True)` ou `Date`.

| Tabela | Granularidade / colunas relevantes |
|---|---|
| companies | Uma empresa de treinamento; segmento, porte, quantidade, sistemas e categorias fictícias |
| users | Um usuário; e-mail, hash Argon2, papel e empresa |
| participants | Uma pessoa/slot de participação por exercício; exportação analítica não contém nome |
| scenarios | Um cenário; narrativa, dificuldade, contexto e notas reservadas |
| scenario_injects | Um acontecimento ordenado de um cenário; perguntas e sinalizadores de roteamento |
| exercises | Um exercício; tipo de incidente, status, duração, objetivos e timestamps |
| exercise_objectives | Um objetivo de avaliação por exercício; categoria NIST declarada |
| inject_events | Um inject liberado pelo facilitador; severidade, texto e timestamp |
| decisions | Uma decisão registrada; rationale opcional, função responsável e horário |
| agent_runs | Uma execução de agente; status, saída estruturada, duração, tokens e validação |
| findings | Um achado/possível melhoria com evidências referenciadas |
| action_items | Uma ação vinculada a exercício e opcionalmente a achado; prioridade, função, prazo e status |
| communication_drafts | Um rascunho por público-alvo; status de aprovação; não há envio |
| objective_assessments | Uma nota humana (0–4) por objetivo e exercício; evidências registradas. Inclui os dez critérios de avaliação padrão e objetivos de aprendizagem personalizados |
| audit_logs | Um evento de auditoria, tipo/recurso e ator; sem credenciais |
| regulatory_references | Uma referência normativa/metodológica cadastrada |
| business_calendar | Um feriado por empresa e data |

## Status e escalas

- Exercício: `planejado`, `em_andamento`, `concluido`.
- Ação: `pendente`, `em_andamento`, `concluida`, `cancelada`.
- Comunicação: `rascunho`, `aprovado`, `rejeitado`.
- Avaliação de objetivo: inteiro 0–4, atribuído por pessoa e associado a IDs de evidência.
- Agente: status de execução e resultado JSON. Tokens podem ser nulos se o provedor não os reportar.

Consulte [Power BI README](../powerbi/README.md) para o dicionário das dimensões/fatos analíticos.
