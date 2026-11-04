from functools import lru_cache

from app.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator


@lru_cache
def get_orchestrator() -> MultiAgentOrchestrator:
    return MultiAgentOrchestrator()
