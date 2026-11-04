# CyberSim AI

Plataforma em português brasileiro para exercícios tabletop de resposta a crises cibernéticas **fictícias**. O produto é de treinamento: não executa ataques, testes de invasão, ações em infraestrutura real nem envio externo de comunicações.

## Funcionalidades

- Cadastro de empresas de treinamento e exercícios com duração entre 30 e 120 minutos.
- Biblioteca demonstrativa de cinco classes de incidentes e cenário personalizado com cinco acontecimentos progressivos.
- API FastAPI com Swagger, JWT, Argon2, perfis e isolamento por empresa.
- Cinco agentes com respostas Pydantic e fluxo StateGraph LangGraph: narrador, SOC, LGPD, comunicações e consolidador.
- MOCK offline selecionável, além do adaptador OpenAI-compatible opcional.
- Liberação de acontecimentos pelo facilitador, decisões, análises, rascunhos, ações e relatório HTML/Markdown.
- Exportação analítica em esquema estrela para Power BI Desktop (CSV com BOM, SQL, DAX e tema).
- Streamlit com fluxo de empresas, exercícios, sala, análises, ações, relatórios e administração.

## Tecnologias e versões fixadas

Python 3.13; FastAPI 0.115.12; Pydantic 2.11.3; SQLAlchemy 2.0.40; Alembic 1.15.2; PostgreSQL 16; PyJWT 2.10.1; argon2-cffi 23.1.0; Streamlit 1.45.0; LangChain 0.3.25; langchain-core 0.3.59; LangGraph 0.4.3; langchain-openai 0.3.16; Pytest 8.3.5; Ruff 0.11.8. Veja `requirements.txt` para a lista completa.

## Executar localmente no Windows PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `.env`: defina um `SECRET_KEY` aleatório e `ADMIN_PASSWORD` com pelo menos 12 caracteres. Para demonstração sem uma API externa, configure `LLM_PROVIDER=mock`. O `.env.example` seleciona OpenAI; sem `OPENAI_API_KEY`, o aplicativo inicia, mas chamadas de agentes falham explicitamente até que a chave seja configurada ou o MOCK seja selecionado. Se usar Docker Compose, configure também um `POSTGRES_PASSWORD` forte, exclusivo e hexadecimal (por exemplo, gere com `python -c "import secrets; print(secrets.token_hex(32))"`). Chaves compartilhadas em chats devem ser revogadas; crie outra e insira-a somente no `.env` local, nunca no código, Git ou interface da aplicação.

```powershell
python -m alembic upgrade head
python -m scripts.seed_demo
```

O seed cria dados fictícios e o administrador somente quando `ADMIN_PASSWORD` estiver configurada. Não existe senha padrão. Execute API e UI em dois terminais:

```powershell
uvicorn app.main:app --reload
```

```powershell
streamlit run app/ui/main.py
```

URLs locais: Streamlit `http://localhost:8501`, Swagger `http://localhost:8000/docs`, saúde `http://localhost:8000/health`.

## Docker Compose

Com `.env` preenchido, execute:

```powershell
docker compose up --build
```

PostgreSQL é persistido no volume `postgres_data`. As portas de desenvolvimento são vinculadas somente a `127.0.0.1`. Em produção, substitua `POSTGRES_PASSWORD` e `SECRET_KEY`, configure credenciais e TLS, aplique as migrações e não exponha as portas de desenvolvimento sem controles apropriados.

## Testes e qualidade

```powershell
pytest
ruff check .
```

O banco de testes usa SQLite. Verifique a documentação em [docs/USER_GUIDE.md](docs/USER_GUIDE.md) e a arquitetura em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## IA e limites

OpenAI é a seleção de provedor no `.env.example`; nenhuma chave é incluída. Configure `OPENAI_API_KEY` e `OPENAI_MODEL` conforme sua conta/provedor. `LLM_PROVIDER=mock` permite executar o ciclo demonstrativo sem chave. Não há chamada direta a ferramentas externas pelos agentes, nem fallback silencioso de provedor. Limites por exercício e timeout/retries estão configurados.

## Power BI

Baixe o ZIP em `GET /api/v1/analytics/export` após login. Consulte [powerbi/README.md](powerbi/README.md) para importação, relações, DAX, design e publicação opcional. O projeto não fornece arquivo PBIX falso.

## Estrutura

`app/api`: rotas; `app/agents`, `app/llm`, `app/orchestrator`: IA e fluxo; `app/db`: persistência; `app/services`: regras de negócio/relatório; `app/ui`: Streamlit; `app/analytics`: exportador; `alembic`: migrações; `powerbi`: pacote analítico; `docs`: documentação; `tests`: qualidade.

## Limitações conhecidas

- O adaptador OpenAI requer uma credencial válida e conectividade externa para chamadas reais; MOCK não requer credenciais.
- O PostgreSQL checkpointer precisa de PostgreSQL acessível; SQLite usa checkpoint em memória (perde checkpoints ao reiniciar o processo).
- O prazo LGPD é indicativo e não calculado automaticamente; DPO/advogado e calendário aplicável devem validar fatos, prazo e decisão.
- Scores de objetivos são atribuídos por humanos com evidências; a IA não define nota definitiva.
- A exportação CSV é um snapshot. No Power BI, atualize as tabelas ao substituir o pacote.
- A implantação requer hardening operacional (TLS, gestão de segredos, backup, política de retenção e observabilidade).
