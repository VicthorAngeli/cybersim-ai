# Modelo de ameaças

## Ativos

- Dados organizacionais de contexto, exercícios, decisões, análises e rascunhos.
- Credenciais, tokens, segredo JWT e chave opcional do provedor.
- Estado LangGraph e checkpoints de exercícios.
- Integridade e confidencialidade dos CSVs de análise.

## Limites de confiança e ameaças

| Ameaça | Impacto | Controle presente | Risco residual |
|---|---|---|---|
| Acesso cruzado entre empresas | Exposição de exercício | Escopo por `company_id`, autorização de papel e teste de tenant | Rever filtros a cada novo endpoint |
| Prompt injection em contexto/decisão | Saída inadequada ou desvio de tarefa | Instruções fixas, entrada JSON não confiável, sem ferramentas, schema Pydantic | Modelos podem produzir conteúdo incorreto |
| Saída alucinada jurídica/SOC | Decisão indevida | Fatos/hipóteses separados, disclaimers, revisão humana | Revisão humana obrigatória |
| Exposição de segredos em log/repositório | Uso indevido de conta | `.env` ignorado, `.env.example` vazio, logs estruturados | Operação deve proteger arquivos/telemetria |
| CSV formula injection | Execução de fórmula ao abrir planilha | Escape de strings com prefixos de fórmula | Validar comportamento em versões de Excel/Power Query |
| Repetição/consumo excessivo de LLM | Custo e indisponibilidade | Limite por exercício, timeout, retries e tokens por chamada | Não substitui rate limit de gateway/provedor |
| Liberação não autorizada de acontecimento | Compromisso do exercício | RBAC e interrupção LangGraph; ordem sequencial | Gestão de sessão e logs ainda devem ser endurecidos |
| Comunicação precipitada | Dano reputacional/privacidade | Rascunho, sem envio automático, aprovação humana | Processo de aprovação é organizacional |
| Perda de checkpoint em reinício SQLite | Interrupção do exercício | PostgreSQL checkpointer documentado | SQLite usa memória e não recupera estado após reinício |

## Uso seguro

Somente conteúdo fictício, ambientes autorizados e treinamento. Não inserir segredo real, dado pessoal real, payload ou instrução operacional de ataque. Incidentes reais devem seguir processos de resposta aprovados e aconselhamento jurídico.
