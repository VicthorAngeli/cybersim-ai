import json
from typing import TypeVar

from pydantic import BaseModel

from app.llm.base_provider import LLMProvider
from app.schemas.agents import (
    CommunicationOutput,
    ConsolidatedReport,
    LegalAnalysis,
    ScenarioOutput,
    SocAnalysis,
)
from app.services.scenario_catalog import get_demo_scenario

OutputT = TypeVar("OutputT", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Deterministic, local-only responses using the same Pydantic contracts as live models."""

    def generate_structured(
        self, *, prompt: str, user_data: dict, output_schema: type[OutputT]
    ) -> OutputT:
        del prompt
        if output_schema is ScenarioOutput:
            response = get_demo_scenario(
                user_data.get("company", {}),
                user_data.get("incident_type", "exposicao_acidental"),
                user_data.get("difficulty", "Intermediário"),
            )
        elif output_schema is SocAnalysis:
            inject = user_data.get("inject", {})
            text = f"{inject.get('title', '')} {inject.get('description', '')}".casefold()
            response = SocAnalysis(
                incident_classification="Indisponibilidade e possível exposição de dados" if "expos" in text else "Incidente cibernético em avaliação",
                severity="Alto" if inject.get("involves_personal_data") else "Médio",
                justification="Classificação inicial baseada somente no inject fictício; confirmar fatos e escopo antes de qualquer decisão.",
                operational_impact="Pode afetar processos que dependem do serviço citado; o impacto real não foi medido neste exercício.",
                confidentiality_impact="Possível impacto a investigar; não há confirmação de acesso indevido.",
                integrity_impact="Não há evidência suficiente para afirmar alteração de dados.",
                availability_impact="Inject relata indisponibilidade hipotética; duração e abrangência permanecem desconhecidas.",
                affected_assets=user_data.get("affected_assets", []),
                confirmed_facts=[inject.get("description", "Acontecimento simulado registrado no exercício.")],
                hypotheses=["A indisponibilidade pode estar relacionada ao acontecimento descrito; hipótese não confirmada."],
                unknowns=["Extensão do impacto", "Causa raiz", "Integridade dos registros", "Escopo de dados potencialmente afetados"],
                investigation_questions=["Quais sistemas e áreas foram afetados?", "Que registros verificáveis sustentam a avaliação?"],
                defensive_recommendations=["Acionar responsáveis internos e seguir o plano de resposta aprovado.", "Preservar registros relevantes conforme política interna.", "Avaliar continuidade por canais autorizados."],
                evidence_preservation=["Registrar horário, fonte e contexto das evidências fictícias apresentadas."],
                continuity_and_recovery=["Priorizar serviços essenciais conforme plano de continuidade e critérios documentados."],
                escalation_roles=["Liderança de TI", "Segurança da informação", "Continuidade de negócios"],
                confidence=0.72,
            )
        elif output_schema is LegalAnalysis:
            response = LegalAnalysis(
                personal_data_potentially_affected=bool(user_data.get("involves_personal_data", True)),
                data_categories=user_data.get("data_categories", ["dados de clientes"]),
                sensitive_data_potentially_affected=False,
                children_data_potentially_affected=False,
                company_role="A determinar conforme os papéis efetivamente exercidos no tratamento.",
                potential_impacts=["Possível risco a titulares; natureza, extensão e consequências não confirmadas."],
                dpo_review_required=True,
                possible_anpd_communication="Avaliar caso a caso com o controlador e o encarregado; não é uma conclusão automática.",
                possible_data_subject_communication="Avaliar após análise de risco/dano relevante e confirmação dos fatos aplicáveis.",
                legal_assessment_pending=True,
                indicative_deadline="Três dias úteis nas hipóteses aplicáveis; marco inicial e incidência devem ser validados pelo controlador e assessoria jurídica.",
                human_review_required=True,
                disclaimer="Triagem educacional baseada em cenário fictício; não constitui parecer jurídico.",
            )
        elif output_schema is CommunicationOutput:
            response = CommunicationOutput(
                audience=user_data.get("audience", "Diretoria"),
                objective="Compartilhar apenas informações confirmadas e decisões solicitadas.",
                context="Rascunho para exercício fictício; validar fatos, público e canal antes de qualquer uso.",
                proposed_message="A organização identificou uma situação em avaliação e está coordenando as áreas responsáveis. Novas informações serão compartilhadas após validação.",
                confirmed_information=user_data.get("confirmed_information", []),
                pending_information=user_data.get("pending_information", ["Escopo, impacto e causa permanecem em avaliação."]),
                communication_risk="Evitar divulgar dados pessoais, hipóteses como fatos ou prazos não confirmados.",
            )
        elif output_schema is ConsolidatedReport:
            decisions = user_data.get("decisions", [])
            events = user_data.get("events", [])
            evidence_ids = [
                str(item.get("id"))
                for item in [*events, *decisions]
                if item.get("id")
            ]
            follow_up = "Validar responsabilidades, prazos e evidências no pós-exercício."
            response = ConsolidatedReport(
                executive_summary="Relatório de exercício fictício consolidado exclusivamente a partir dos registros fornecidos.",
                timeline=[event.get("title", "Evento do exercício") for event in events],
                decisions=[decision.get("description", "") for decision in decisions],
                strengths=[f"Foram registradas {len(decisions)} decisões para revisão."] if decisions else [],
                improvement_areas=["A equipe deve validar responsabilidades, evidências e critérios de escalonamento com base nas decisões observadas."],
                recommendations=["Revisar o plano de resposta e continuidade com as equipes responsáveis."],
                findings=[follow_up] if events else [],
                action_plan=[{
                    "description": "Revisar o plano de resposta e registrar os próximos passos acordados.",
                    "related_problem": follow_up,
                    "recommendation": "Revisar o plano com as funções envolvidas e documentar responsáveis, prazos e evidências.",
                    "priority": "Média",
                    "responsible_role": "Liderança de segurança da informação",
                    "proposed_due_days": 30,
                    "status": "pendente",
                    "evidence_ids": evidence_ids,
                }] if events else [],
                objectives_not_assessed=user_data.get("objectives", []),
                nist_mapping=["NIST CSF 2.0: Govern, Identify, Protect, Detect, Respond, Recover", "NIST SP 800-61 Rev. 3"],
                evidence_ids=evidence_ids,
            )
        else:
            raise ValueError(f"Schema sem resposta MOCK cadastrada: {output_schema.__name__}")
        return output_schema.model_validate_json(response.model_dump_json())  # type: ignore[return-value]

    @staticmethod
    def safe_input(data: dict) -> str:
        """Serialize user-controlled data as data, not as instructions."""
        return json.dumps(data, ensure_ascii=False, default=str)
