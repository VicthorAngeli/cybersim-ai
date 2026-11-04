import logging
import time
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.communications_agent import CrisisCommunicationsAgent
from app.agents.soc_agent import SocAnalystAgent
from app.core.config import get_settings
from app.db.models import (
    AgentRun,
    AuditLog,
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
    ScenarioInject,
    User,
)
from app.llm.provider_factory import create_provider
from app.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator
from app.orchestrator.state import ExerciseState
from app.schemas.agents import ConsolidatedReport
from app.schemas.api import DecisionCreate, ExerciseCreate
from app.services.assessment import ASSESSMENT_CRITERIA

logger = logging.getLogger(__name__)


def _company_payload(company: Company) -> dict:
    return {
        "id": company.id, "name": company.name, "segment": company.segment,
        "size": company.size, "employee_count": company.employee_count,
        "critical_systems": company.critical_systems or [],
        "data_categories": company.data_categories or [],
        "essential_processes": company.essential_processes or [],
        "security_maturity": company.security_maturity,
    }


def _scope_exercise(db: Session, exercise_id: str, user: User) -> Exercise:
    exercise = db.scalar(select(Exercise).where(Exercise.id == exercise_id))
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercício não encontrado.")
    if user.role != "admin" and exercise.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Exercício não encontrado.")
    return exercise


def _audit(db: Session, user: User, action: str, resource_type: str, resource_id: str, company_id: str) -> None:
    db.add(AuditLog(
        company_id=company_id, user_id=user.id, action=action,
        resource_type=resource_type, resource_id=resource_id, details={},
    ))


