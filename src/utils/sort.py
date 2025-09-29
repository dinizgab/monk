from collections import deque

from src.models.execution_plan import ExecutionPlan


def sort_execution_plan(steps: list[ExecutionPlan]) -> list[ExecutionPlan]:
    in_degrees = {step.id: len(step.depends_on) for step in steps}
    dependents = {step.id: [] for step in steps}

    for step in steps:
        for dep in step.depends_on:
            dependents[dep].append(step)

    queue = deque([s for s in steps if in_degrees[s.id] == 0])
    sorted_steps = []
    while queue:
        current = queue.popleft()
        sorted_steps.append(current)

        for dep_step in dependents[current.id]:
            in_degrees[dep_step.id] -= 1

            if in_degrees[dep_step.id] == 0:
                queue.append(dep_step)

    if len(sorted_steps) != len(steps):
        raise ValueError("Ciclo detectado no plano de execução.")

    return sorted_steps
