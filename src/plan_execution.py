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

        db_url = add_url_driver(step.database)
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
        final_df = _aggregate_results(
            final_df, plan.final_aggregation, plan.final_output_columns
        )

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

        dtype = dep_df[col].dtype
        values = dep_df[col].dropna().unique()
        if len(values) == 0:
            if pd.api.types.is_numeric_dtype(dtype):
                values_sql = -1
            else:
                values_sql = "''"
        else:
            if pd.api.types.is_string_dtype(
                dtype
            ) or pd.api.types.is_datetime64_any_dtype(dtype):
                values_list = [f"'{v}'" for v in values]
            else:
                values_list = [str(v) for v in values]

            values_sql = f"{', '.join(values_list)}"

        query = query.replace(f"{step_id}.{col}", values_sql)

    return query


def _aggregate_results(
    df: pd.DataFrame, aggregation_info: dict[str, str], final_output_columns: list[str]
) -> pd.DataFrame:
    agg_type = aggregation_info.get("type", "NONE").upper()
    agg_column = aggregation_info.get("column")

    if agg_type == "NONE":
        return df

    if not agg_column:
        raise RuntimeError(f"Aggregation column not specified for type {agg_type}")
    if agg_column not in df.columns:
        if all(col in df.columns for col in final_output_columns):
            return df[final_output_columns]
        else:
            raise RuntimeError(f"Aggregation column '{agg_column}' not found in DataFrame.")

    group_by_cols = [
        col for col in final_output_columns if col != agg_column and col in df.columns
    ]
    if not group_by_cols:
        if agg_type == "COUNT":
            result_val = df[agg_column].nunique()
        elif agg_type == "SUM":
            result_val = df[agg_column].sum()
        elif agg_type == "AVG":
            result_val = df[agg_column].mean()
        elif agg_type == "MAX":
            result_val = df[agg_column].max()
        elif agg_type == "MIN":
            result_val = df[agg_column].min()
        else:
            raise RuntimeError(f"Tipo de agregação global não suportado: {agg_type}")

        if len(final_output_columns) == 1:
            final_col_name = final_output_columns[0]
        else:
            final_col_name = f"{agg_column}_{agg_type.lower()}"

        return pd.DataFrame({final_col_name: [result_val]})
    else:

        grouped_df = df.groupby(group_by_cols)
        result_df = None

        if agg_type == "SUM":
            result_df = grouped_df[agg_column].sum().reset_index()
        elif agg_type == "COUNT":
            result_df = grouped_df[agg_column].nunique().reset_index()
        elif agg_type == "AVG":
            result_df = grouped_df[agg_column].mean().reset_index()
        elif agg_type == "MAX":
            result_df = grouped_df[agg_column].max().reset_index()
        elif agg_type == "MIN":
            result_df = grouped_df[agg_column].min().reset_index()
        else:
            raise RuntimeError(f"Tipo de agregação agrupada não suportado: {agg_type}")

        if agg_column not in result_df.columns:
            result_df.rename(columns={result_df.columns[-1]: agg_column}, inplace=True)

        return result_df
