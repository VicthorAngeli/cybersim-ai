# API REST

Base local: `http://localhost:8000`; Swagger interativo em `/docs`. JSON UTF-8. Rotas de negócio usam `Authorization: Bearer <JWT>`.

| Método | Rota | Papel / finalidade |
|---|---|---|
| GET | `/health` | Saúde e provedor selecionado |
| POST | `/api/v1/auth/token` | Login JSON `{ "email": "...", "password": "..." }` |
| GET | `/api/v1/auth/me` | Perfil autenticado |
| GET/POST | `/api/v1/companies` | Listar por tenant; criar empresa (admin) |
| GET | `/api/v1/companies/{company_id}` | Empresa no escopo autorizado |
| GET/POST | `/api/v1/exercises` | Listar e criar exercício |
| GET | `/api/v1/exercises/{exercise_id}` | Detalhes sem revelar inject futuro |
| POST | `/api/v1/exercises/{id}/scenario/generate` | Gera/regenera cenário enquanto planejado |
| POST | `/api/v1/exercises/{id}/start` | Gera cenário com `incident_type` |
| POST | `/api/v1/exercises/{id}/objectives/assessments` | Nota humana 0–4 associada a IDs de evidência |
| POST | `/api/v1/exercises/{id}/injects/release-next` | Libera próximo inject (admin/facilitator) |
| POST | `/api/v1/exercises/{id}/decisions` | Registrar decisão |
| GET | `/api/v1/exercises/{id}/agents` | Execuções estruturadas |
| POST | `/api/v1/exercises/{id}/agents/run` | Executar análise SOC/comunicações |
| POST | `/api/v1/exercises/{id}/complete` | Consolidar e concluir |
| GET | `/api/v1/exercises/{id}/report?format=json\|html\|markdown` | Relatório após conclusão |
| GET | `/api/v1/exercises/{id}/insights` | Ações e rascunhos |
| PATCH | `/api/v1/exercises/{id}/actions/{action_id}` | Atualizar status de ação |
| PATCH | `/api/v1/exercises/{id}/communications/{draft_id}` | Aprovar/rejeitar rascunho; não envia |
| GET | `/api/v1/analytics/export` | ZIP de CSVs Power BI no escopo do tenant |
| GET | `/api/v1/analytics/summary` | KPIs do dashboard interno |
| GET/POST | `/api/v1/admin/users` | Administrar perfis (admin) |
| GET/POST | `/api/v1/admin/calendar` | Consultar/cadastrar feriados |
| GET | `/api/v1/admin/audit` | Histórico de auditoria |

Erros usam códigos HTTP e `detail` explícito; não há fallback de IA apresentado como sucesso.
