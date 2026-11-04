from app.agents.base_agent import BaseAgent
from app.schemas.agents import LegalAnalysis


class LegalAnalystAgent(BaseAgent):
    prompt_file = "legal_lgpd.md"
    output_schema = LegalAnalysis
    role = "Analista indicativo de privacidade e LGPD"
