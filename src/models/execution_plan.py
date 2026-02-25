from pydantic import BaseModel


class JoinInfo(BaseModel):
    type: str
    on: dict[str, str]


class ExecutionStep(BaseModel):
    id: int
    description: str
    database: str
    query: str
    depends_on: list[int]
    output_columns: list[dict[str, str]] = []
    join_info: JoinInfo | None = None


class FinalAggregationModel(BaseModel):
    type: str
    column: str = ""
    distinct: bool = False
    group_by: list[str] = []


class TranslationReturn(BaseModel):
    execution_plan: list[ExecutionStep]
    final_output_columns: list[str]
    final_aggregation: FinalAggregationModel