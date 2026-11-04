from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.llm.base_provider import LLMProvider

OutputT = TypeVar("OutputT", bound=BaseModel)
PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


class BaseAgent:
    prompt_file: str
    output_schema: type[BaseModel]
    role: str

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def run(self, user_data: dict) -> BaseModel:
        prompt = (PROMPT_DIR / self.prompt_file).read_text(encoding="utf-8")
        return self.provider.generate_structured(
            prompt=prompt,
            user_data=user_data,
            output_schema=self.output_schema,
        )
