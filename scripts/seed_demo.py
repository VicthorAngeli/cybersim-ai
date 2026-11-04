import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import (
    ActionItem,
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
    RegulatoryReference,
    Scenario,
    ScenarioInject,
    User,
)
from app.db.session import SessionLocal, engine
from app.services.scenario_catalog import get_demo_scenario
from app.services.assessment import ASSESSMENT_CRITERIA

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DEMO_COMPANY = {
    "name": "Horizonte Digital Ltda.",
    "segment": "Comércio eletrônico",
    "size": "Médio",
    "employee_count": 120,
    "location": "Brasil (fictício)",
    "critical_systems": ["CRM", "ERP", "e-mail corporativo", "plataforma de e-commerce"],
    "suppliers": ["provedor de nuvem fictício", "parceiro logístico fictício"],
    "data_categories": ["dados cadastrais de clientes", "histórico de pedidos"],
    "essential_processes": ["vendas digitais", "atendimento ao cliente", "processamento de pedidos"],
    "security_maturity": "Em desenvolvimento",
    "demo_data": True,
}

CATALOG = [
    ("comprometimento_conta", "Comprometimento fictício de conta corporativa"),
    ("indisponibilidade_sistema", "Indisponibilidade de sistema crítico"),
    ("exposicao_acidental", "Exposição acidental de dados pessoais"),
    ("fornecedor_terceirizado", "Incidente envolvendo fornecedor terceirizado"),
    ("nuvem_indisponivel", "Indisponibilidade de serviço em nuvem"),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    with SessionLocal() as db:
        company = db.scalar(select(Company).where(Company.name == DEMO_COMPANY["name"]))
        if not company:
            company = Company(**DEMO_COMPANY)
            db.add(company)
            db.flush()

        for incident_type, _label in CATALOG:
            exists = db.scalar(select(Scenario.id).where(
                Scenario.company_id.is_(None), Scenario.incident_type == incident_type
            ))
            if exists:
                continue
            output = get_demo_scenario(DEMO_COMPANY, incident_type, "Intermediário")
            scenario = Scenario(
                company_id=None, name=output.name, incident_type=incident_type,
                category="Biblioteca demonstrativa", difficulty=output.difficulty,
                description=output.executive_summary, executive_summary=output.executive_summary,
                context=output.context, learning_objectives=output.learning_objectives,
                timeline=output.timeline,
                facilitator_notes=output.facilitator_notes, demo_data=True,
            )
            db.add(scenario)
            db.flush()
            for item in output.injects:
                db.add(ScenarioInject(
                    scenario_id=scenario.id, sequence=item.sequence, title=item.title,
                    description=item.description, questions=item.questions,
                    facilitator_notes=item.facilitator_notes,
                    involves_personal_data=item.involves_personal_data,
                    involves_outage=item.involves_outage,
                    requires_communication=item.requires_communication,
                ))

        admin = db.scalar(select(User).where(User.email == settings.admin_email.casefold()))
        if not admin and settings.admin_password:
            admin = User(
                email=settings.admin_email.casefold(),
                password_hash=hash_password(settings.admin_password),
                role="admin",
            )
            db.add(admin)
        elif not admin:
            logging.warning("ADMIN_PASSWORD não definida; nenhum usuário administrador foi criado.")

        report_exercise = db.scalar(select(Exercise).where(
            Exercise.company_id == company.id, Exercise.title == "Simulação demonstrativa — exposição e indisponibilidade"
        ))
        if report_exercise:
            logging.info("Dados demonstrativos já existem; nenhuma duplicação foi criada.")
            db.commit()
            return

        demo_scenario = get_demo_scenario(DEMO_COMPANY, "exposicao_acidental", "Intermediário")
        scenario = Scenario(
            company_id=company.id, name=demo_scenario.name,
            incident_type=demo_scenario.incident_type, category="Exposição e disponibilidade",
            difficulty=demo_scenario.difficulty, description=demo_scenario.executive_summary,
            executive_summary=demo_scenario.executive_summary, context=demo_scenario.context,
            learning_objectives=demo_scenario.learning_objectives,
            timeline=demo_scenario.timeline,
            facilitator_notes=demo_scenario.facilitator_notes, demo_data=True,
        )
        db.add(scenario)
        db.flush()
        inject_rows = []
        for item in demo_scenario.injects:
            inject = ScenarioInject(
                scenario_id=scenario.id, sequence=item.sequence, title=item.title,
                description=item.description, questions=item.questions,
                facilitator_notes=item.facilitator_notes,
                involves_personal_data=item.involves_personal_data,
                involves_outage=item.involves_outage,
                requires_communication=item.requires_communication,
            )
            db.add(inject)
            inject_rows.append(inject)
        db.flush()

        now = datetime.now(UTC)
        started = now - timedelta(minutes=58)
        exercise = Exercise(
            company_id=company.id, scenario_id=scenario.id,
            title="Simulação demonstrativa — exposição e indisponibilidade",
            status="concluido", difficulty="Intermediário", planned_duration=60,
            actual_duration=52, participant_count=4,
            objectives=demo_scenario.learning_objectives,
            areas=["TI", "Segurança", "Privacidade", "Comunicação"],
            affected_systems=DEMO_COMPANY["critical_systems"],
            data_categories=DEMO_COMPANY["data_categories"],
            started_at=started, completed_at=now - timedelta(minutes=6),
        )
        db.add(exercise)
        db.flush()
        objective_rows = []
        objective_names = list(dict.fromkeys([
            *demo_scenario.learning_objectives, *(name for name, _ in ASSESSMENT_CRITERIA)
        ]))
        objective_categories = dict(ASSESSMENT_CRITERIA)
        for index, name in enumerate(objective_names):
            objective = ExerciseObjective(
                company_id=company.id, exercise_id=exercise.id,
                objective_name=name,
                nist_category=objective_categories.get(name, ["Respond", "Govern", "Recover", "Identify"][index % 4]),
            )
            db.add(objective)
            objective_rows.append(objective)
        for profile, department in [
            ("facilitator", "Segurança da informação"),
            ("participant", "Tecnologia"),
            ("participant", "Privacidade"),
            ("participant", "Comunicação"),
        ]:
            db.add(Participant(
                company_id=company.id, exercise_id=exercise.id,
                profile=profile, department=department, display_name=None,
            ))
        db.flush()

        events = []
        decisions = []
        for index, inject in enumerate(inject_rows):
            released_at = started + timedelta(minutes=index * 10)
            event = InjectEvent(
                company_id=company.id, exercise_id=exercise.id, scenario_inject_id=inject.id,
                sequence=inject.sequence, title=inject.title, description=inject.description,
                severity="Alto" if inject.involves_personal_data else "Médio",
                released_at=released_at,
            )
            db.add(event)
            events.append(event)
        db.flush()
        decision_texts = [
            "Acionar responsáveis por tecnologia e iniciar registro cronológico.",
            "Confirmar áreas afetadas e avaliar continuidade dos processos essenciais.",
            "Solicitar avaliação de privacidade sem tratar a hipótese como fato confirmado.",
            "Centralizar respostas externas em canal previamente autorizado.",
            "Definir prioridades de recuperação e registrar responsáveis por função.",
        ]
        for event, description in zip(events, decision_texts):
            decision = Decision(
                company_id=company.id, exercise_id=exercise.id, inject_event_id=event.id,
                description=description,
                rationale="Decisão registrada durante o exercício demonstrativo fictício.",
                responsible_role="Liderança da área responsável",
                decided_at=event.released_at + timedelta(minutes=4),
            )
            db.add(decision)
            decisions.append(decision)
        db.flush()

        for index, event in enumerate(events):
            db.add(AgentRun(
                company_id=company.id, exercise_id=exercise.id,
                agent_name="soc", agent_role="Analista SOC defensivo",
                status="sucesso", validated=True, latency_ms=180 + index * 35,
                result={
                    "severity": "Alto" if index == 2 else "Médio",
                    "incident_classification": "Incidente fictício em avaliação",
                    "unknowns": ["Escopo ainda não confirmado"],
                    "defensive_recommendations": ["Acionar responsáveis e preservar registros do exercício"],
                    "confirmed_facts": [event.description],
                    "hypotheses": ["Causa e extensão ainda precisam ser avaliadas."],
                },
                started_at=event.released_at, finished_at=event.released_at + timedelta(seconds=1),
            ))
        db.add(AgentRun(
            company_id=company.id, exercise_id=exercise.id, agent_name="narrator",
            agent_role="Narrador / Simulador", status="sucesso", validated=True,
            latency_ms=90, result=demo_scenario.model_dump(mode="json"),
        ))
        db.add(AgentRun(
            company_id=company.id, exercise_id=exercise.id, agent_name="legal",
            agent_role="Analista indicativo de privacidade e LGPD", status="sucesso",
            validated=True, latency_ms=210,
            result={
                "legal_assessment_pending": True, "possible_anpd_communication": "Avaliar caso a caso com revisão humana.",
                "data_categories": DEMO_COMPANY["data_categories"],
                "disclaimer": "Triagem fictícia, não é parecer jurídico.",
            },
        ))
        db.add(AgentRun(
            company_id=company.id, exercise_id=exercise.id, agent_name="communications",
            agent_role="Comunicações de crise; somente rascunhos", status="sucesso",
            validated=True, latency_ms=160,
            result={"approval_status": "rascunho", "audience": "Clientes"},
        ))
        db.add(AgentRun(
            company_id=company.id, exercise_id=exercise.id, agent_name="consolidator",
            agent_role="Consolidador de inteligência", status="sucesso",
            validated=True, latency_ms=230,
            result={"executive_summary": "Consolidação demonstrativa baseada em decisões registradas.",
                    "timeline": [event.title for event in events]},
        ))

        findings = []
        for category, description, priority in [
            ("Escalonamento", "Clarificar o ponto de contato e os critérios de escalonamento.", "Alta"),
            ("Continuidade", "Documentar dependências e alternativas para processos essenciais.", "Média"),
            ("Privacidade", "Validar papéis e fluxo de avaliação com o encarregado.", "Alta"),
            ("Comunicação", "Definir processo de aprovação de comunicados externos.", "Média"),
        ]:
            finding = Finding(
                company_id=company.id, exercise_id=exercise.id, category=category,
                description=description, evidence=[events[0].id, decisions[0].id],
                priority=priority,
            )
            db.add(finding)
            findings.append(finding)
        db.flush()
        action_statuses = ["pendente", "em_andamento", "concluida", "pendente"]
        for index, finding in enumerate(findings):
            db.add(ActionItem(
                company_id=company.id, exercise_id=exercise.id, finding_id=finding.id,
                description=f"Ação demonstrativa: {finding.description}",
                priority=finding.priority, responsible_role=["Segurança", "TI", "DPO", "Comunicação"][index],
                due_date=(date.today() + timedelta(days=[-2, 14, -5, 30][index])),
                status=action_statuses[index],
                completion_indicator="Evidência de conclusão revisada pelo responsável.",
            ))
        db.add(CommunicationDraft(
            company_id=company.id, exercise_id=exercise.id, audience="Clientes",
            objective="Compartilhar atualizações validadas sobre o exercício fictício.",
            context="Rascunho demonstrativo; nenhum envio é realizado.",
            message="Estamos avaliando uma situação fictícia do exercício e compartilharemos informações após validação.",
            confirmed_information=["A ocorrência faz parte de treinamento simulado."],
            pending_information=["Nenhum fato de produção está envolvido."],
            communication_risk="Não reutilizar como comunicação real.",
            approval_status="rascunho",
        ))
        db.add(CommunicationDraft(
            company_id=company.id, exercise_id=exercise.id, audience="Diretoria",
            objective="Resumo para tomada de decisão no exercício.",
            context="Treinamento tabletop fictício.",
            message="O exercício foi concluído e os próximos passos estão registrados no plano de melhoria.",
            confirmed_information=["Exercício de treinamento concluído."],
            pending_information=[],
            communication_risk="Validar conteúdo e contexto antes de qualquer reutilização.",
            approval_status="aprovado",
        ))
        for index, objective in enumerate(objective_rows):
            db.add(ObjectiveAssessment(
                company_id=company.id, exercise_id=exercise.id, objective_id=objective.id,
                score=index % 5,
                evidence=[decisions[index % len(decisions)].id],
                assessed_by="facilitador",
            ))
        for title, reference, url in [
            ("Lei Geral de Proteção de Dados Pessoais", "Lei nº 13.709/2018", "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"),
            ("Comunicação de incidente de segurança", "Resolução CD/ANPD nº 15/2024", "https://www.gov.br/anpd/pt-br"),
            ("Cybersecurity Framework 2.0", "NIST CSF 2.0", "https://www.nist.gov/cyberframework"),
        ]:
            if not db.scalar(select(RegulatoryReference.id).where(RegulatoryReference.reference == reference)):
                db.add(RegulatoryReference(title=title, reference=reference, url=url))
        db.add(AuditLog(
            company_id=company.id, action="demo.seeded", resource_type="exercise",
            resource_id=exercise.id, details={"simulated_data": True},
        ))
        db.commit()
        logging.info("Dados fictícios criados. Empresa: %s. Exercício concluído: %s.", company.id, exercise.id)
        if not settings.admin_password:
            logging.info("Defina ADMIN_PASSWORD no arquivo .env e execute novamente para criar o administrador.")


if __name__ == "__main__":
    main()
