import re
from contextlib import contextmanager
from typing import Dict, Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.models.execution_plan import ExecutionPlan
from src.utils.metadata_extraction import add_url_driver

class ExecutionError(Exception):
    """Custom exception for execution plan errors."""
    pass

@contextmanager
def get_db_engines(databases: set[str]) -> Dict[str, Engine]:
    """Context manager for database engine lifecycle management."""
    engines = {}
    try:
        for db_url in databases:
            engines[db_url] = create_engine(db_url)
        yield engines
    finally:
        for engine in engines.values():
            engine.dispose()

def execute_plan(plan: ExecutionPlan) -> pd.DataFrame:
    partial_results: Dict[int, pd.DataFrame] = {}
    
    db_urls = {add_url_driver(step.database) for step in plan.execution_plan}
    
    with get_db_engines(db_urls) as db_engines:
        for step in plan.execution_plan:
            print("-" * 40)
            print(f"▶️ Executing Step {step.id}: {step.description}")
            
            query = _replace_placeholders(step.query, partial_results)
            current_df = _execute_query(step, query, db_engines)
            
            final_step_df = _handle_joins(step, current_df, partial_results)
            
            partial_results[step.id] = final_step_df

    print("-" * 40)
    
    final_df = partial_results[plan.execution_plan[-1].id]
    return _finalize_results(final_df, plan)


def _execute_query(step, query: str, db_engines: Dict[str, Engine]) -> pd.DataFrame:
    db_url = add_url_driver(step.database)
    engine = db_engines[db_url]
    
    print(f"Executing {step.id} on database: {db_url}")
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        print(f"✅ Step executed successfully - Returned {len(df)} rows.")
        return df
    except Exception as e:
        raise ExecutionError(
            f"Failed to execute step {step.id} on database {db_url}: {e}"
        ) from e

def _handle_joins(
    step, 
    current_df: pd.DataFrame, 
    partial_results: Dict[int, pd.DataFrame]
) -> pd.DataFrame:
    """Handle joining current results with dependencies."""
    if not (step.depends_on and step.join_info):
        return current_df
    
    print("-" * 40)
    print(f"▶️ Joining results with step(s): {step.depends_on}")
    
    dep_id = step.depends_on[0]
    if dep_id not in partial_results:
        raise ExecutionError(f"Step {step.id} depends on step {dep_id} which hasn't been executed")
    
    dep_df = partial_results[dep_id]
    
    left_col = step.join_info.on["dependency_step_column"]
    right_col = step.join_info.on["current_step_column"]
    
    if left_col not in dep_df.columns:
        raise ExecutionError(f"Join column '{left_col}' not found in step {dep_id} results")
    if right_col not in current_df.columns:
        raise ExecutionError(f"Join column '{right_col}' not found in step {step.id} results")
    
    joined_df = pd.merge(
        left=dep_df,
        right=current_df,
        how=step.join_info.type.lower(),
        left_on=left_col,
        right_on=right_col,
    )
    
    print(f"✅ Join resulted in {len(joined_df)} rows.")
    return joined_df

def _replace_placeholders(query: str, partial_results: dict[int, pd.DataFrame]) -> str:
    placeholders = re.findall(r"(\$step\d+).(\w+)", query)
    for step_ref, col in placeholders:
        dep_id_str = step_ref.replace("$step", "")
        if not dep_id_str.isdigit():
            raise ExecutionError(f"Invalid placeholder '{step_ref}.{col}' in query")
        
        dep_id = int(dep_id_str)
        
        if dep_id not in partial_results:
            raise ExecutionError(f"Referenced step {dep_id} not found in results")
        
        dep_df = partial_results[dep_id]
        
        if col not in dep_df.columns:
            raise ExecutionError(f"Column '{col}' not found in step {dep_id} results")
        
        values_sql = _format_column_values(dep_df[col])
        query = query.replace(f"{step_ref}.{col}", values_sql)
    
    return query

