"""
Utility CLI for interacting with the test databases.

Supported commands:
- extract_metadata: generate metadata JSON by listing database container names instead of full URLs.
- translate: translate the test suite questions into SQL execution plans using the metadata file.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from dataclasses import dataclass
from pathlib import Path
import re
import traceback
from typing import Dict, List

import pandas as pd
import typer

from src.plan_execution import execute_plan
from src.query_translation import TranslationReturn, translate_query
from src.utils.metadata_extraction import extract_db_info
from src.utils.sort import sort_execution_plan


@dataclass(frozen=True)
class ContainerConfig:
    dialect: str
    username: str
    password: str
    database: str
    port: int
    host: str = "localhost"

    def to_url(self) -> str:
        return f"{self.dialect}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


_BASE_CONTAINERS: Dict[str, ContainerConfig] = {
    # Store
    "store_alt": ContainerConfig(
        dialect="postgresql",
        username="store_alt_user",
        password="store_alt_pass",
        database="store_alt",
        port=5442,
    ),
    "store_main": ContainerConfig(
        dialect="postgresql",
        username="store_main_user",
        password="store_main_pass",
        database="store_main",
        port=5441,
    ),
    # Chat
    "app": ContainerConfig(
        dialect="postgresql",
        username="app_user",
        password="app_pass",
        database="app",
        port=5440,
    ),
    "app_chat": ContainerConfig(
        dialect="postgresql",
        username="app_chat_user",
        password="app_chat_pass",
        database="app_chat",
        port=5439,
    ),
    # Sales
    "sales_eu": ContainerConfig(
        dialect="postgresql",
        username="eu_user",
        password="eu_pass",
        database="sales_eu",
        port=5437,
    ),
    "sales_us": ContainerConfig(
        dialect="postgresql",
        username="us_user",
        password="us_pass",
        database="sales_us",
        port=5438,
    ),
    # Ecommerce
    "ecommerce_mysql_products": ContainerConfig(
        dialect="mysql",
        username="appuser",
        password="apppass",
        database="products_db",
        port=3307,
    ),
    "ecommerce_mysql_orders": ContainerConfig(
        dialect="mysql",
        username="appuser",
        password="apppass",
        database="orders_db",
        port=3308,
    ),
    "ecommerce_pg_users": ContainerConfig(
        dialect="postgresql",
        username="appuser",
        password="root",
        database="users_db",
        port=5433,
    ),
    "ecommerce_pg_shipments": ContainerConfig(
        dialect="postgresql",
        username="appuser",
        password="root",
        database="shipments_db",
        port=5434,
    ),
    # Bakery 1
    "bakery_1_mysql_receipts": ContainerConfig(
        dialect="mysql",
        username="appuser",
        password="apppass",
        database="receipts_db",
        port=3309,
    ),
    "bakery_1_mysql_items": ContainerConfig(
        dialect="mysql",
        username="appuser",
        password="apppass",
        database="items_db",
        port=3310,
    ),
    "bakery_1_pg_customers": ContainerConfig(
        dialect="postgresql",
        username="appuser",
        password="root",
        database="customers_db",
        port=5435,
    ),
    "bakery_1_pg_goods": ContainerConfig(
        dialect="postgresql",
        username="appuser",
        password="root",
        database="goods_db",
        port=5436,
    ),
}

_CONTAINER_ALIASES: Dict[str, str] = {
    # Sales
    "sales_eu_db": "sales_eu",
    "sales_us_db": "sales_us",
    # Bakery 1
    "bakery_1_mysql_item": "bakery_1_mysql_items",
}

CONTAINER_CONFIGS: Dict[str, ContainerConfig] = {
    **_BASE_CONTAINERS,
    **{alias: _BASE_CONTAINERS[target] for alias, target in _CONTAINER_ALIASES.items()},
}

QUESTIONS_ROOT = Path("test/suites/schemas")
RESULTS_ROOT = Path("test/results")
app = typer.Typer(
    help="Helper commands for extracting metadata and translating test questions."
)


def _canonical_column_name(column_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(column_name).strip().lower())


def _normalize_value_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    numeric_ratio = float(numeric.notna().mean()) if len(series) else 0.0
    if numeric_ratio >= 0.8:
        return numeric
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.lower()
    )


def _normalize_projection(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    projected = df[columns].copy()
    projected = projected.rename(columns={col: _canonical_column_name(col) for col in columns})

    normalized_columns: dict[str, pd.Series] = {}
    for col in projected.columns:
        normalized_columns[col] = _normalize_value_series(projected[col])

    normalized_df = pd.DataFrame(normalized_columns)
    normalized_df = normalized_df.sort_index(axis=1)

    sort_view = normalized_df.copy()
    for col in sort_view.columns:
        if pd.api.types.is_numeric_dtype(sort_view[col]):
            sort_view[col] = sort_view[col].map(lambda v: "" if pd.isna(v) else f"{float(v):.12g}")
        else:
            sort_view[col] = sort_view[col].fillna("").astype(str)

    sorted_index = sort_view.sort_values(by=list(sort_view.columns), kind="mergesort").index
    return normalized_df.loc[sorted_index].reset_index(drop=True)


def _compare_series(a: pd.Series, b: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
        for av, bv in zip(a.tolist(), b.tolist()):
            if pd.isna(av) and pd.isna(bv):
                continue
            if pd.isna(av) != pd.isna(bv):
                return False
            if abs(float(av) - float(bv)) > 1e-4:
                return False
        return True

    for av, bv in zip(a.tolist(), b.tolist()):
        if pd.isna(av) and pd.isna(bv):
            continue
        if str(av) != str(bv):
            return False
    return True


def _compare_csv_files(a: Path, b: Path) -> bool:
    try:
        da = pd.read_csv(a)
        db = pd.read_csv(b)

        left_map = {_canonical_column_name(col): col for col in da.columns}
        right_map = {_canonical_column_name(col): col for col in db.columns}
        common_keys = [key for key in left_map.keys() if key in right_map]

        if not common_keys:
            return False

        left_projected = _normalize_projection(da, [left_map[key] for key in common_keys])
        right_projected = _normalize_projection(db, [right_map[key] for key in common_keys])

        if len(left_projected) != len(right_projected):
            return False

        for col in left_projected.columns:
            if col not in right_projected.columns:
                return False
            if not _compare_series(left_projected[col], right_projected[col]):
                return False
        return True
    except Exception:
        return a.read_bytes() == b.read_bytes()


def _classify_execution_failure(exception_type: str, message: str) -> str:
    msg = f"{exception_type} {message}".lower()

    hallucination_patterns = [
        "unknown column",
        "no such column",
        "column '",
        "does not exist",
        "no such table",
        "returned unexpected schema",
    ]
    if any(pattern in msg for pattern in hallucination_patterns):
        return "ERRO_ALUCINACAO"

    aggregation_patterns = [
        "aggregation column",
        "unsupported global aggregation",
        "unsupported grouped aggregation",
        "final results",
    ]
    if any(pattern in msg for pattern in aggregation_patterns):
        return "ERRO_AGREGACAO"

    integration_patterns = [
        "join",
        "depends on step",
        "referenced step",
        "placeholder",
    ]
    if any(pattern in msg for pattern in integration_patterns):
        return "ERRO_JUNCAO_INTEGRACAO"

    query_patterns = [
        "syntax error",
        "programmingerror",
        "sql",
        "failed to execute step",
    ]
    if any(pattern in msg for pattern in query_patterns):
        return "ERRO_QUERY"

    return "ERRO_EXECUCAO_NAO_CLASSIFICADO"


def _available_containers() -> str:
    return ", ".join(sorted(CONTAINER_CONFIGS))


def _resolve_connection(identifier: str) -> str:
    if "://" in identifier:
        return identifier

    normalized = identifier.lower()
    if normalized not in CONTAINER_CONFIGS:
        raise typer.BadParameter(
            f"Unknown container '{identifier}'. Available containers: {_available_containers()}. "
            "You can also pass a full database URL if the container is not predefined."
        )
    return CONTAINER_CONFIGS[normalized].to_url()


def _load_questions(suite_name: str) -> List[dict]:
    questions_path = QUESTIONS_ROOT / suite_name / "questions.json"
    if not questions_path.exists():
        raise typer.BadParameter(f"Questions file not found at {questions_path}")

    try:
        data = json.loads(questions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON in {questions_path}: {exc}") from exc

    if not isinstance(data, list):
        raise typer.BadParameter(f"Expected a list of questions in {questions_path}")

    return data


def _append_error_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _append_execution_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _plan_number(path: Path) -> int:
    m = re.search(r"plan_(\d+)\.json$", path.name)
    if not m:
        raise ValueError(f"Nome inesperado: {path.name}")
    return int(m.group(1))


@app.command("extract_metadata")
def extract_metadata(
    containers: List[str] = typer.Argument(
        ..., help="Container names or database URLs"
    ),
    output_path: Path = typer.Option(
        Path("./metadata.json"), help="Where to save the metadata JSON"
    ),
):
    urls = [_resolve_connection(name) for name in containers]
    metadata = extract_db_info(urls)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    typer.echo(f"Metadata saved to {output_path.resolve()}")


@app.command("translate")
def translate(
    suite_name: str = typer.Argument(
        ..., help="Name of the test suite (folder under test/schema)"
    ),
    metadata_path: Path = typer.Option(
        Path("./metadata.json"), help="Path to the metadata JSON"
    ),
):
    if not metadata_path.exists():
        raise typer.BadParameter(f"Metadata file not found: {metadata_path}")

    questions = _load_questions(suite_name)
    plans_dir = Path("plans") / suite_name
    plans_dir.mkdir(parents=True, exist_ok=True)

    for item in questions:
        question_id = item.get("id")
        question_text = item.get("question")
        if question_id is None or not question_text:
            typer.echo(f"Skipping malformed item: {item}")
            continue

        typer.echo(f"Translating question {question_id}: {question_text}")
        translation = translate_query(str(metadata_path), question_text)
        translation.execution_plan = sort_execution_plan(translation.execution_plan)

        output_path = plans_dir / f"plan_{question_id}.json"
        output_path.write_text(
            json.dumps(translation.model_dump(), indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        typer.echo(f"Saved plan to {output_path}")


@app.command("run_plans")
def run_plans(
    suite_name: List[str] = typer.Argument(
        help="Name of the test suite (folder under test/schemas)",
        default=["bakery_1", "chat", "ecommerce", "sales", "store"],
    ),
):
    for suite in suite_name:
        plans_dir = Path("plans_v2") / suite
        if not plans_dir.exists():
            typer.echo(f"Plans directory not found for suite '{suite}': {plans_dir}")
            continue

        questions = _load_questions(suite)
        questions_by_id = {
            item.get("id"): item.get("question")
            for item in questions
            if item.get("id") is not None and item.get("question")
        }

        plan_files = sorted(plans_dir.glob("plan_*.json"), key=_plan_number)

        typer.echo("============================================")
        typer.echo(f"Found {len(plan_files)} plan(s) in {plans_dir}")
        typer.echo(f"Running plans for suite '{suite}'...")
        typer.echo("============================================")

        errors_out_path = RESULTS_ROOT / "errors" / f"{suite}.jsonl"
        execution_out_path = RESULTS_ROOT / "execution_logs" / f"{suite}.jsonl"
        crossing_dir = RESULTS_ROOT / "crossing_data" / suite
        suite_results_dir = RESULTS_ROOT / "results" / suite

        errors_out_path = Path(f"./test/errors/{suite}.jsonl")
        execution_out_path = Path(f"./test/execution_logs/{suite}.jsonl")
        
        errors_out_path.unlink(missing_ok=True)
        execution_out_path.unlink(missing_ok=True)
        for i, plan_file in enumerate(plan_files):
            plan_num = _plan_number(plan_file)
            typer.echo(f"Processing plan file: {plan_num}")

            with open(plan_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data = TranslationReturn(**data)
                question = questions_by_id.get(plan_num, "")
                try:
                    result_df = execute_plan(data)
                except Exception as e:
                    err_payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "suite": suite,
                        "plan_num": plan_num,
                        "plan_file": str(plan_file),
                        "exception_type": type(e).__name__,
                        "message": str(e),
                        "traceback": traceback.format_exc(),
                    }
                    _append_error_jsonl(errors_out_path, err_payload)

                    execution_payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "suite": suite,
                        "plan_num": plan_num,
                        "question": question,
                        "execution_plan_path": str(plan_file),
                        "status": "FAILED",
                        "failure_group": "FALHA_EXECUCAO",
                        "raw_exception_type": type(e).__name__,
                        "raw_exception_message": str(e),
                    }
                    _append_execution_jsonl(execution_out_path, execution_payload)
                    typer.echo(
                        f"[ERROR] suite={suite} plan_num={plan_num} {type(e).__name__}: {e}"
                    )
                    continue


            res_out_path = suite_results_dir / f"result_plan_{plan_num}.csv"
            res_out_path.parent.mkdir(parents=True, exist_ok=True)
            result_df.to_csv(res_out_path, index=False)

            status = "SUCCESS"
            failure_group = None
            execution_payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "suite": suite,
                "plan_num": plan_num,
                "question": question,
                "execution_plan_path": str(plan_file),
                "result_path": str(res_out_path),
                "status": status,
                "failure_group": failure_group,
                "rows_count": int(len(result_df)),
                "empty_result": bool(result_df.empty),
            }
            _append_execution_jsonl(execution_out_path, execution_payload)

            print(f"Final result saved to {res_out_path.resolve()}")

        typer.echo("============================================")
        typer.echo(f"Completed running plans for suite '{suite}'.")
        typer.echo("============================================")


@app.command("analyze_execution_logs")
def analyze_execution_logs(
    suite_name: List[str] = typer.Argument(
        default=["bakery_1", "chat", "ecommerce", "sales", "store"],
        help="Suites to analyze from test/results/execution_logs",
    ),
):
    summary = {}
    for suite in suite_name:
        log_path = Path(f"test/execution_logs/{suite}.jsonl")
        if not log_path.exists():
            typer.echo(f"Execution log not found for suite '{suite}': {log_path}")
            continue

        rows = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        status_count: Dict[str, int] = {}
        group_count: Dict[str, int] = {}
        type_count: Dict[str, int] = {}
        empty_success = 0
        for row in rows:
            status = row.get("status", "UNKNOWN")
            status_count[status] = status_count.get(status, 0) + 1

            failure_group = row.get("failure_group")
            if failure_group:
                group_count[failure_group] = group_count.get(failure_group, 0) + 1

            failure_type = row.get("failure_type")
            if failure_type:
                type_count[failure_type] = type_count.get(failure_type, 0) + 1

            if row.get("status") == "SUCCESS" and row.get("empty_result") is True:
                empty_success += 1

        summary[suite] = {
            "total_execucoes": len(rows),
            "status": status_count,
            "falhas_por_grupo": group_count,
            "falhas_por_tipo": type_count,
            "resultados_vazios_com_execucao_valida": empty_success,
        }

    out_path = RESULTS_ROOT / "execution_analysis_summary.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    typer.echo(f"Execution analysis summary saved to {out_path.resolve()}")



@app.command("debug_plan")
def debug_plan(
    plan_path: Path = typer.Argument(..., help="Path to the plan JSON file"),
):
    if not plan_path.exists():
        raise typer.BadParameter(f"Plan file not found: {plan_path}")

    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        data = TranslationReturn(**data)
        try:
            result_df = execute_plan(data)
            typer.echo("Execution successful. Result:")
            typer.echo(result_df)
        except Exception as e:
            typer.echo(f"[ERROR] {type(e).__name__}: {e}")
            typer.echo(traceback.format_exc())


if __name__ == "__main__":
    app()
