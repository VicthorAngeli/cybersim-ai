-- Views PostgreSQL de leitura para consultas operacionais/analíticas.
-- O exportador Python gera chaves substitutas estáveis para cada snapshot CSV.
CREATE OR REPLACE VIEW vw_analytics_exercises AS
SELECT e.id AS exercise_id, e.company_id, e.scenario_id, e.title, e.status,
       e.difficulty, e.planned_duration, e.actual_duration, e.participant_count,
       e.started_at, e.completed_at, e.created_at
FROM exercises e;

CREATE OR REPLACE VIEW vw_analytics_injects AS
SELECT ie.id AS inject_event_id, ie.company_id, ie.exercise_id,
       ie.sequence, ie.title, ie.severity, ie.released_at
FROM inject_events ie;

CREATE OR REPLACE VIEW vw_analytics_decisions AS
SELECT d.id AS decision_id, d.company_id, d.exercise_id, d.inject_event_id,
       d.description, d.responsible_role, d.decided_at
FROM decisions d;

CREATE OR REPLACE VIEW vw_analytics_agent_runs AS
SELECT ar.id AS agent_run_id, ar.company_id, ar.exercise_id, ar.agent_name,
       ar.agent_role, ar.status, ar.latency_ms, ar.tokens_used, ar.validated,
       ar.started_at, ar.finished_at
FROM agent_runs ar;

CREATE OR REPLACE VIEW vw_analytics_action_items AS
SELECT ai.id AS action_id, ai.company_id, ai.exercise_id, ai.finding_id,
       ai.priority, ai.responsible_role, ai.due_date, ai.status, ai.created_at
FROM action_items ai;
