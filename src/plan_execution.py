import re
import pandas as pd
from sqlalchemy import create_engine, text

from src.models.execution_plan import ExecutionPlan
from src.utils.metadata_extraction import add_url_driver


def execute_plan(plan: ExecutionPlan) -> None:
    partial_results = {}
    db_engines = {}

    for step in plan.execution_plan:
        print("-" * 40)
        print(f"▶️ Executing Step {step.id}: {step.description}")

        query = _replace_placeholders(step.query, partial_results)

        db_url =  add_url_driver(step.database)
        if db_url not in db_engines:
            db_engines[db_url] = create_engine(db_url)

        engine = db_engines[db_url]
        print(f"Executing {step.id} on database: {db_url}")
        try:
            with engine.connect() as conn:
                current_df = pd.read_sql(text(query), conn)
            print(f"✅ Step executed successfully - Returned {len(current_df)} rows.")
        except Exception as e:
            print(e)
            raise RuntimeError(f"Failed to execute query into database {db_url}: {e}")


        final_step_df = current_df
        if step.depends_on and step.join_info:
            print("-" * 40)
            print(f"▶️ Joining results with step(s): {step.depends_on}")
            dep_id_to_join = step.depends_on[0]
            dep_df = partial_results[dep_id_to_join]

            final_step_df = pd.merge(
                left=dep_df,
                right=current_df,
                how=step.join_info.type.lower(),
                left_on=step.join_info.on["dependency_step_column"],
                right_on=step.join_info.on["current_step_column"],
            )
            print(f"✅ Join resulted in {len(final_step_df)} rows.")

        partial_results[step.id] = final_step_df

    print("-" * 40)

    last_step = plan.execution_plan[-1]
    final_df = partial_results[last_step.id]

    if plan.final_aggregation:
        final_df = _aggregate_results(final_df, plan.final_aggregation)

    if plan.final_output_columns:
        existing_cols = [
            col for col in final_df.columns if col in plan.final_output_columns
        ]
        final_df = final_df[existing_cols]

    return final_df


def _replace_placeholders(query: str, partial_results: dict[int, pd.DataFrame]) -> str:
    placeholders = re.findall(r"(\$step\d+).(\w+)", query)
    for step_id, col in placeholders:
        dep_id = int(step_id[-1])
        if dep_id not in partial_results:
            raise RuntimeError(f"Step {dep_id} has not been executed yet.")

        dep_df = partial_results[dep_id]
        if col not in dep_df.columns:
            raise RuntimeError(f"Column '{col}' not found in results of step {dep_id}.")

        values = tuple(dep_df[col].unique())
        if not values:
            values_sql = "NULL"
        else:
            values_sql = str(values)

        query = query.replace(f"{step_id}.{col}", values_sql)

    return query


def _aggregate_results(df: pd.DataFrame, aggregation: dict[str, str]) -> pd.DataFrame:
    match aggregation["type"].upper():
        case "COUNT":
            return pd.DataFrame({"count": [len(df)]})
        case "SUM":
            col = aggregation.get("column")
            if col not in df.columns:
                raise RuntimeError(f"Column '{col}' not found for SUM aggregation.")
            return pd.DataFrame({"sum": [df[col].sum()]})
        case "AVG":
            col = aggregation.get("column")
            if col not in df.columns:
                raise RuntimeError(f"Column '{col}' not found for AVG aggregation.")
            return pd.DataFrame({"avg": [df[col].mean()]})
        case "MAX":
            col = aggregation.get("column")
            if col not in df.columns:
                raise RuntimeError(f"Column '{col}' not found for MAX aggregation.")
            return pd.DataFrame({"max": [df[col].max()]})
        case "MIN":
            col = aggregation.get("column")
            if col not in df.columns:
                raise RuntimeError(f"Column '{col}' not found for MIN aggregation.")
            return pd.DataFrame({"min": [df[col].min()]})
        case "NONE":
            return df
        case _:
            raise RuntimeError(f"Unsupported aggregation type: {aggregation['type']}")
