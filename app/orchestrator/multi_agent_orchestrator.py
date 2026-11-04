import logging
import time
from contextlib import AbstractContextManager
from typing import Any, cast

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agents.communications_agent import CrisisCommunicationsAgent
from app.agents.consolidator_agent import IntelligenceConsolidatorAgent
from app.agents.legal_agent import LegalAnalystAgent
from app.agents.narrator_agent import NarratorAgent
from app.agents.soc_agent import SocAnalystAgent
from app.core.config import get_settings
from app.llm.base_provider import LLMProvider
from app.llm.provider_factory import create_provider
from app.orchestrator.state import ExerciseState

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Runs typed, checkpointed agent workflows; graph nodes have no external tools."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or create_provider()
        self.narrator = NarratorAgent(self.provider)
        self.soc = SocAnalystAgent(self.provider)
        self.legal = LegalAnalystAgent(self.provider)
        self.communications = CrisisCommunicationsAgent(self.provider)
        self.consolidator = IntelligenceConsolidatorAgent(self.provider)
        self._checkpoint_context: AbstractContextManager[Any] | None = None
        checkpointer = self._get_checkpointer()
        self.graph = self._build_graph(checkpointer)

    def _get_checkpointer(self) -> Any:
        database_url = get_settings().database_url
        if not database_url.startswith("postgresql"):
            return MemorySaver()
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as exc:
            raise RuntimeError("PostgreSQL checkpointer indisponível; instale langgraph-checkpoint-postgres.") from exc
        connection_string = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._checkpoint_context = PostgresSaver.from_conn_string(connection_string)
        checkpointer = self._checkpoint_context.__enter__()
        checkpointer.setup()
        return checkpointer

    def close(self) -> None:
        if self._checkpoint_context:
            self._checkpoint_context.__exit__(None, None, None)
            self._checkpoint_context = None

    def _build_graph(self, checkpointer: Any) -> Any:
        builder = StateGraph(ExerciseState)

        def dispatch(state: ExerciseState) -> dict:
            return {}

        def route_action(state: ExerciseState) -> str:
            return state.get("action", "generate")

        def narrator_node(state: ExerciseState) -> dict:
            started = time.perf_counter()
            output = self.narrator.run(state.get("scenario_input", {}))
            latency = int((time.perf_counter() - started) * 1000)
            return {
                "scenario": output.model_dump(mode="json"), "status": "scenario_ready",
                "agent_latencies": {**state.get("agent_latencies", {}), "narrator": latency},
                "agent_tokens": {**state.get("agent_tokens", {}), "narrator": self.provider.last_tokens_used},
            }

        def facilitator_gate(state: ExerciseState) -> dict:
            approval = interrupt({
                "kind": "facilitator_approval",
                "exercise_id": state.get("exercise_id"),
                "inject": state.get("current_inject"),
                "message": "A liberação do acontecimento depende de ação explícita do facilitador.",
            })
            if not isinstance(approval, dict) or approval.get("approved") is not True:
                raise ValueError("Aprovação do facilitador ausente ou inválida.")
            return {"approval": approval, "status": "inject_released"}

        def soc_node(state: ExerciseState) -> dict:
            scenario = state.get("scenario", {})
            company = state.get("company", {})
            started = time.perf_counter()
            result = self.soc.run({
                "inject": state.get("current_inject", {}),
                "affected_assets": scenario.get("affected_assets", company.get("critical_systems", [])),
                "events": state.get("events", []),
            })
            return {
                "agent_results": {**state.get("agent_results", {}), "soc": result.model_dump(mode="json")},
                "agent_latencies": {**state.get("agent_latencies", {}), "soc": int((time.perf_counter() - started) * 1000)},
                "agent_tokens": {**state.get("agent_tokens", {}), "soc": self.provider.last_tokens_used},
            }

        def route_after_soc(state: ExerciseState) -> str:
            inject = state.get("current_inject", {})
            if inject.get("involves_personal_data"):
                return "legal"
            if inject.get("requires_communication") or state.get("communication_requested"):
                return "communications"
            return "record"

        def legal_node(state: ExerciseState) -> dict:
            company = state.get("company", {})
            started = time.perf_counter()
            result = self.legal.run({
                "inject": state.get("current_inject", {}),
                "involves_personal_data": True,
                "data_categories": company.get("data_categories", []),
                "events": state.get("events", []),
            })
            return {
                "agent_results": {**state.get("agent_results", {}), "legal": result.model_dump(mode="json")},
                "agent_latencies": {**state.get("agent_latencies", {}), "legal": int((time.perf_counter() - started) * 1000)},
                "agent_tokens": {**state.get("agent_tokens", {}), "legal": self.provider.last_tokens_used},
            }

        def route_after_legal(state: ExerciseState) -> str:
            inject = state.get("current_inject", {})
            return "communications" if inject.get("requires_communication") or state.get("communication_requested") else "record"

        def communications_node(state: ExerciseState) -> dict:
            agent_results = state.get("agent_results", {})
            soc = agent_results.get("soc", {})
            started = time.perf_counter()
            result = self.communications.run({
                "audience": "Diretoria",
                "confirmed_information": soc.get("confirmed_facts", []),
                "pending_information": soc.get("unknowns", []),
                "inject": state.get("current_inject", {}),
            })
            return {
                "agent_results": {**agent_results, "communications": result.model_dump(mode="json")},
                "agent_latencies": {**state.get("agent_latencies", {}), "communications": int((time.perf_counter() - started) * 1000)},
                "agent_tokens": {**state.get("agent_tokens", {}), "communications": self.provider.last_tokens_used},
            }

        def record_node(state: ExerciseState) -> dict:
            events = list(state.get("events", []))
            current = state.get("current_inject", {})
            events.append({
                "sequence": current.get("sequence"),
                "inject_id": current.get("id"),
                "title": current.get("title"),
                "description": current.get("description"),
                "agent_names": list(state.get("agent_results", {}).keys()),
            })
            return {"events": events, "status": "in_progress"}

        def consolidator_node(state: ExerciseState) -> dict:
            started = time.perf_counter()
            result = self.consolidator.run({
                "scenario": state.get("scenario", {}),
                "events": state.get("events", []),
                "decisions": state.get("decisions", []),
                "agent_results": state.get("agent_results", {}),
                "objectives": state.get("scenario", {}).get("learning_objectives", []),
            })
            return {
                "report": result.model_dump(mode="json"), "status": "completed",
                "agent_latencies": {**state.get("agent_latencies", {}), "consolidator": int((time.perf_counter() - started) * 1000)},
                "agent_tokens": {**state.get("agent_tokens", {}), "consolidator": self.provider.last_tokens_used},
            }

        builder.add_node("dispatch", dispatch)
        builder.add_node("narrator_node", narrator_node)
        builder.add_node("facilitator_gate", facilitator_gate)
        builder.add_node("soc_node", soc_node)
        builder.add_node("legal_node", legal_node)
        builder.add_node("communications_node", communications_node)
        builder.add_node("record_results", record_node)
        builder.add_node("consolidator_node", consolidator_node)
        builder.add_edge(START, "dispatch")
        builder.add_conditional_edges("dispatch", route_action, {
            "generate": "narrator_node",
            "run_inject": "facilitator_gate",
            "complete": "consolidator_node",
        })
        builder.add_edge("narrator_node", END)
        builder.add_edge("facilitator_gate", "soc_node")
        builder.add_conditional_edges("soc_node", route_after_soc, {
            "legal": "legal_node",
            "communications": "communications_node",
            "record": "record_results",
        })
        builder.add_conditional_edges("legal_node", route_after_legal, {
            "communications": "communications_node",
            "record": "record_results",
        })
        builder.add_edge("communications_node", "record_results")
        builder.add_edge("record_results", END)
        builder.add_edge("consolidator_node", END)
        return builder.compile(checkpointer=checkpointer)

    def generate_scenario(self, state: ExerciseState) -> dict:
        return cast(dict, self.graph.invoke({**state, "action": "generate"}, self._config(state)))

    def run_inject(self, state: ExerciseState, *, approved_by: str) -> dict:
        if not approved_by:
            raise ValueError("Aprovação humana obrigatória para liberar inject.")
        config = self._config(state)
        suspended = self.graph.invoke({**state, "action": "run_inject"}, config)
        if not suspended.get("__interrupt__"):
            raise RuntimeError("O grafo não solicitou aprovação do facilitador.")
        return cast(dict, self.graph.invoke(Command(resume={"approved": True, "approved_by": approved_by}), config))

    def complete(self, state: ExerciseState) -> dict:
        return cast(dict, self.graph.invoke({**state, "action": "complete"}, self._config(state)))

    def get_state(self, exercise_id: str) -> dict | None:
        snapshot = self.graph.get_state({"configurable": {"thread_id": exercise_id}})
        return dict(snapshot.values) if snapshot and snapshot.values else None

    @staticmethod
    def _config(state: ExerciseState) -> dict:
        exercise_id = state.get("exercise_id")
        if not exercise_id:
            raise ValueError("exercise_id é obrigatório para persistir o checkpoint.")
        return {"configurable": {"thread_id": exercise_id}}