class ExerciseService:
    def __init__(self, db: Session, orchestrator: MultiAgentOrchestrator | None = None) -> None:
        self.db = db
        self.orchestrator = orchestrator or MultiAgentOrchestrator()

    def _enforce_agent_budget(self, exercise_id: str, expected_calls: int) -> None:
        run_count = self.db.scalar(
            select(func.count(AgentRun.id)).where(AgentRun.exercise_id == exercise_id)
        ) or 0
        token_count = self.db.scalar(
            select(func.coalesce(func.sum(AgentRun.tokens_used), 0)).where(AgentRun.exercise_id == exercise_id)
        ) or 0
        max_calls = max(1, 100_000 // get_settings().openai_max_tokens)
        if run_count + expected_calls > max_calls or token_count >= 100_000:
            raise HTTPException(status_code=429, detail="Limite de execuções ou tokens por exercício atingido.")

    def create(self, data: ExerciseCreate, user: User) -> Exercise:
        company = self.db.get(Company, data.company_id)
        if not company or (user.role != "admin" and user.company_id != company.id):
            raise HTTPException(status_code=404, detail="Empresa não encontrada.")
        exercise = Exercise(
            company_id=company.id, title=data.title, status="planejado",
            incident_type=data.incident_type,
            difficulty=data.difficulty, planned_duration=data.planned_duration,
            participant_count=data.participant_count, objectives=data.objectives,
            areas=data.areas, affected_systems=data.affected_systems,
            data_categories=data.data_categories,
        )
        self.db.add(exercise)
        self.db.flush()
        objective_categories = dict(ASSESSMENT_CRITERIA)
        objective_names = list(dict.fromkeys([*data.objectives, *objective_categories]))
        for objective in objective_names:
            self.db.add(ExerciseObjective(
                company_id=company.id, exercise_id=exercise.id,
                objective_name=objective, nist_category=objective_categories.get(objective),
            ))
        _audit(self.db, user, "exercise.created", "exercise", exercise.id, company.id)
        self.db.commit()
        self.db.refresh(exercise)
        return exercise

    def generate_scenario(self, exercise_id: str, user: User, incident_type: str | None = None) -> dict:
        exercise = _scope_exercise(self.db, exercise_id, user)
        if exercise.status != "planejado":
            raise HTTPException(status_code=409, detail="O cenário só pode ser gerado enquanto o exercício está planejado.")
        company = self.db.get(Company, exercise.company_id)
        if not company:
            raise HTTPException(status_code=409, detail="Empresa vinculada não está disponível.")
        self._enforce_agent_budget(exercise.id, 1)
        selected_incident = incident_type or exercise.incident_type
        if incident_type:
            exercise.incident_type = incident_type
        state: ExerciseState = {
            "exercise_id": exercise.id,
            "company_id": company.id,
            "company": _company_payload(company),
            "scenario_input": {
                "company": _company_payload(company),
                "incident_type": selected_incident,
                "difficulty": exercise.difficulty,
                "duration": exercise.planned_duration,
                "objectives": exercise.objectives,
            },
            "events": [],
            "decisions": [],
            "agent_results": {},
        }
        try:
            graph_state = self.orchestrator.generate_scenario(state)
            scenario_data = graph_state["scenario"]
            previous_scenario = self.db.get(Scenario, exercise.scenario_id) if exercise.scenario_id else None
            if previous_scenario:
                self.db.query(ScenarioInject).filter_by(scenario_id=previous_scenario.id).delete()
                self.db.delete(previous_scenario)
                self.db.flush()
            scenario = Scenario(
                company_id=company.id,
                name=scenario_data["name"],
                incident_type=scenario_data["incident_type"],
                difficulty=scenario_data["difficulty"],
                description=scenario_data["executive_summary"],
                executive_summary=scenario_data["executive_summary"],
                context=scenario_data["context"],
                learning_objectives=scenario_data["learning_objectives"],
                timeline=scenario_data["timeline"],
                facilitator_notes=scenario_data["facilitator_notes"],
                demo_data=scenario_data["demo_data"],
            )
            self.db.add(scenario)
            self.db.flush()
            exercise.scenario_id = scenario.id
            for item in scenario_data["injects"]:
                self.db.add(ScenarioInject(
                    scenario_id=scenario.id, sequence=item["sequence"], title=item["title"],
                    description=item["description"], questions=item["questions"],
                    facilitator_notes=item["facilitator_notes"],
                    involves_personal_data=item["involves_personal_data"],
                    involves_outage=item["involves_outage"],
                    requires_communication=item["requires_communication"],
                ))
            _audit(self.db, user, "scenario.generated", "scenario", scenario.id, company.id)
            self.db.add(AgentRun(
                company_id=company.id, exercise_id=exercise.id,
                agent_name="narrator", agent_role="Narrador / Simulador",
                status="sucesso", result=scenario_data,
                latency_ms=graph_state.get("agent_latencies", {}).get("narrator", 0), validated=True,
                tokens_used=graph_state.get("agent_tokens", {}).get("narrator"),
            ))
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            self.db.add(AgentRun(
                company_id=company.id, exercise_id=exercise.id,
                agent_name="narrator", agent_role="Narrador / Simulador",
                status="falha", error_message=f"Falha de execução ({type(exc).__name__}).",
                validated=False,
            ))
            self.db.commit()
            logger.error("Falha ao gerar cenário para exercício %s (%s).", exercise_id, type(exc).__name__)
            raise HTTPException(status_code=502, detail="Não foi possível gerar o cenário. Verifique o provedor de IA configurado.") from exc
        return self._scenario_summary(exercise, "Cenário gerado. Revise e regenere antes de iniciar, se necessário.")

    def start(self, exercise_id: str, user: User, incident_type: str | None = None) -> dict:
        exercise = _scope_exercise(self.db, exercise_id, user)
        if exercise.status != "planejado":
            raise HTTPException(status_code=409, detail="Somente exercícios planejados podem ser iniciados.")
        if incident_type and incident_type != exercise.incident_type:
            self.generate_scenario(exercise.id, user, incident_type)
            exercise = _scope_exercise(self.db, exercise_id, user)
        elif not exercise.scenario_id:
            self.generate_scenario(exercise.id, user)
            exercise = _scope_exercise(self.db, exercise_id, user)
        exercise.status = "em_andamento"
        exercise.started_at = datetime.now(UTC)
        _audit(self.db, user, "exercise.started", "exercise", exercise.id, exercise.company_id)
        self.db.commit()
        return self._scenario_summary(exercise, "Exercício iniciado. O próximo acontecimento depende de liberação explícita do facilitador.")

    def _scenario_summary(self, exercise: Exercise, message: str) -> dict:
        scenario = self.db.get(Scenario, exercise.scenario_id) if exercise.scenario_id else None
        if not scenario:
            raise HTTPException(status_code=409, detail="O cenário do exercício não está disponível.")
        inject_count = self.db.scalar(select(func.count(ScenarioInject.id)).where(
            ScenarioInject.scenario_id == scenario.id
        )) or 0
        return {
            "exercise_id": exercise.id,
            "status": exercise.status,
            "scenario": {
                "id": scenario.id, "name": scenario.name,
                "executive_summary": scenario.executive_summary,
                "incident_type": scenario.incident_type,
                "difficulty": scenario.difficulty,
                "learning_objectives": scenario.learning_objectives,
                "timeline": scenario.timeline,
                "inject_count": inject_count,
            },
            "message": message,
        }

    def release_next(self, exercise_id: str, user: User, requested_inject_id: str | None = None) -> dict:
        exercise = _scope_exercise(self.db, exercise_id, user)
        if exercise.status != "em_andamento" or not exercise.scenario_id:
            raise HTTPException(status_code=409, detail="Exercício sem cenário ativo.")
        released_count = self.db.scalar(
            select(func.count(InjectEvent.id)).where(InjectEvent.exercise_id == exercise.id)
        ) or 0
        inject_preview = self.db.scalar(
            select(ScenarioInject).where(
                ScenarioInject.scenario_id == exercise.scenario_id,
                ScenarioInject.sequence == released_count + 1,
            )
        )
        if not inject_preview:
            raise HTTPException(status_code=409, detail="Não há mais acontecimentos para liberar.")
        expected_calls = 1 + int(inject_preview.involves_personal_data) + int(inject_preview.requires_communication)
        self._enforce_agent_budget(exercise.id, expected_calls)
        inject = self.db.scalar(
            select(ScenarioInject).where(
                ScenarioInject.scenario_id == exercise.scenario_id,
                ScenarioInject.sequence == released_count + 1,
            )
        )
        if not inject:
            raise HTTPException(status_code=409, detail="Não há mais acontecimentos para liberar.")
        if requested_inject_id and requested_inject_id != inject.id:
            raise HTTPException(status_code=409, detail="A liberação deve seguir a ordem cronológica.")
        company = self.db.get(Company, exercise.company_id)
        scenario = self.db.get(Scenario, exercise.scenario_id)
        if not company or not scenario:
            raise HTTPException(status_code=409, detail="Dados do exercício estão incompletos.")
        current_inject = {
            "id": inject.id, "sequence": inject.sequence, "title": inject.title,
            "description": inject.description, "questions": inject.questions,
            "involves_personal_data": inject.involves_personal_data,
            "involves_outage": inject.involves_outage,
            "requires_communication": inject.requires_communication,
        }
        prior = self.orchestrator.get_state(exercise.id)
        state: ExerciseState = {
            **(prior or {}),
            "action": "run_inject",
            "exercise_id": exercise.id,
            "company_id": company.id,
            "company": _company_payload(company),
            "scenario": {
                "name": scenario.name,
                "affected_assets": exercise.affected_systems or company.critical_systems or [],
                "learning_objectives": scenario.learning_objectives or [],
            },
            "current_inject": current_inject,
            "inject_index": inject.sequence,
        }
        try:
            previously_processed = any(
                item.get("inject_id") == inject.id for item in (prior or {}).get("events", [])
            )
            result = prior if previously_processed else self.orchestrator.run_inject(state, approved_by=user.id)
            if not result:
                raise RuntimeError("Estado do grafo ausente após processamento.")
            event = InjectEvent(
                company_id=company.id, exercise_id=exercise.id, scenario_inject_id=inject.id,
                sequence=inject.sequence, title=inject.title, description=inject.description,
                severity="Alto" if inject.involves_personal_data else "Médio",
            )
            self.db.add(event)
            self.db.flush()
            current_results = result.get("agent_results", {})
            selected = ["soc"]
            if inject.involves_personal_data:
                selected.append("legal")
            if inject.requires_communication:
                selected.append("communications")
            for name in selected:
                output = current_results.get(name)
                if output is None:
                    continue
                self.db.add(AgentRun(
                    company_id=company.id, exercise_id=exercise.id,
                    agent_name=name, agent_role=name, status="sucesso",
                    result=output,
                    latency_ms=result.get("agent_latencies", {}).get(name, 0), validated=True,
                    tokens_used=result.get("agent_tokens", {}).get(name),
                ))
            communication = current_results.get("communications")
            if communication and "communications" in selected:
                self.db.add(CommunicationDraft(
                    company_id=company.id, exercise_id=exercise.id,
                    audience=communication["audience"], objective=communication["objective"],
                    context=communication["context"], message=communication["proposed_message"],
                    confirmed_information=communication["confirmed_information"],
                    pending_information=communication["pending_information"],
                    communication_risk=communication["communication_risk"],
                    approval_status="rascunho",
                ))
            _audit(self.db, user, "inject.released", "inject_event", event.id, company.id)
            self.db.commit()
            return {
                "inject": {"id": event.id, "sequence": event.sequence, "title": event.title,
                           "description": event.description, "severity": event.severity},
                "agent_results": {key: current_results[key] for key in selected if key in current_results},
                "released_count": released_count + 1,
                "next_release_requires_facilitator": released_count + 1 < self._inject_total(exercise.scenario_id),
            }
        except Exception as exc:
            self.db.rollback()
            self.db.add(AgentRun(
                company_id=company.id, exercise_id=exercise.id,
                agent_name="soc", agent_role="Análise do acontecimento",
                status="falha", error_message=f"Falha de execução ({type(exc).__name__}).",
                validated=False,
            ))
            self.db.commit()
            logger.error("Falha ao liberar inject %s do exercício %s (%s).", inject.id, exercise.id, type(exc).__name__)
            raise HTTPException(status_code=502, detail="A análise do inject falhou; nenhum acontecimento foi registrado como liberado.") from exc

    def record_decision(self, exercise_id: str, data: DecisionCreate, user: User) -> Decision:
        exercise = _scope_exercise(self.db, exercise_id, user)
        if exercise.status != "em_andamento":
            raise HTTPException(status_code=409, detail="Decisões só podem ser registradas durante o exercício.")
        if data.inject_event_id:
            event = self.db.scalar(select(InjectEvent).where(InjectEvent.id == data.inject_event_id))
            if not event or event.exercise_id != exercise.id:
                raise HTTPException(status_code=404, detail="Acontecimento não encontrado neste exercício.")
        event_id = data.inject_event_id or self.db.scalar(
            select(InjectEvent.id).where(InjectEvent.exercise_id == exercise.id).order_by(InjectEvent.sequence.desc())
        )
        decision = Decision(
            company_id=exercise.company_id, exercise_id=exercise.id, inject_event_id=event_id,
            description=data.description, rationale=data.rationale, responsible_role=data.responsible_role,
        )
        self.db.add(decision)
        _audit(self.db, user, "decision.created", "decision", decision.id, exercise.company_id)
        self.db.commit()
        self.db.refresh(decision)
        return decision

    def run_agent(self, exercise_id: str, user: User, agent_name: str | None) -> dict:
        exercise = _scope_exercise(self.db, exercise_id, user)
        if exercise.status != "em_andamento":
            raise HTTPException(status_code=409, detail="O exercício não está em andamento.")
        event = self.db.scalar(
            select(InjectEvent).where(InjectEvent.exercise_id == exercise.id).order_by(InjectEvent.sequence.desc())
        )
        if not event:
            raise HTTPException(status_code=409, detail="Libere um acontecimento antes de executar análises.")
        self._enforce_agent_budget(exercise.id, 1)
        names = {"soc": SocAnalystAgent, "communications": CrisisCommunicationsAgent}
        if agent_name not in names:
            raise HTTPException(status_code=400, detail="Execução manual permite 'soc' ou 'communications'.")
        try:
            provider = create_provider()
            agent = names[agent_name](provider)
            start = time.perf_counter()
            output = agent.run({"inject": {"title": event.title, "description": event.description},
                                "affected_assets": exercise.affected_systems or [],
                                "confirmed_information": [event.description],
                                "pending_information": ["Impacto e escopo ainda não confirmados."]})
            run = AgentRun(
                company_id=exercise.company_id, exercise_id=exercise.id, agent_name=agent_name,
                agent_role=agent.role, status="sucesso", result=output.model_dump(mode="json"),
                latency_ms=int((time.perf_counter() - start) * 1000), validated=True,
                tokens_used=provider.last_tokens_used,
            )
            self.db.add(run)
            self.db.commit()
            return {"id": run.id, "agent_name": run.agent_name, "status": run.status,
                    "result": run.result, "latency_ms": run.latency_ms, "validated": run.validated}
        except Exception as exc:
            self.db.rollback()
            self.db.add(AgentRun(
                company_id=exercise.company_id, exercise_id=exercise.id,
                agent_name=agent_name or "unknown", agent_role="Execução manual",
                status="falha", error_message=f"Falha de execução ({type(exc).__name__}).",
                validated=False,
            ))
            self.db.commit()
            logger.error("Falha na execução manual de agente %s (%s).", agent_name, type(exc).__name__)
            raise HTTPException(status_code=502, detail="A execução do agente falhou; verifique o provedor configurado.") from exc

    def complete(self, exercise_id: str, user: User) -> dict:
        exercise = _scope_exercise(self.db, exercise_id, user)
        if exercise.status != "em_andamento" or not exercise.scenario_id:
            raise HTTPException(status_code=409, detail="Exercício não pode ser concluído neste estado.")
        self._enforce_agent_budget(exercise.id, 1)
        events = list(self.db.scalars(select(InjectEvent).where(
            InjectEvent.exercise_id == exercise.id
        ).order_by(InjectEvent.sequence)))
        decisions = list(self.db.scalars(select(Decision).where(Decision.exercise_id == exercise.id)))
        company = self.db.get(Company, exercise.company_id)
        scenario = self.db.get(Scenario, exercise.scenario_id)
        participants = list(self.db.scalars(select(Participant).where(Participant.exercise_id == exercise.id)))
        objectives = list(self.db.scalars(select(ExerciseObjective).where(
            ExerciseObjective.exercise_id == exercise.id
        ).order_by(ExerciseObjective.created_at)))
        assessments = list(self.db.scalars(select(ObjectiveAssessment).where(
            ObjectiveAssessment.exercise_id == exercise.id
        )))
        assessed_scores = {item.objective_id: item.score for item in assessments}
        prior = self.orchestrator.get_state(exercise.id) or {}
        state: ExerciseState = {
            **prior,
            "action": "complete",
            "exercise_id": exercise.id,
            "events": [
                {"id": row.id, "title": row.title, "description": row.description, "sequence": row.sequence}
                for row in events
            ],
            "decisions": [
                {"id": row.id, "description": row.description, "rationale": row.rationale}
                for row in decisions
            ],
        }
        try:
            result = self.orchestrator.complete(state)
            report = ConsolidatedReport.model_validate(result["report"])
            exercise.status = "concluido"
            exercise.completed_at = datetime.now(UTC)
            if exercise.started_at:
                started_at = exercise.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=UTC)
                exercise.actual_duration = max(0, int(
                    (exercise.completed_at - started_at).total_seconds() // 60
                ))
            report = report.model_copy(update={
                "exercise_id": exercise.id,
                "company_name": company.name if company else "Empresa não disponível",
                "exercise_date": exercise.started_at.isoformat() if exercise.started_at else None,
                "scenario_name": scenario.name if scenario else "Cenário não disponível",
                "participants": [
                    f"{participant.profile} — {participant.department}"
                    if participant.department else participant.profile
                    for participant in participants
                ],
                "objectives": [item.objective_name for item in objectives],
                "objectives_achieved": [
                    item.objective_name for item in objectives if assessed_scores.get(item.id) == 4
                ],
                "objectives_not_assessed": [
                    item.objective_name for item in objectives if item.id not in assessed_scores
                ],
                "nist_mapping": sorted({
                    item.nist_category for item in objectives if item.nist_category
                }) or report.nist_mapping,
            })
            findings_by_description = {}
            for item in report.findings:
                finding = Finding(
                    company_id=exercise.company_id, exercise_id=exercise.id,
                    category="Lição aprendida", description=item,
                    evidence=report.evidence_ids, priority="Média",
                )
                self.db.add(finding)
                findings_by_description[item] = finding
            self.db.flush()
            for action in report.action_plan:
                due_date = datetime.now(UTC).date()
                if action.proposed_due_days is not None:
                    from datetime import timedelta
                    due_date += timedelta(days=action.proposed_due_days)
                from app.db.models import ActionItem
                self.db.add(ActionItem(
                    company_id=exercise.company_id, exercise_id=exercise.id,
                    finding_id=(
                        findings_by_description[action.related_problem].id
                        if action.related_problem in findings_by_description else None
                    ),
                    description=action.description, priority=action.priority,
                    responsible_role=action.responsible_role, due_date=due_date,
                    status=action.status, completion_indicator="Validação documentada pelo responsável.",
                ))
            self.db.add(AgentRun(
                company_id=exercise.company_id, exercise_id=exercise.id,
                agent_name="consolidator", agent_role="Consolidador de inteligência",
                status="sucesso", result=report.model_dump(mode="json"),
                latency_ms=result.get("agent_latencies", {}).get("consolidator", 0), validated=True,
                tokens_used=result.get("agent_tokens", {}).get("consolidator"),
            ))
            _audit(self.db, user, "exercise.completed", "exercise", exercise.id, exercise.company_id)
            self.db.commit()
            return report.model_dump(mode="json")
        except Exception as exc:
            self.db.rollback()
            self.db.add(AgentRun(
                company_id=exercise.company_id, exercise_id=exercise.id,
                agent_name="consolidator", agent_role="Consolidador de inteligência",
                status="falha", error_message=f"Falha de execução ({type(exc).__name__}).",
                validated=False,
            ))
            self.db.commit()
            logger.error("Falha ao consolidar exercício %s (%s).", exercise.id, type(exc).__name__)
            raise HTTPException(status_code=502, detail="A consolidação falhou; verifique os resultados do provedor.") from exc

    def get_report(self, exercise_id: str, user: User) -> dict:
        exercise = _scope_exercise(self.db, exercise_id, user)
        report_run = self.db.scalar(
            select(AgentRun).where(
                AgentRun.exercise_id == exercise.id, AgentRun.agent_name == "consolidator"
            ).order_by(AgentRun.created_at.desc())
        )
        if report_run:
            return report_run.result
        prior = self.orchestrator.get_state(exercise.id) or {}
        if exercise.status != "concluido" or not prior.get("report"):
            raise HTTPException(status_code=409, detail="O relatório estará disponível após a consolidação.")
        return prior["report"]

    def _inject_total(self, scenario_id: str) -> int:
        return self.db.scalar(select(func.count(ScenarioInject.id)).where(
            ScenarioInject.scenario_id == scenario_id
        )) or 0
