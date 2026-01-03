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


def prompt_2(query: str, metadata: str) -> str:
    return f"""
      You are an expert in federated database query planning.

      Given the database metadata (tables, columns, types, and database URLs), produce a minimal-step SEQUENTIAL execution plan to answer the natural-language question.

      [DATABASE METADATA]
      {metadata}
      [END OF METADATA]

      Core rules (MUST follow):
      1) Use ONLY tables/columns that exist in the metadata. Never invent columns.
      2) Each step must include an explicit output contract:
        - Provide "output_columns": a list of objects with:
          - "alias": the exact column name that will appear in the step result
          - "source": the exact table.column selected
        - The SQL query must SELECT exactly those columns with matching aliases.
        - Never use SELECT *.
      3) Alias normalization:
        - Every selected column MUST use the alias format: s<step_id>__<column_name>.
          Example: SELECT users.id AS s1__id, users.username AS s1__username ...
      4) Dependencies & placeholders:
        - If a step depends on a previous step, reference dependency values ONLY with placeholders:
          $step<id>.<alias>
          Example: WHERE orders.customer_id IN ($step1.s1__id)
        - NEVER use driver placeholders like $1, ?, :param.
      5) Join info contract:
        - If depends_on is not empty, include join_info.
        - join_info.on.current_step_column and dependency_step_column MUST reference output aliases
          (e.g., "s2__customer_id" and "s1__id"), not raw column names.
        - join_info.type must be one of: INNER, LEFT, RIGHT, FULL.
      6) Final output contract:
        - final_output_columns must list ONLY aliases that exist after application-level joining.
        - If a column is needed in the final output, it must be present in some step output_columns.
      7) Final aggregation model:
        - Use this structure:
          {{
            "type": "COUNT|SUM|AVG|MIN|MAX|NONE",
            "column": "<alias from the final dataset>",
            "distinct": <true|false>,
            "group_by": ["<alias>", ...]
          }}
        - If no aggregation: {{ "type": "NONE" }}.
        - Do NOT encode DISTINCT inside the "column" string.

      Return ONLY valid JSON with this format:

      {{
        "execution_plan": [
          {{
            "id": <int>,
            "description": "<string>",
            "database": "<string: the database URL from metadata>",
            "query": "<string: SQL>",
            "output_columns": [
              {{ "alias": "<string>", "source": "<table.column>" }}
            ],
            "depends_on": [<int>],
            "join_info": {{
              "type": "INNER|LEFT|RIGHT|FULL",
              "on": {{
                "current_step_column": "<alias from THIS step output_columns>",
                "dependency_step_column": "<alias from dependency step output_columns>"
              }}
            }}
          }}
        ],
        "final_aggregation": {{
          "type": "COUNT|SUM|AVG|MIN|MAX|NONE",
          "column": "<alias>",
          "distinct": <true|false>,
          "group_by": ["<alias>", "..."]
        }},
        "final_output_columns": ["<alias>", "..."]
      }}

      Before finalizing, self-check (must pass):
      - Every referenced column exists in metadata.
      - Every join_info column exists in the referenced step output_columns.
      - final_output_columns are present in at least one step output_columns.
      - Aggregation column is an alias, not an expression string.

      [CURRENT TASK]
      Question: {query}
    """.strip()


class FinalAggregationModel(BaseModel):
    type: str
    column: str = ""
    distinct: bool = False
    group_by: list[str] = []


class TranslationReturn(BaseModel):
    execution_plan: list[ExecutionPlan]
    final_output_columns: list[str]
    final_aggregation: FinalAggregationModel
    
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
                "content": prompt_2(query, metadata),
            }
        ],
    )

    data = extract_json(response.output_text)
    return TranslationReturn(**data)
