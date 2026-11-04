from app.agents.base_agent import BaseAgent
from app.schemas.agents import CommunicationOutput


class CrisisCommunicationsAgent(BaseAgent):
    prompt_file = "communications.md"
    output_schema = CommunicationOutput
    role = "Comunicações de crise; somente rascunhos"
