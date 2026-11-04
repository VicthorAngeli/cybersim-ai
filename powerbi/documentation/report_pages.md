# Guia de construção das seis páginas

Use página 16:9 com fundo cinza-azulado claro `#DCE3EA`, cabeçalhos azul-marinho `#20385F`, cartões brancos arredondados com sombra discreta e uma paleta acessível de azul `#1687C9`, teal `#087F7A`, dourado `#A07800`, vermelho `#D9364F`, grafite `#4C5662` e violeta `#7655A3`. A mesma moldura visual, os filtros sincronizados por empresa, período (`dim_data[data]`), cenário, dificuldade e status, e a hierarquia de KPIs e painéis são aplicados às seis páginas.

1. **Executiva:** cards Total de Exercícios, Exercícios Concluídos, Total de Decisões, Ações Pendentes e Média de Cobertura; linha `dim_data[ano_mes]` × exercícios; barras por `dim_cenario[tipo_incidente]`; ações por prioridade; score por objetivo.
2. **Linha do tempo:** tabela inject com `sequence/titulo/severidade`, decisões com horário/função, tempo médio; linha por data e severidade.
3. **Operação SOC:** classificação/severidade da execução dos agentes, contagem de unknowns/recomendações, decisão por inject; evidências e continuidade são texto orientativo.
4. **LGPD e comunicação:** categorias informadas, execuções legais pendentes, possível comunicação (texto do agente, sem KPI legal conclusivo) e status dos rascunhos. Nunca exibir dados pessoais.
5. **Lições aprendidas:** achados por categoria, ações por prioridade/status/responsável/prazo; use `Ações Atrasadas` e tabela de plano.
6. **Inteligência Artificial:** execuções/agente, duração média, falhas/validação e tokens quando disponíveis. Não exibir custo sem tarifa configurada.

Use títulos curtos e evite excesso de visuais. Campo `severity` contém classificação simulada, não incidente real.
