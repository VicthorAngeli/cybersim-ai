from app.agents.base_agent import BaseAgent
from app.schemas.agents import ConsolidatedReport


class IntelligenceConsolidatorAgent(BaseAgent):
    prompt_file = "consolidator.md"
    output_schema = ConsolidatedReport
    role = "Consolidador de inteligência e lições aprendidas"
