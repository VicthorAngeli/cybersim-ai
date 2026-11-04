from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    segment: str = Field(min_length=2, max_length=120)
    size: str
    employee_count: int = Field(gt=0, le=1_000_000)
    location: str | None = None
    critical_systems: list[str] = Field(default_factory=list)
    suppliers: list[str] = Field(default_factory=list)
    data_categories: list[str] = Field(default_factory=list)
    essential_processes: list[str] = Field(default_factory=list)
    security_maturity: str = "Inicial"


class CompanyRead(CompanyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    demo_data: bool
    created_at: datetime


class ExerciseCreate(BaseModel):
    company_id: str
    title: str = Field(min_length=3, max_length=180)
    incident_type: str = Field(
        default="exposicao_acidental",
        pattern="^(comprometimento_conta|indisponibilidade_sistema|exposicao_acidental|fornecedor_terceirizado|nuvem_indisponivel)$",
    )
    difficulty: str = "Intermediário"
    planned_duration: int = Field(default=60, ge=30, le=120)
    participant_count: int = Field(default=1, ge=1, le=500)
    objectives: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    affected_systems: list[str] = Field(default_factory=list)
    data_categories: list[str] = Field(default_factory=list)


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    scenario_id: str | None
    title: str
    incident_type: str
    status: str
    difficulty: str
    planned_duration: int
    participant_count: int
    objectives: list[str]
    started_at: datetime | None
    completed_at: datetime | None


class DecisionCreate(BaseModel):
    inject_event_id: str | None = None
    description: str = Field(min_length=3, max_length=10_000)
    rationale: str | None = Field(default=None, max_length=10_000)
    responsible_role: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InjectReleaseRequest(BaseModel):
    inject_id: str | None = None


class StartExerciseRequest(BaseModel):
    incident_type: str | None = Field(
        default=None,
        pattern="^(comprometimento_conta|indisponibilidade_sistema|exposicao_acidental|fornecedor_terceirizado|nuvem_indisponivel)$",
    )


class AgentRunRequest(BaseModel):
    agent_name: str | None = None


class ActionItemUpdate(BaseModel):
    status: str = Field(pattern="^(pendente|em_andamento|concluida|cancelada)$")


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    role: str = Field(pattern="^(admin|facilitator|participant|viewer)$")
    company_id: str | None = None


class HolidayCreate(BaseModel):
    holiday_date: date
    description: str = Field(min_length=2, max_length=180)
    company_id: str | None = None


class CommunicationApprovalUpdate(BaseModel):
    status: str = Field(pattern="^(aprovado|rejeitado)$")
    rationale: str = Field(min_length=3, max_length=2_000)


class ObjectiveAssessmentCreate(BaseModel):
    objective_id: str
    score: int = Field(ge=0, le=4)
    evidence_ids: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
