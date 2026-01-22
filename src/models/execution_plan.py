from pydantic import BaseModel


class JoinInfo(BaseModel):
    type: str
    on: dict[str, str]


class ExecutionPlan(BaseModel):
    id: int
    description: str
    database: str
    query: str
    depends_on: list[int]
    output_columns: list[dict[str, str]] = []
    join_info: JoinInfo | None = None
