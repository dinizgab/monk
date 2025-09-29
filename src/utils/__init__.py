import json
import re
from typing import Any
from collections import deque

from src.models.execution_plan import ExecutionPlan


def extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            "Não foi possível localizar um objeto JSON no retorno do modelo."
        )

    snippet = cleaned[start : end + 1]
    return json.loads(snippet)


def sort_execution_plan(steps: list[ExecutionPlan]) -> list[ExecutionPlan]:
    in_degrees = {step.id: len(step.depends_on) for step in steps}
    queue = deque([s for s in steps if in_degrees[s.id] == 0])
    sorted_steps = []

    while queue:
        current = queue.popleft()
        sorted_steps.append(current)

        for step in steps:
            if current.id in step.depends_on:
                in_degrees[step.id] -= 1

                if in_degrees[step.id] == 0:
                    queue.append(step)

    if len(sorted_steps) != len(steps):
        raise ValueError("Ciclo detectado no plano de execução.")

    return sorted_steps
