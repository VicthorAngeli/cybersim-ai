# Segurança e limites

- Senhas são armazenadas com Argon2; JWT HS256 usa segredo configurável e expiração.
- Perfis: `admin`, `facilitator`, `participant`, `viewer`. A API valida papel e escopo da empresa/exercício; recursos de outra empresa retornam 404.
- SQLAlchemy usa consultas parametrizadas e validação de entrada Pydantic.
- Logs JSON não incluem senha, chave de API ou conteúdo integral de dados pessoais. Logs de auditoria registram ações e IDs.
- `SECRET_KEY` de desenvolvimento não é adequada a produção; em `ENVIRONMENT=production` a aplicação rejeita o valor de exemplo.
- Antes do envio ao provedor externo OpenAI, o adaptador remove padrões comuns de e-mail, CPF, telefone, bearer token e chave `sk-`. Isso é uma minimização de melhor esforço, não detecção completa de dados pessoais; use apenas dados sintéticos e mantenha revisão humana.
- Limite de 100 execuções e 100.000 tokens reportados por exercício. Limite do provedor (timeout, retries e tokens por chamada) é configurável. O controle é por exercício; políticas globais por organização e rate limit distribuído precisam de infraestrutura antes de produção.
- O modo OpenAI requer credencial externa. O MOCK é determinístico e não faz chamadas externas.
- O grafo não dá ferramentas aos agentes; conteúdo de usuário é não confiável; respostas são validadas por schema. A aprovação humana protege liberação de inject; comunicações não são enviadas.
- CSV aplica escape preventivo em textos iniciados por prefixos de fórmula de planilha; dados analíticos não incluem nomes de participantes.

## Limitações

Este repositório é uma base de portfólio/demonstração, não uma certificação nem garantia de segurança. Ainda exige rate limiting distribuído, rotação e revogação de tokens, política de sessão, TLS, gestão de segredos, backups, monitoramento, revisão de dependências, testes de carga e avaliação independente antes de dados/uso reais. A aplicação destina-se a dados fictícios.
