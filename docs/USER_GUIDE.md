# Guia de uso

1. Configure `.env`, selecione `LLM_PROVIDER=mock` para funcionar offline, defina `SECRET_KEY` e `ADMIN_PASSWORD`.
2. Execute `python -m alembic upgrade head` e `python -m scripts.seed_demo`.
3. Inicie API e Streamlit; acesse `http://localhost:8501` e autentique-se com o e-mail/senha configurados.
4. Em **Empresas**, cadastre somente contexto fictício. O seed já inclui Horizonte Digital Ltda.
5. Em **Novo exercício**, escolha empresa, tipo, dificuldade, duração (30–120 min) e objetivos. O registro fica planejado.
6. Em **Cenário** ou **Sala de simulação**, inicie o exercício. O narrador gera cinco injects em ordem; respostas esperadas/notes são reservadas ao facilitador.
7. Em **Sala de simulação**, revise o inject atual, libere o próximo deliberadamente, consulte as análises SOC/LGPD/comunicação e registre decisões, rationale e função responsável.
8. Toda comunicação é rascunho. Toda análise LGPD exige validação do DPO/advogado; não há envio nem notificação automática.
9. Em **Lições aprendidas**, avalie manualmente os dez critérios (identificação, classificação, comunicação interna, escalonamento, preservação de evidências, contenção, continuidade, LGPD, comunicação externa e recuperação): 0 não abordado; 1 abordado sem decisão; 2 decisão/ação proposta; 3 responsável e prazo definidos; 4 validação documentada. Notas acima de zero exigem referência a inject ou decisão do exercício. A IA não atribui nota definitiva.
10. Finalize para gerar relatório em JSON/HTML/Markdown. HTML pode ser impresso ou salvo como PDF pelo navegador.
11. Em **Power BI**, baixe o ZIP e siga as etapas em [powerbi/README.md](../powerbi/README.md).

Roles: admin gerencia tenants/usuários; facilitator conduz exercício; participant registra decisão; viewer consulta recursos permitidos. Não usar dados reais nem conduzir resposta a incidente de produção dentro do simulador.
