from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, rate_limit_llm_request, require_roles
from app.core.runtime import get_orchestrator
from app.db.models import (
    ActionItem,
    AgentRun,
    AuditLog,
    CommunicationDraft,
    Decision,
    Exercise,
    InjectEvent,
    ExerciseObjective,
    ObjectiveAssessment,
    Scenario,
    ScenarioInject,
    User,
)
from app.db.session import get_db
from app.schemas.api import (
    AgentRunRequest,
    ActionItemUpdate,
    CommunicationApprovalUpdate,
    DecisionCreate,
    ExerciseCreate,
    ExerciseRead,
    InjectReleaseRequest,
    ObjectiveAssessmentCreate,
    StartExerciseRequest,
)
from app.services.exercise_service import ExerciseService
from app.services.report_service import render_report_html, render_report_markdown

router = APIRouter(prefix="/exercises", tags=["Exercícios"])


def _service(db: Session) -> ExerciseService:
    return ExerciseService(db, get_orchestrator())


@router.get("", response_model=list[ExerciseRead])
def list_exercises(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Exercise]:
    query = select(Exercise).order_by(Exercise.created_at.desc())
    if user.role != "admin":
        query = query.where(Exercise.company_id == user.company_id)
    return list(db.scalars(query))


@router.post("", response_model=ExerciseRead, status_code=201)
def create_exercise(
    data: ExerciseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
) -> Exercise:
    return _service(db).create(data, user)


