from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

from src.models.execution_plan import ExecutionPlan
from src.utils import extract_json


load_dotenv()


def prompt(query: str):
    return f"""
    You are an expert in federated database query optimization. Taking into account the metadata file of my databases, which contains tables, columns, and their types, translate the following question in natural language into an SQL execution plan.
    Question: {query}
    You must generate a detailed sequential execution plan. The plan should divide the question into the minimum number of necessary queries, assign each query to the correct database, and define the dependencies between them. The final data aggregation will be done at the application level.
    All the databases necessary informations should be found in the metadata file.
    Return ONLY a JSON structure with the following format:

    {{
    "execution_plan": [
        {{
        "step_id": <int>,
        "description": "<string: a natural language description of what this query does>",
        "database": "<string: the database URL>",
        "query": "<string: the SQL query>",
        "depends_on": [<int: a list of step_ids on which this step depends. Empty if there is no dependency>],
        "join_info": {{
            "type": "<string: the type of join to be performed in the application, e.g., INNER, LEFT>",
            "on": {{
                "current_step_column": "<string: the join column of this query>",
                "dependency_step_column": "<string: the join column of the dependency query>"
            }}
        }}
        }}
    ],
    "final_output_columns": ["<string: the list of columns to be displayed in the final result>"]
    }}

    Additional Instructions:
    - If a query depends on the results of another, use a placeholder in the format $stepID.columnName in the WHERE clause. For example: WHERE id IN ($step1.user_id).
    - The join_info field is only necessary for steps that have dependencies and need to be aggregated. For the first step or independent steps, it can be omitted.
"""


class TranslationReturn(BaseModel):
    execution_plan: list[ExecutionPlan]
    final_output_columns: list[str]


def translate_query(
    metadata_file_path: str,
    query: str,
) -> str:
    client = OpenAI()
    storage = client.vector_stores.create(name="database_metadata_storage")

    with open(metadata_file_path, "rb") as f:
        client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=storage.id,
            files=[f],
        )

    response = client.responses.create(
        model="gpt-5",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt(query),
                    },
                ],
            }
        ],
        tools=[{"type": "file_search", "vector_store_ids": [storage.id]}],
    )

    data = extract_json(response.output_text)
    TranslationReturn(**data)

    return data
