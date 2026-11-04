from pydantic import BaseModel, Field


class ScenarioInjectOutput(BaseModel):
    sequence: int = Field(ge=1)
    title: str
    description: str
    questions: list[str] = Field(default_factory=list)
    facilitator_notes: str = ""
    involves_personal_data: bool = False
    involves_outage: bool = False
    requires_communication: bool = False


class ScenarioOutput(BaseModel):
    name: str
    executive_summary: str
    incident_type: str
    context: dict[str, str] = Field(default_factory=dict)
    affected_assets: list[str] = Field(default_factory=list)
    difficulty: str
    learning_objectives: list[str] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)
    injects: list[ScenarioInjectOutput] = Field(min_length=1)
    facilitator_notes: str = ""
    demo_data: bool = True


class SocAnalysis(BaseModel):
    incident_classification: str
    severity: str
    justification: str
    operational_impact: str
    confidentiality_impact: str
    integrity_impact: str
    availability_impact: str
    affected_assets: list[str] = Field(default_factory=list)
    confirmed_facts: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    investigation_questions: list[str] = Field(default_factory=list)
    defensive_recommendations: list[str] = Field(default_factory=list)
    evidence_preservation: list[str] = Field(default_factory=list)
    continuity_and_recovery: list[str] = Field(default_factory=list)
    escalation_roles: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class LegalAnalysis(BaseModel):
    personal_data_potentially_affected: bool
    data_categories: list[str] = Field(default_factory=list)
    sensitive_data_potentially_affected: bool = False
    children_data_potentially_affected: bool = False
    estimated_data_subjects: int | None = Field(default=None, ge=0)
    company_role: str
    potential_impacts: list[str] = Field(default_factory=list)
    dpo_review_required: bool = True
    possible_anpd_communication: str
    possible_data_subject_communication: str
    legal_assessment_pending: bool = True
    indicative_deadline: str | None = None
    deadline_note: str = "Prazo indicativo em dias úteis; exige validação humana e calendário aplicável."
    incident_discovery_time: str | None = None
    controller_awareness_time: str | None = None
    impact_confirmation_time: str | None = None
    legal_review_time: str | None = None
    communication_decision_time: str | None = None
    communication_approved: bool = False
    records_retention_note: str = "Manter registros por pelo menos cinco anos, quando aplicável; validar juridicamente."
    normative_references: list[str] = Field(
        default_factory=lambda: ["LGPD (Lei nº 13.709/2018)", "Resolução CD/ANPD nº 15/2024"]
    )
    human_review_required: bool = True
    disclaimer: str = "Avaliação indicativa; não constitui parecer jurídico."


class CommunicationOutput(BaseModel):
    audience: str
    objective: str
    context: str
    proposed_message: str
    confirmed_information: list[str] = Field(default_factory=list)
    pending_information: list[str] = Field(default_factory=list)
    communication_risk: str
    approval_status: str = "rascunho"
    human_approval_required: bool = True


class ConsolidatedAction(BaseModel):
    description: str
    related_problem: str
    recommendation: str
    priority: str
    responsible_role: str
    proposed_due_days: int | None = Field(default=None, ge=0)
    status: str = "pendente"
    evidence_ids: list[str] = Field(default_factory=list)


class ConsolidatedReport(BaseModel):
    exercise_id: str | None = None
    company_name: str | None = None
    exercise_date: str | None = None
    scenario_name: str | None = None
    scope: str = "Exercício de mesa fictício; não representa auditoria ou certificação."
    participants: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    executive_summary: str
    timeline: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    communication_gaps: list[str] = Field(default_factory=list)
    responsibility_gaps: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    action_plan: list[ConsolidatedAction] = Field(default_factory=list)
    objectives_achieved: list[str] = Field(default_factory=list)
    objectives_not_assessed: list[str] = Field(default_factory=list)
    nist_mapping: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    human_review_required: bool = True
