"""tighten user and assessment constraints

Revision ID: ec2010b7b6e7
Revises: 8a803609591a
Create Date: 2026-11-03 16:53:52.641394
"""
from alembic import op


revision = 'ec2010b7b6e7'
down_revision = '8a803609591a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("companies") as batch:
        batch.create_check_constraint("ck_company_employee_count", "employee_count > 0")
    with op.batch_alter_table("users") as batch:
        batch.create_check_constraint("ck_user_role", "role IN ('admin', 'facilitator', 'participant', 'viewer')")
    with op.batch_alter_table("scenario_injects") as batch:
        batch.create_unique_constraint("uq_scenario_inject_sequence", ["scenario_id", "sequence"])
    with op.batch_alter_table("exercises") as batch:
        batch.create_check_constraint("ck_exercise_status", "status IN ('planejado', 'em_andamento', 'concluido')")
        batch.create_check_constraint("ck_exercise_duration", "planned_duration BETWEEN 30 AND 120")
        batch.create_check_constraint("ck_exercise_participant_count", "participant_count > 0")
    with op.batch_alter_table("exercise_objectives") as batch:
        batch.create_unique_constraint("uq_exercise_objective_name", ["exercise_id", "objective_name"])
    with op.batch_alter_table("inject_events") as batch:
        batch.create_unique_constraint("uq_exercise_inject_sequence", ["exercise_id", "sequence"])
    with op.batch_alter_table("agent_runs") as batch:
        batch.create_check_constraint("ck_agent_run_status", "status IN ('sucesso', 'falha', 'erro', 'pendente')")
    with op.batch_alter_table("action_items") as batch:
        batch.create_check_constraint("ck_action_item_status", "status IN ('pendente', 'em_andamento', 'concluida', 'cancelada')")
    with op.batch_alter_table("communication_drafts") as batch:
        batch.create_check_constraint("ck_communication_status", "approval_status IN ('rascunho', 'aprovado', 'rejeitado')")
    with op.batch_alter_table("objective_assessments") as batch:
        batch.create_unique_constraint("uq_assessment_exercise_objective", ["exercise_id", "objective_id"])
        batch.create_check_constraint("ck_assessment_score", "score BETWEEN 0 AND 4")
    with op.batch_alter_table("business_calendar") as batch:
        batch.create_unique_constraint("uq_company_holiday_date", ["company_id", "holiday_date"])

def downgrade() -> None:
    with op.batch_alter_table("business_calendar") as batch:
        batch.drop_constraint("uq_company_holiday_date", type_="unique")
    with op.batch_alter_table("objective_assessments") as batch:
        batch.drop_constraint("ck_assessment_score", type_="check")
        batch.drop_constraint("uq_assessment_exercise_objective", type_="unique")
    with op.batch_alter_table("communication_drafts") as batch:
        batch.drop_constraint("ck_communication_status", type_="check")
    with op.batch_alter_table("action_items") as batch:
        batch.drop_constraint("ck_action_item_status", type_="check")
    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_constraint("ck_agent_run_status", type_="check")
    with op.batch_alter_table("inject_events") as batch:
        batch.drop_constraint("uq_exercise_inject_sequence", type_="unique")
    with op.batch_alter_table("exercise_objectives") as batch:
        batch.drop_constraint("uq_exercise_objective_name", type_="unique")
    with op.batch_alter_table("exercises") as batch:
        batch.drop_constraint("ck_exercise_participant_count", type_="check")
        batch.drop_constraint("ck_exercise_duration", type_="check")
        batch.drop_constraint("ck_exercise_status", type_="check")
    with op.batch_alter_table("scenario_injects") as batch:
        batch.drop_constraint("uq_scenario_inject_sequence", type_="unique")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_user_role", type_="check")
    with op.batch_alter_table("companies") as batch:
        batch.drop_constraint("ck_company_employee_count", type_="check")
