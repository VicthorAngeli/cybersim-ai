from app.agents.base_agent import BaseAgent
from app.schemas.agents import SocAnalysis


class SocAnalystAgent(BaseAgent):
    prompt_file = "soc.md"
    output_schema = SocAnalysis
    role = "Analista SOC defensivo"
