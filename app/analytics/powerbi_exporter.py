import csv
import io
import tempfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ActionItem,
    AgentRun,
    CommunicationDraft,
    Company,
    Decision,
    Exercise,
    ExerciseObjective,
    Finding,
    InjectEvent,
    ObjectiveAssessment,
    Participant,
    Scenario,
)

POWERBI_DIR = Path(__file__).resolve().parents[2] / "powerbi" / "exports"
AGENTS = {
    "narrator": "Narrador / Simulador",
    "soc": "Analista SOC",
    "legal": "Analista LGPD",
    "communications": "Comunicações de crise",
    "consolidator": "Consolidador de inteligência",
}


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _date_key(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return int(value.strftime("%Y%m%d"))
    try:
        return int(str(value)[:10].replace("-", ""))
    except ValueError:
        return None


def _safe_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def _write_csv(directory: Path, name: str, rows: list[dict], columns: list[str]) -> int:
    path = directory / f"{name}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _safe_cell(row.get(column)) for column in columns})
    return len(rows)


def export_powerbi(
    db: Session, output_dir: Path | None = None, company_id: str | None = None
) -> dict[str, Any]:
    """Write a consistent, non-PII star-schema snapshot as Excel-friendly UTF-8-BOM CSVs."""
    directory = output_dir or POWERBI_DIR
    directory.mkdir(parents=True, exist_ok=True)

    def query(model: Any, order_by: Any) -> list:
        statement = select(model)
        if company_id:
            company_column = Company.id if model is Company else model.company_id
            statement = statement.where(company_column == company_id)
        order_columns = order_by if isinstance(order_by, tuple) else (order_by,)
        return list(db.scalars(statement.order_by(*order_columns)))

    companies = query(Company, Company.id)
    exercises = query(Exercise, Exercise.id)
    scenarios = query(Scenario, Scenario.id)
    participants = query(Participant, Participant.id)
    objectives = query(ExerciseObjective, ExerciseObjective.id)
    injects = query(InjectEvent, (InjectEvent.exercise_id, InjectEvent.sequence))
    decisions = query(Decision, Decision.id)
    agent_runs = query(AgentRun, AgentRun.id)
    findings = query(Finding, Finding.id)
    actions = query(ActionItem, ActionItem.id)
    communications = query(CommunicationDraft, CommunicationDraft.id)
    assessments = query(ObjectiveAssessment, ObjectiveAssessment.id)

    company_keys = {row.id: i for i, row in enumerate(companies, start=1)}
    exercise_keys = {row.id: i for i, row in enumerate(exercises, start=1)}
    scenario_keys = {row.id: i for i, row in enumerate(scenarios, start=1)}
    participant_keys = {row.id: i for i, row in enumerate(participants, start=1)}
    objective_keys = {row.id: i for i, row in enumerate(objectives, start=1)}
    agent_names = sorted(set(AGENTS) | {run.agent_name for run in agent_runs})
    agent_keys = {name: i for i, name in enumerate(agent_names, start=1)}

    all_datetimes: list[Any] = []
    for row in exercises:
        all_datetimes.extend([row.created_at, row.started_at, row.completed_at])
    for collection, attrs in [
        (injects, ("released_at",)),
        (decisions, ("decided_at",)),
        (agent_runs, ("started_at", "finished_at", "created_at")),
        (findings, ("created_at",)),
        (actions, ("created_at", "due_date")),
        (communications, ("created_at",)),
        (assessments, ("created_at",)),
    ]:
        for row in collection:
            all_datetimes.extend(getattr(row, attr, None) for attr in attrs)
    dates = sorted({value.date() if isinstance(value, datetime) else value for value in all_datetimes if value})
    if not dates:
        dates = [date.today()]
    date_rows = []
    month_names = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    for day in dates:
        date_rows.append({
            "date_key": int(day.strftime("%Y%m%d")), "data": day.isoformat(),
            "ano": day.year, "semestre": 1 if day.month <= 6 else 2,
            "trimestre": (day.month - 1) // 3 + 1, "mes": day.month,
            "mes_nome": month_names[day.month - 1], "dia": day.day,
            "dia_semana": day.isoweekday(), "ano_mes": day.strftime("%Y-%m"),
        })

    dim_empresa = [{
        "company_key": company_keys[row.id], "company_id": row.id, "nome_empresa": row.name,
        "segmento": row.segment, "porte": row.size, "quantidade_funcionarios": row.employee_count,
        "dados_simulados": row.demo_data,
    } for row in companies]
    dim_exercicio = [{
        "exercise_key": exercise_keys[row.id], "exercise_id": row.id, "company_key": company_keys.get(row.company_id),
        "scenario_key": scenario_keys.get(row.scenario_id), "data_inicio": _iso(row.started_at),
        "data_fim": _iso(row.completed_at), "status": row.status, "dificuldade": row.difficulty,
        "duracao_planejada": row.planned_duration, "duracao_real": row.actual_duration,
    } for row in exercises]
    dim_cenario = [{
        "scenario_key": scenario_keys[row.id], "scenario_id": row.id, "nome_cenario": row.name,
        "tipo_incidente": row.incident_type, "categoria": row.category, "dificuldade": row.difficulty,
    } for row in scenarios]
    dim_agente = [{
        "agent_key": agent_keys[name], "agent_name": name,
        "agent_role": AGENTS.get(name, "Agente especializado"),
    } for name in agent_names]
    dim_participante = [{
        "participant_key": participant_keys[row.id], "participant_id": row.id,
        "exercise_key": exercise_keys.get(row.exercise_id), "perfil": row.profile,
        "departamento": row.department,
    } for row in participants]
    dim_objetivo = [{
        "objective_key": objective_keys[row.id], "objective_id": row.id,
        "exercise_key": exercise_keys.get(row.exercise_id), "nome_objetivo": row.objective_name,
        "categoria_nist": row.nist_category,
    } for row in objectives]

    decisions_per_inject = Counter(row.inject_event_id for row in decisions if row.inject_event_id)
    event_by_id = {row.id: row for row in injects}
    scenario_by_exercise = {row.id: scenario_keys.get(row.scenario_id) for row in exercises}
    facts_exercises = [{
        "exercise_id": row.id, "exercise_key": exercise_keys[row.id],
        "company_key": company_keys.get(row.company_id), "scenario_key": scenario_keys.get(row.scenario_id),
        "date_key": _date_key(row.started_at or row.created_at), "status": row.status,
        "dificuldade": row.difficulty, "duracao_planejada": row.planned_duration,
        "duracao_real": row.actual_duration, "participantes": row.participant_count,
    } for row in exercises]
    facts_injects = [{
        "inject_event_id": row.id, "exercise_key": exercise_keys.get(row.exercise_id),
        "company_key": company_keys.get(row.company_id), "scenario_key": scenario_by_exercise.get(row.exercise_id),
        "date_key": _date_key(row.released_at),
        "sequence": row.sequence, "titulo": row.title, "severidade": row.severity,
        "has_decision": int(decisions_per_inject.get(row.id, 0) > 0),
        "decision_count": decisions_per_inject.get(row.id, 0),
    } for row in injects]
    facts_decisions = []
    for row in decisions:
        event = event_by_id.get(row.inject_event_id)
        elapsed = None
        if event and event.released_at and row.decided_at:
            elapsed = max(0, int((row.decided_at - event.released_at).total_seconds() // 60))
        facts_decisions.append({
            "decision_id": row.id, "exercise_key": exercise_keys.get(row.exercise_id),
            "company_key": company_keys.get(row.company_id), "scenario_key": scenario_by_exercise.get(row.exercise_id),
            "inject_event_id": row.inject_event_id,
            "date_key": _date_key(row.decided_at), "responsible_role": row.responsible_role,
            "tempo_resposta_min": elapsed,
        })
    facts_agents = []
    for row in agent_runs:
        output = row.result or {}
        facts_agents.append({
            "agent_run_id": row.id, "exercise_key": exercise_keys.get(row.exercise_id),
            "company_key": company_keys.get(row.company_id), "scenario_key": scenario_by_exercise.get(row.exercise_id),
            "agent_key": agent_keys.get(row.agent_name),
            "date_key": _date_key(row.started_at or row.created_at), "status": row.status,
            "latency_ms": row.latency_ms, "tokens_used": row.tokens_used,
            "validated": int(row.validated), "attempts": 1,
            "severity": output.get("severity"), "incident_classification": output.get("incident_classification"),
            "unknowns_count": len(output.get("unknowns", [])),
            "recommendations_count": len(output.get("defensive_recommendations", [])),
            "possible_anpd_communication": output.get("possible_anpd_communication"),
            "legal_review_pending": int(output.get("legal_assessment_pending", False)),
            "data_categories": " | ".join(output.get("data_categories", [])),
        })
    facts_findings = [{
        "finding_id": row.id, "exercise_key": exercise_keys.get(row.exercise_id),
        "company_key": company_keys.get(row.company_id), "scenario_key": scenario_by_exercise.get(row.exercise_id),
        "date_key": _date_key(row.created_at),
        "categoria": row.category, "descricao": row.description, "prioridade": row.priority,
        "evidence_count": len(row.evidence or []),
    } for row in findings]
    facts_actions = [{
        "action_id": row.id, "exercise_key": exercise_keys.get(row.exercise_id),
        "company_key": company_keys.get(row.company_id), "scenario_key": scenario_by_exercise.get(row.exercise_id),
        "finding_id": row.finding_id,
        "date_key": _date_key(row.created_at), "data_prazo": _iso(row.due_date),
        "descricao": row.description, "prioridade": row.priority, "responsavel_funcao": row.responsible_role,
        "status": row.status,
    } for row in actions]
    facts_communications = [{
        "communication_id": row.id, "exercise_key": exercise_keys.get(row.exercise_id),
        "company_key": company_keys.get(row.company_id), "scenario_key": scenario_by_exercise.get(row.exercise_id),
        "date_key": _date_key(row.created_at),
        "publico_alvo": row.audience, "status_aprovacao": row.approval_status,
        "informacoes_pendentes": len(row.pending_information or []),
    } for row in communications]
    facts_assessments = [{
        "assessment_id": row.id, "exercise_key": exercise_keys.get(row.exercise_id),
        "company_key": company_keys.get(row.company_id), "scenario_key": scenario_by_exercise.get(row.exercise_id),
        "objective_key": objective_keys.get(row.objective_id),
        "date_key": _date_key(row.created_at), "score": row.score,
        "evidence_count": len(row.evidence or []), "assessed_by": row.assessed_by,
    } for row in assessments]

    datasets = {
        "dim_empresa": (dim_empresa, ["company_key", "company_id", "nome_empresa", "segmento", "porte", "quantidade_funcionarios", "dados_simulados"]),
        "dim_exercicio": (dim_exercicio, ["exercise_key", "exercise_id", "company_key", "scenario_key", "data_inicio", "data_fim", "status", "dificuldade", "duracao_planejada", "duracao_real"]),
        "dim_cenario": (dim_cenario, ["scenario_key", "scenario_id", "nome_cenario", "tipo_incidente", "categoria", "dificuldade"]),
        "dim_agente": (dim_agente, ["agent_key", "agent_name", "agent_role"]),
        "dim_participante": (dim_participante, ["participant_key", "participant_id", "exercise_key", "perfil", "departamento"]),
        "dim_objetivo": (dim_objetivo, ["objective_key", "objective_id", "exercise_key", "nome_objetivo", "categoria_nist"]),
        "dim_data": (date_rows, ["date_key", "data", "ano", "semestre", "trimestre", "mes", "mes_nome", "dia", "dia_semana", "ano_mes"]),
        "fato_exercicios": (facts_exercises, ["exercise_id", "exercise_key", "company_key", "scenario_key", "date_key", "status", "dificuldade", "duracao_planejada", "duracao_real", "participantes"]),
        "fato_injects": (facts_injects, ["inject_event_id", "exercise_key", "company_key", "scenario_key", "date_key", "sequence", "titulo", "severidade", "has_decision", "decision_count"]),
        "fato_decisoes": (facts_decisions, ["decision_id", "exercise_key", "company_key", "scenario_key", "inject_event_id", "date_key", "responsible_role", "tempo_resposta_min"]),
        "fato_execucoes_agente": (facts_agents, ["agent_run_id", "exercise_key", "company_key", "scenario_key", "agent_key", "date_key", "status", "latency_ms", "tokens_used", "validated", "attempts", "severity", "incident_classification", "unknowns_count", "recommendations_count", "possible_anpd_communication", "legal_review_pending", "data_categories"]),
        "fato_achados": (facts_findings, ["finding_id", "exercise_key", "company_key", "scenario_key", "date_key", "categoria", "descricao", "prioridade", "evidence_count"]),
        "fato_acoes_melhoria": (facts_actions, ["action_id", "exercise_key", "company_key", "scenario_key", "finding_id", "date_key", "data_prazo", "descricao", "prioridade", "responsavel_funcao", "status"]),
        "fato_comunicacoes": (facts_communications, ["communication_id", "exercise_key", "company_key", "scenario_key", "date_key", "publico_alvo", "status_aprovacao", "informacoes_pendentes"]),
        "fato_avaliacao_objetivos": (facts_assessments, ["assessment_id", "exercise_key", "company_key", "scenario_key", "objective_key", "date_key", "score", "evidence_count", "assessed_by"]),
    }

    counts = {name: _write_csv(directory, name, rows, columns) for name, (rows, columns) in datasets.items()}
    return {"directory": str(directory), "counts": counts, "total_rows": sum(counts.values()), "encoding": "UTF-8 with BOM"}


def export_zip(db: Session, company_id: str | None = None) -> tuple[bytes, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="cybersim-export-") as temp_dir:
        result = export_powerbi(db, output_dir=Path(temp_dir), company_id=company_id)
        buffer = io.BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for path in sorted(Path(result["directory"]).glob("*.csv")):
                archive.write(path, arcname=path.name)
        result["directory"] = "temporary scoped export"
        return buffer.getvalue(), result
