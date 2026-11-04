"""LangGraph unit tests."""

from uuid import uuid4

import pytest

from app.llm.mock_provider import MockLLMProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider
from app.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator


def test_langgraph_routes_agents_and_recovers_checkpoint():
    exercise_id = str(uuid4())
    orchestrator = MultiAgentOrchestrator(MockLLMProvider())
    try:
        initial = {
            "exercise_id": exercise_id,
            "company": {"name": "Empresa de teste", "segment": "Treinamento",
                        "critical_systems": ["sistema fictício"], "data_categories": ["dados de clientes"]},
            "scenario_input": {
                "company": {"name": "Empresa de teste", "segment": "Treinamento",
                            "critical_systems": ["sistema fictício"], "data_categories": ["dados de clientes"]},
                "incident_type": "exposicao_acidental", "difficulty": "Intermediário",
            },
            "events": [], "decisions": [], "agent_results": {},
        }
        prepared = orchestrator.generate_scenario(initial)
        assert len(prepared["scenario"]["injects"]) == 5
        assert prepared["status"] == "scenario_ready"

        inject = prepared["scenario"]["injects"][2]
        result = orchestrator.run_inject(
            {
                **prepared,
                "exercise_id": exercise_id,
                "company": initial["company"],
                "scenario": prepared["scenario"],
                "current_inject": inject,
                "events": [],
                "action": "run_inject",
            },
            approved_by="facilitator-test",
        )
        assert set(result["agent_results"]) >= {"soc", "legal"}
        assert "communications" not in result["agent_results"]
        assert result["approval"]["approved"] is True
        assert len(orchestrator.get_state(exercise_id)["events"]) == 1

        resumed = orchestrator.get_state(exercise_id)
        next_inject = prepared["scenario"]["injects"][3]
        result = orchestrator.run_inject(
            {**resumed, "current_inject": next_inject, "action": "run_inject"},
            approved_by="facilitator-test",
        )
        assert set(result["agent_results"]) >= {"soc", "legal", "communications"}
        consolidated = orchestrator.complete({**result, "action": "complete"})
        assert consolidated["status"] == "completed"
        assert consolidated["report"]["human_review_required"] is True
    finally:
        orchestrator.close()


def test_mock_outputs_are_schema_valid_and_personal_data_routing_is_explicit():
    output = MockLLMProvider().generate_structured(
        prompt="instruction",
        user_data={"inject": {"title": "alerta fictício", "description": "dados"}, "involves_personal_data": True},
        output_schema=__import__("app.schemas.agents", fromlist=["LegalAnalysis"]).LegalAnalysis,
    )
    assert output.personal_data_potentially_affected
    assert output.human_review_required
    assert "três dias úteis" in output.indicative_deadline.casefold()
    assert "não constitui parecer" in output.disclaimer


def test_openai_provider_fails_explicitly_without_key():
    provider = OpenAICompatibleProvider()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        provider.generate_structured(
            prompt="prompt",
            user_data={},
            output_schema=__import__("app.schemas.agents", fromlist=["ScenarioOutput"]).ScenarioOutput,
        )
