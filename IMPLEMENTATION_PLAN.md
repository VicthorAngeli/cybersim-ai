# CyberSim AI — Plano de implementação

## Objetivo

Construir uma plataforma demonstrável de exercícios tabletop de incidentes cibernéticos fictícios, com API FastAPI, interface Streamlit, agentes LangChain/LangGraph, persistência SQL, relatórios e integração de dados para Power BI Desktop.

## Etapas

1. **Fundação:** estrutura modular, configuração segura, dependências, Docker, SQLAlchemy e migrações.
2. **Domínio e API:** autenticação Argon2/JWT, RBAC, isolamento de tenant, empresas, exercícios, injects, decisões, auditoria e relatórios.
3. **Agentes:** adaptadores LangChain MOCK/OpenAI; cinco schemas Pydantic; StateGraph com roteamento, checkpoint por exercício e aprovação de facilitador.
4. **Interface:** Streamlit em pt-BR para empresas, configuração e condução do exercício, análises, ações, relatório e administração.
5. **Analytics:** esquema estrela, exportação CSV BOM, views SQL, tema e medidas DAX para seis páginas Power BI.
6. **Qualidade e entrega:** dados fictícios idempotentes, testes, documentação técnica/operacional/LGPD e validação de execução.

## Decisões de implementação

- OpenAI é o provedor selecionado no `.env.example`, sem segredo no repositório. A inicialização da aplicação não exige chave; chamadas de IA sem credencial retornam erro explícito. Para execução offline ponta a ponta, selecione `LLM_PROVIDER=mock`.
- PostgreSQL é o banco recomendado; SQLite é o padrão local e o backend dos testes.
- Os agentes não recebem ferramentas para executar comandos, acessar sistemas, enviar mensagens ou consultar serviços externos além da API LLM configurada.
- Liberação de inject exige papel autorizado e aprovação explícita registrada. Comunicações são rascunhos; avaliações legais são indicativas e exigem revisão humana.
- Power BI é entregue como pacote importável de CSVs, SQL, DAX, tema e documentação. Não há `.pbix` ou PBIP/TMDL inventado.
- Todos os dados de demonstração são fictícios e exportações analíticas omitem nomes de participantes.

## Critérios de validação

- API e Streamlit executáveis localmente e por Docker Compose.
- Exercício completo em MOCK: criar, iniciar, liberar cinco injects, analisar, registrar decisões, concluir, gerar relatório e exportar dados.
- Testes cobrindo autorização/tenant, estado e roteamento do grafo, schemas e integridade/granularidade do modelo analítico.
- Migração Alembic aplicável; CSVs com BOM, datas ISO e chaves relacionais consistentes.
- Documentação em português com comandos PowerShell, riscos e limitações conhecidos.
