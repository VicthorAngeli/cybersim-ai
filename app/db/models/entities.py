import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (CheckConstraint("employee_count > 0", name="ck_company_employee_count"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    segment: Mapped[str] = mapped_column(String(120), nullable=False)
    size: Mapped[str] = mapped_column(String(40), nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120))
    critical_systems: Mapped[list[str]] = mapped_column(JSON, default=list)
    suppliers: Mapped[list[str]] = mapped_column(JSON, default=list)
    data_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    essential_processes: Mapped[list[str]] = mapped_column(JSON, default=list)
    security_maturity: Mapped[str] = mapped_column(String(40), default="Inicial")
    demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="company")
    exercises: Mapped[list["Exercise"]] = relationship(back_populates="company")


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_company_email", "company_id", "email", unique=True),
        CheckConstraint("role IN ('admin', 'facilitator', 'participant', 'viewer')", name="ck_user_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="facilitator")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    company: Mapped[Company | None] = relationship(back_populates="users")


class Participant(TimestampMixin, Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    profile: Mapped[str] = mapped_column(String(40), default="participante")
    department: Mapped[str | None] = mapped_column(String(120))
    display_name: Mapped[str | None] = mapped_column(String(120))


class Scenario(TimestampMixin, Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), default="Segurança cibernética")
    difficulty: Mapped[str] = mapped_column(String(30), default="Intermediário")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, default="")
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    learning_objectives: Mapped[list[str]] = mapped_column(JSON, default=list)
    timeline: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    facilitator_notes: Mapped[str] = mapped_column(Text, default="")
    demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ScenarioInject(TimestampMixin, Base):
    __tablename__ = "scenario_injects"
    __table_args__ = (UniqueConstraint("scenario_id", "sequence", name="uq_scenario_inject_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    facilitator_notes: Mapped[str] = mapped_column(Text, default="")
    involves_personal_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    involves_outage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_communication: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Exercise(TimestampMixin, Base):
    __tablename__ = "exercises"
    __table_args__ = (
        Index("ix_exercises_company_status", "company_id", "status"),
        CheckConstraint("status IN ('planejado', 'em_andamento', 'concluido')", name="ck_exercise_status"),
        CheckConstraint("planned_duration BETWEEN 30 AND 120", name="ck_exercise_duration"),
        CheckConstraint("participant_count > 0", name="ck_exercise_participant_count"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    incident_type: Mapped[str] = mapped_column(
        String(80), nullable=False, default="exposicao_acidental", server_default="exposicao_acidental"
    )
    status: Mapped[str] = mapped_column(String(30), default="planejado", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(30), default="Intermediário")
    planned_duration: Mapped[int] = mapped_column(Integer, default=60)
    actual_duration: Mapped[int | None] = mapped_column(Integer)
    participant_count: Mapped[int] = mapped_column(Integer, default=1)
    objectives: Mapped[list[str]] = mapped_column(JSON, default=list)
    areas: Mapped[list[str]] = mapped_column(JSON, default=list)
    affected_systems: Mapped[list[str]] = mapped_column(JSON, default=list)
    data_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    company: Mapped[Company] = relationship(back_populates="exercises")


class ExerciseObjective(TimestampMixin, Base):
    __tablename__ = "exercise_objectives"
    __table_args__ = (UniqueConstraint("exercise_id", "objective_name", name="uq_exercise_objective_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    objective_name: Mapped[str] = mapped_column(String(180), nullable=False)
    nist_category: Mapped[str | None] = mapped_column(String(120))


class InjectEvent(TimestampMixin, Base):
    __tablename__ = "inject_events"
    __table_args__ = (UniqueConstraint("exercise_id", "sequence", name="uq_exercise_inject_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    scenario_inject_id: Mapped[str] = mapped_column(ForeignKey("scenario_injects.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), default="Médio")
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Decision(TimestampMixin, Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    inject_event_id: Mapped[str | None] = mapped_column(ForeignKey("inject_events.id", ondelete="SET NULL"), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    responsible_role: Mapped[str | None] = mapped_column(String(120))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint("status IN ('sucesso', 'falha', 'erro', 'pendente')", name="ck_agent_run_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    agent_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    agent_role: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Finding(TimestampMixin, Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(String(30), default="Média")


class ActionItem(TimestampMixin, Base):
    __tablename__ = "action_items"
    __table_args__ = (
        CheckConstraint("status IN ('pendente', 'em_andamento', 'concluida', 'cancelada')", name="ck_action_item_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    finding_id: Mapped[str | None] = mapped_column(ForeignKey("findings.id", ondelete="SET NULL"), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(30), default="Média")
    responsible_role: Mapped[str | None] = mapped_column(String(120))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    completion_indicator: Mapped[str | None] = mapped_column(Text)


class CommunicationDraft(TimestampMixin, Base):
    __tablename__ = "communication_drafts"
    __table_args__ = (
        CheckConstraint("approval_status IN ('rascunho', 'aprovado', 'rejeitado')", name="ck_communication_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    audience: Mapped[str] = mapped_column(String(80), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_information: Mapped[list[str]] = mapped_column(JSON, default=list)
    pending_information: Mapped[list[str]] = mapped_column(JSON, default=list)
    communication_risk: Mapped[str] = mapped_column(Text, default="")
    approval_status: Mapped[str] = mapped_column(String(30), default="rascunho")


class ObjectiveAssessment(TimestampMixin, Base):
    __tablename__ = "objective_assessments"
    __table_args__ = (
        UniqueConstraint("exercise_id", "objective_id", name="uq_assessment_exercise_objective"),
        CheckConstraint("score BETWEEN 0 AND 4", name="ck_assessment_score"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    objective_id: Mapped[str] = mapped_column(ForeignKey("exercise_objectives.id", ondelete="CASCADE"), index=True)
    score: Mapped[int | None] = mapped_column(Integer)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    assessed_by: Mapped[str] = mapped_column(String(40), default="facilitador")


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class RegulatoryReference(TimestampMixin, Base):
    __tablename__ = "regulatory_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    reference: Mapped[str] = mapped_column(String(220), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str] = mapped_column(Text, default="")


class BusinessCalendar(TimestampMixin, Base):
    __tablename__ = "business_calendar"
    __table_args__ = (UniqueConstraint("company_id", "holiday_date", name="uq_company_holiday_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(180), nullable=False)
