from typing import Any, TypedDict


class ExerciseState(TypedDict, total=False):
    action: str
    company: dict[str, Any]
    exercise_id: str
    company_id: str
    scenario_input: dict[str, Any]
    scenario: dict[str, Any]
    current_inject: dict[str, Any]
    inject_index: int
    events: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    agent_results: dict[str, Any]
    agent_latencies: dict[str, int]
    agent_tokens: dict[str, int | None]
    approval: dict[str, Any]
    status: str
    report: dict[str, Any]
    communication_requested: bool