@router.get("/{exercise_id}")
def get_exercise(
    exercise_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    from app.services.exercise_service import _scope_exercise
    exercise = _scope_exercise(db, exercise_id, user)
    scenario = db.get(Scenario, exercise.scenario_id) if exercise.scenario_id else None
    released = list(db.scalars(select(InjectEvent).where(
        InjectEvent.exercise_id == exercise.id
    ).order_by(InjectEvent.sequence)))
    decisions = list(db.scalars(select(Decision).where(
        Decision.exercise_id == exercise.id
    ).order_by(Decision.decided_at)))
    payload = ExerciseRead.model_validate(exercise).model_dump(mode="json")
    payload["scenario"] = None
    if scenario:
        payload["scenario"] = {
            "id": scenario.id, "name": scenario.name, "executive_summary": scenario.executive_summary,
            "incident_type": scenario.incident_type, "difficulty": scenario.difficulty,
            "learning_objectives": scenario.learning_objectives,
            "timeline": scenario.timeline,
            "inject_count": db.query(ScenarioInject).filter_by(scenario_id=scenario.id).count(),
            "facilitator_notes": scenario.facilitator_notes if user.role in {"admin", "facilitator"} else None,
        }
    payload["released_injects"] = [
        {"id": row.id, "sequence": row.sequence, "title": row.title, "description": row.description,
         "severity": row.severity, "released_at": row.released_at.isoformat()}
        for row in released
    ]
    payload["decisions"] = [
        {"id": row.id, "inject_event_id": row.inject_event_id, "description": row.description,
         "rationale": row.rationale, "responsible_role": row.responsible_role,
         "decided_at": row.decided_at.isoformat()}
        for row in decisions
    ]
    objective_rows = list(db.scalars(select(ExerciseObjective).where(
        ExerciseObjective.exercise_id == exercise.id
    ).order_by(ExerciseObjective.created_at)))
    assessments = {
        row.objective_id: row for row in db.scalars(select(ObjectiveAssessment).where(
            ObjectiveAssessment.exercise_id == exercise.id
        ))
    }
    payload["objectives"] = [
        {
            "id": objective.id, "name": objective.objective_name,
            "nist_category": objective.nist_category,
            "score": assessments[objective.id].score if objective.id in assessments else None,
            "evidence_ids": assessments[objective.id].evidence if objective.id in assessments else [],
        }
        for objective in objective_rows
    ]
    return payload


@router.get("/{exercise_id}/agents")
def list_agent_runs(
    exercise_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    from app.services.exercise_service import _scope_exercise
    exercise = _scope_exercise(db, exercise_id, user)
    rows = db.scalars(select(AgentRun).where(
        AgentRun.exercise_id == exercise.id
    ).order_by(AgentRun.created_at))
    response = []
    for row in rows:
        result = dict(row.result or {})
        if row.agent_name == "narrator" and user.role not in {"admin", "facilitator"}:
            result.pop("facilitator_notes", None)
            for inject in result.get("injects", []):
                inject.pop("facilitator_notes", None)
        response.append({
            "id": row.id, "agent_name": row.agent_name, "agent_role": row.agent_role,
            "status": row.status, "result": result, "latency_ms": row.latency_ms,
            "validated": row.validated, "started_at": row.started_at.isoformat(),
        })
    return response


@router.get("/{exercise_id}/insights")
def get_insights(
    exercise_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    from app.services.exercise_service import _scope_exercise
    exercise = _scope_exercise(db, exercise_id, user)
    actions = db.scalars(select(ActionItem).where(
        ActionItem.exercise_id == exercise.id
    ).order_by(ActionItem.created_at))
    communications = db.scalars(select(CommunicationDraft).where(
        CommunicationDraft.exercise_id == exercise.id
    ).order_by(CommunicationDraft.created_at))
    return {
        "actions": [
            {"id": row.id, "description": row.description, "priority": row.priority,
             "responsible_role": row.responsible_role,
             "due_date": row.due_date.isoformat() if row.due_date else None,
             "status": row.status}
            for row in actions
        ],
        "communications": [
            {"id": row.id, "audience": row.audience, "objective": row.objective,
             "message": row.message, "confirmed_information": row.confirmed_information,
             "pending_information": row.pending_information, "approval_status": row.approval_status}
            for row in communications
        ],
    }


@router.patch("/{exercise_id}/actions/{action_id}")
def update_action(
    exercise_id: str,
    action_id: str,
    data: ActionItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
) -> dict:
    from app.services.exercise_service import _scope_exercise
    exercise = _scope_exercise(db, exercise_id, user)
    action = db.scalar(select(ActionItem).where(
        ActionItem.id == action_id, ActionItem.exercise_id == exercise.id
    ))
    if not action:
        raise HTTPException(status_code=404, detail="Ação não encontrada.")
    action.status = data.status
    db.add(AuditLog(
        company_id=exercise.company_id, user_id=user.id, action="action_item.status_changed",
        resource_type="action_item", resource_id=action.id, details={"status": data.status},
    ))
    db.commit()
    return {"id": action.id, "status": action.status}


@router.post("/{exercise_id}/start")
def start_exercise(
    exercise_id: str,
    data: StartExerciseRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
    _: None = Depends(rate_limit_llm_request),
) -> dict:
    return _service(db).start(exercise_id, user, data.incident_type if data else None)


@router.post("/{exercise_id}/scenario/generate")
def generate_scenario(
    exercise_id: str,
    data: StartExerciseRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
    _: None = Depends(rate_limit_llm_request),
) -> dict:
    return _service(db).generate_scenario(
        exercise_id, user, data.incident_type if data else None
    )


@router.post("/{exercise_id}/injects/{inject_id}/release")
def release_inject(
    exercise_id: str,
    inject_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
    _: None = Depends(rate_limit_llm_request),
) -> dict:
    return _service(db).release_next(exercise_id, user, inject_id)


@router.post("/{exercise_id}/injects/release-next")
def release_next(
    exercise_id: str,
    data: InjectReleaseRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
    _: None = Depends(rate_limit_llm_request),
) -> dict:
    return _service(db).release_next(exercise_id, user, (data or InjectReleaseRequest()).inject_id)


@router.post("/{exercise_id}/decisions", status_code=201)
def record_decision(
    exercise_id: str,
    data: DecisionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator", "participant")),
) -> dict:
    decision = _service(db).record_decision(exercise_id, data, user)
    return {
        "id": decision.id, "exercise_id": decision.exercise_id,
        "inject_event_id": decision.inject_event_id, "description": decision.description,
        "rationale": decision.rationale, "responsible_role": decision.responsible_role,
        "decided_at": decision.decided_at.isoformat(),
    }


@router.post("/{exercise_id}/agents/run")
def run_agent(
    exercise_id: str,
    data: AgentRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
    _: None = Depends(rate_limit_llm_request),
) -> dict:
    return _service(db).run_agent(exercise_id, user, data.agent_name)


@router.post("/{exercise_id}/complete")
def complete_exercise(
    exercise_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
    _: None = Depends(rate_limit_llm_request),
) -> dict:
    return _service(db).complete(exercise_id, user)


@router.post("/{exercise_id}/objectives/assessments")
def assess_objective(
    exercise_id: str,
    data: ObjectiveAssessmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
) -> dict:
    from app.services.exercise_service import _scope_exercise
    exercise = _scope_exercise(db, exercise_id, user)
    objective = db.scalar(select(ExerciseObjective).where(
        ExerciseObjective.id == data.objective_id,
        ExerciseObjective.exercise_id == exercise.id,
    ))
    if not objective:
        raise HTTPException(status_code=404, detail="Objetivo não encontrado neste exercício.")
    if data.score > 0 and not data.evidence_ids:
        raise HTTPException(status_code=422, detail="Notas acima de zero exigem evidência registrada.")
    valid_evidence = set(db.scalars(select(InjectEvent.id).where(
        InjectEvent.exercise_id == exercise.id
    ))) | set(db.scalars(select(Decision.id).where(Decision.exercise_id == exercise.id)))
    if not set(data.evidence_ids).issubset(valid_evidence):
        raise HTTPException(status_code=422, detail="As evidências devem ser injects ou decisões deste exercício.")
    assessment = db.scalar(select(ObjectiveAssessment).where(
        ObjectiveAssessment.exercise_id == exercise.id,
        ObjectiveAssessment.objective_id == objective.id,
    ))
    if not assessment:
        assessment = ObjectiveAssessment(
            company_id=exercise.company_id, exercise_id=exercise.id,
            objective_id=objective.id, score=data.score, evidence=data.evidence_ids,
            assessed_by=user.role,
        )
        db.add(assessment)
    else:
        assessment.score = data.score
        assessment.evidence = data.evidence_ids
        assessment.assessed_by = user.role
    db.add(AuditLog(
        company_id=exercise.company_id, user_id=user.id, action="objective.assessed",
        resource_type="objective_assessment", resource_id=assessment.id,
        details={"score": data.score, "evidence_count": len(data.evidence_ids)},
    ))
    db.flush()
    db.commit()
    return {"objective_id": objective.id, "score": assessment.score, "evidence_ids": assessment.evidence}


@router.patch("/{exercise_id}/communications/{draft_id}")
def approve_communication(
    exercise_id: str,
    draft_id: str,
    data: CommunicationApprovalUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
) -> dict:
    from app.services.exercise_service import _scope_exercise
    exercise = _scope_exercise(db, exercise_id, user)
    draft = db.scalar(select(CommunicationDraft).where(
        CommunicationDraft.id == draft_id, CommunicationDraft.exercise_id == exercise.id
    ))
    if not draft:
        raise HTTPException(status_code=404, detail="Rascunho não encontrado.")
    draft.approval_status = data.status
    db.add(AuditLog(
        company_id=exercise.company_id, user_id=user.id, action=f"communication.{data.status}",
        resource_type="communication_draft", resource_id=draft.id,
        details={"review_decision": data.status},
    ))
    db.commit()
    return {"id": draft.id, "approval_status": draft.approval_status,
            "message": "Status de revisão atualizado; nenhum envio foi realizado."}


@router.get("/{exercise_id}/report", response_model=None)
def get_report(
    exercise_id: str,
    format: str = "json",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response | dict:
    service = _service(db)
    report = service.get_report(exercise_id, user)
    if format == "markdown":
        return Response(render_report_markdown(report), media_type="text/markdown; charset=utf-8")
    if format == "html":
        return Response(render_report_html(report), media_type="text/html; charset=utf-8")
    if format != "json":
        raise HTTPException(status_code=400, detail="Formato deve ser json, html ou markdown.")
    return report
