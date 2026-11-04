from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

OutputT = TypeVar("OutputT", bound=BaseModel)


class LLMProvider(ABC):
    last_tokens_used: int | None = None

    @abstractmethod
    def generate_structured(
        self, *, prompt: str, user_data: dict, output_schema: type[OutputT]
    ) -> OutputT:
        """Return validated structured output. Implementations must not perform external actions."""