def _format_column_values(series: pd.Series) -> str:
    dtype = series.dtype
    values = series.dropna().unique()
    
    if len(values) == 0:
        return 'NULL'
    
    if pd.api.types.is_string_dtype(dtype) or pd.api.types.is_datetime64_any_dtype(dtype):
        values_list = [
            "'" + str(v).replace("'", "''") + "'" 
            for v in values
        ]
    else:
        values_list = [str(v) for v in values]
    
    return ', '.join(values_list)

def _finalize_results(
    df: pd.DataFrame, 
    plan: ExecutionPlan
) -> pd.DataFrame:
    """Apply final aggregations and column filtering."""
    if plan.final_aggregation:
        df = _aggregate_results(df, plan.final_aggregation, plan.final_output_columns)
    
    if plan.final_output_columns:
        existing_cols = [col for col in plan.final_output_columns if col in df.columns]
        if not existing_cols:
            raise ExecutionError(
                f"None of the requested output columns {plan.final_output_columns} "
                f"found in final results"
            )
        df = df[existing_cols]
    
    return df


def _aggregate_results(
    df: pd.DataFrame, 
    aggregation_info: Dict[str, str], 
    final_output_columns: Optional[list[str]]
) -> pd.DataFrame:
    """
    Apply aggregation to results with optional grouping.
    
    Supports: COUNT, SUM, AVG, MAX, MIN
    """
    agg_type = aggregation_info.get("type", "NONE").upper()
    agg_column = aggregation_info.get("column")
    
    if agg_type == "NONE":
        return df
    
    # Validate aggregation parameters
    if not agg_column:
        raise ExecutionError(f"Aggregation column not specified for type {agg_type}")
    
    if agg_column not in df.columns:
        # Check if we can proceed without aggregation
        if final_output_columns and all(col in df.columns for col in final_output_columns):
            return df[final_output_columns]
        raise ExecutionError(f"Aggregation column '{agg_column}' not found in DataFrame")
    
    # Determine grouping columns
    group_by_cols = []
    if final_output_columns:
        group_by_cols = [
            col for col in final_output_columns 
            if col != agg_column and col in df.columns
        ]
    
    # Perform aggregation
    if not group_by_cols:
        return _global_aggregation(df, agg_type, agg_column, final_output_columns)
    else:
        return _grouped_aggregation(df, agg_type, agg_column, group_by_cols)


def _global_aggregation(
    df: pd.DataFrame,
    agg_type: str,
    agg_column: str,
    final_output_columns: Optional[list[str]]
) -> pd.DataFrame:
    """Perform aggregation across entire dataframe (no grouping)."""
    agg_functions = {
        "COUNT": lambda s: s.nunique(),
        "SUM": lambda s: s.sum(),
        "AVG": lambda s: s.mean(),
        "MAX": lambda s: s.max(),
        "MIN": lambda s: s.min(),
    }
    
    if agg_type not in agg_functions:
        raise ExecutionError(f"Unsupported global aggregation type: {agg_type}")
    
    result_val = agg_functions[agg_type](df[agg_column])
    
    # Determine output column name
    if final_output_columns and len(final_output_columns) == 1:
        col_name = final_output_columns[0]
    else:
        col_name = f"{agg_column}_{agg_type.lower()}"
    
    return pd.DataFrame({col_name: [result_val]})


def _grouped_aggregation(
    df: pd.DataFrame,
    agg_type: str,
    agg_column: str,
    group_by_cols: list[str]
) -> pd.DataFrame:
    """Perform aggregation with grouping."""
    grouped = df.groupby(group_by_cols, dropna=False)
    
    agg_functions = {
        "COUNT": lambda g: g.nunique(),
        "SUM": lambda g: g.sum(),
        "AVG": lambda g: g.mean(),
        "MAX": lambda g: g.max(),
        "MIN": lambda g: g.min(),
    }
    
    if agg_type not in agg_functions:
        raise ExecutionError(f"Unsupported grouped aggregation type: {agg_type}")
    
    result_df = agg_functions[agg_type](grouped[agg_column]).reset_index()
    
    # Rename the aggregated column if needed
    if agg_column not in result_df.columns:
        result_df.rename(
            columns={result_df.columns[-1]: agg_column}, 
            inplace=True
        )
    
    return result_df