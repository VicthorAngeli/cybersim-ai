from app.agents.base_agent import BaseAgent
from app.schemas.agents import ScenarioOutput


class NarratorAgent(BaseAgent):
    prompt_file = "narrator.md"
    output_schema = ScenarioOutput
    role = "Narrador e simulador de incidentes fictícios"
