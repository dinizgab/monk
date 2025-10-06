from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

from src.models.execution_plan import ExecutionPlan
from src.utils import extract_json


load_dotenv()


def prompt(query: str, metadata: str) -> str:
    return f"""
    You are an expert in federated database query optimization. Taking into account the metadata file of my databases, which contains tables, columns, and their types, translate the following question in natural language into an SQL execution plan.

    [DATABASE METADATA]
    {metadata}
    [END OF METADATA]

    You must generate a detailed sequential execution plan. The plan should divide the question into the minimum number of necessary queries, assign each query to the correct database, and define the dependencies between them. The final data aggregation will be done at the application level.
    All the databases necessary informations should be found in the metadata file.
    Return ONLY a JSON structure with the following format:

    [JSON FORMAT]
    {{
    "execution_plan": [
        {{
        "id": <int>,
        "description": "<string: a natural language description of what this query does>",
        "database": "<string: the database URL>",
        "query": "<string: the SQL query>",
        "depends_on": [<int: a list of step_ids on which this step depends. Empty if there is no dependency>],
        "join_info": {{
            "type": "<string: the type of join to be performed in the application, e.g., INNER, LEFT, RIGHT, FULL>",
            "on": {{
                "current_step_column": "<string: the join column of this query>",
                "dependency_step_column": "<string: the join column of the dependency query>"
            }}
        }}
        }}
    ],
    "final_aggregation": {{
        "type": "<string: e.g., COUNT, SUM, AVG, or NONE>",
        "column": "<string: the column to aggregate>"
    }},
    "final_output_columns": ["<string: the list of columns to be displayed in the final result>"]
    }}
    [END OF JSON FORMAT]

    Additional Instructions:
    - If a query depends on the results of another, use a placeholder in the format $stepID.columnName in the WHERE clause. For example: WHERE id IN ($step1.user_id).
    - The join_info field is only necessary for steps that have dependencies and need to be aggregated. For the first step or independent steps, it can be omitted, use only these words (LEFT, RIGHT, FULL and INNER).
    - `final_aggregation` describes the final operation performed by the application. If no aggregation is needed, use "NONE".

    [EXAMPLES]
    
    ---
    Question: "Show the names and order dates for customers from Brazil."
    
    [METADATA FOR EXAMPLE]
    DB1 (CRM - PostgreSQL): postgres://.../crmdb
      - table: customers (id, name, country)
    DB2 (Sales - MySQL): mysql://.../salesdb
      - table: orders (order_id, customer_id, order_date)
    [END METADATA FOR EXAMPLE]
    
    {{
      "execution_plan": [
        {{
          "id": 1,
          "description": "Get IDs of all customers from Brazil.",
          "database": "postgres://.../crmdb",
          "query": "SELECT id FROM customers WHERE country = 'Brazil';",
          "depends_on": []
        }},
        {{
          "id": 2,
          "description": "Get order dates for the customers found in step 1.",
          "database": "mysql://.../salesdb",
          "query": "SELECT customer_id, order_date FROM orders WHERE customer_id IN ($step1.id);",
          "depends_on": [1],
          "join_info": {{
            "type": "INNER",
            "on": {{
              "current_step_column": "customer_id",
              "dependency_step_column": "id"
            }}
          }}
        }}
      ],
      "final_aggregation": {{ "type": "NONE" }},
      "final_output_columns": ["name", "order_date"]
    }}
    ---
    
    [CURRENT TASK]
    Question: {query}
"""


class TranslationReturn(BaseModel):
    execution_plan: list[ExecutionPlan]
    final_output_columns: list[str]
    final_aggregation: dict[str, str]


def translate_query(
    metadata_file_path: str,
    query: str,
) -> TranslationReturn:
    client = OpenAI()
    metadata = ""
    with open(metadata_file_path, "rb") as f:
        metadata = f.read().decode("utf-8")

    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {
                "role": "user",
                "content": prompt(query, metadata),
            }
        ],
    )

    data = extract_json(response.output_text)
    return TranslationReturn(**data)
