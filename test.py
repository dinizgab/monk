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
from typing import Dict, Iterable, List

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
        dialect="postgresql", username="store_alt_user", password="store_alt_pass", database="store_alt", port=5442
    ),
    "store_main": ContainerConfig(
        dialect="postgresql", username="store_main_user", password="store_main_pass", database="store_main", port=5441
    ),
    # Chat
    "app": ContainerConfig(
        dialect="postgresql", username="app_user", password="app_pass", database="app", port=5440
    ),
    "app_chat": ContainerConfig(
        dialect="postgresql", username="app_chat_user", password="app_chat_pass", database="app_chat", port=5439
    ),
    # Sales
    "sales_eu": ContainerConfig(
        dialect="postgresql", username="eu_user", password="eu_pass", database="sales_eu", port=5437
    ),
    "sales_us": ContainerConfig(
        dialect="postgresql", username="us_user", password="us_pass", database="sales_us", port=5438
    ),
    # Ecommerce
    "ecommerce_mysql_products": ContainerConfig(
        dialect="mysql", username="appuser", password="apppass", database="products_db", port=3307
    ),
    "ecommerce_mysql_orders": ContainerConfig(
        dialect="mysql", username="appuser", password="apppass", database="orders_db", port=3308
    ),
    "ecommerce_pg_users": ContainerConfig(
        dialect="postgresql", username="appuser", password="root", database="users_db", port=5433
    ),
    "ecommerce_pg_shipments": ContainerConfig(
        dialect="postgresql", username="appuser", password="root", database="shipments_db", port=5434
    ),
    # Bakery 1
    "bakery_1_mysql_receipts": ContainerConfig(
        dialect="mysql", username="appuser", password="apppass", database="receipts_db", port=3309
    ),
    "bakery_1_mysql_items": ContainerConfig(
        dialect="mysql", username="appuser", password="apppass", database="items_db", port=3310
    ),
    "bakery_1_pg_customers": ContainerConfig(
        dialect="postgresql", username="appuser", password="root", database="customers_db", port=5435
    ),
    "bakery_1_pg_goods": ContainerConfig(
        dialect="postgresql", username="appuser", password="root", database="goods_db", port=5436
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

QUESTIONS_ROOT = Path("test/schemas")
app = typer.Typer(help="Helper commands for extracting metadata and translating test questions.")


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
        

def _plan_number(path: Path) -> int:
    m = re.search(r"plan_(\d+)\.json$", path.name)
    if not m:
        raise ValueError(f"Nome inesperado: {path.name}")
    return int(m.group(1))


@app.command("extract_metadata")
def extract_metadata(
    containers: List[str] = typer.Argument(..., help="Container names or database URLs"),
    output_path: Path = typer.Option(Path("./metadata.json"), help="Where to save the metadata JSON"),
):
    """Extract database metadata using container names instead of full URLs."""

    urls = [_resolve_connection(name) for name in containers]
    metadata = extract_db_info(urls)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
    typer.echo(f"Metadata saved to {output_path.resolve()}")


@app.command("translate")
def translate(
    suite_name: str = typer.Argument(..., help="Name of the test suite (folder under test/schema)"),
    metadata_path: Path = typer.Option(Path("./metadata.json"), help="Path to the metadata JSON"),
):
    """Translate all questions in a suite into SQL execution plans."""

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
            json.dumps(translation.model_dump(), indent=4, ensure_ascii=False), encoding="utf-8"
        )
        typer.echo(f"Saved plan to {output_path}")


@app.command("run_plans")
def run_plans(
    suite_name: List[str] = typer.Argument(help="Name of the test suite (folder under test/schemas)", default=["bakery_1", "chat", "ecommerce", "sales", "store"] ),
):
    """Run all translation plans for the specified test suites."""

    for suite in suite_name:
        plans_dir = Path("plans") / suite
        if not plans_dir.exists():
            typer.echo(f"Plans directory not found for suite '{suite}': {plans_dir}")
            continue

        plan_files = sorted(plans_dir.glob("plan_*.json"), key=_plan_number)

        typer.echo("============================================")
        typer.echo(f"Found {len(plan_files)} plan(s) in {plans_dir}")
        typer.echo(f"Running plans for suite '{suite}'...")
        typer.echo("============================================")
        
        errors_out_path = Path(f"./test_data/errors/{suite}.jsonl")
        for i, plan_file in enumerate(plan_files):
            plan_num = _plan_number(plan_file)
            typer.echo(f"Processing plan file: {plan_num}")
            
            with open(plan_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data = TranslationReturn(**data)
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
                    typer.echo(f"[ERROR] suite={suite} plan_num={plan_num} {type(e).__name__}: {e}")
                    continue

            res_out_path = Path(f"./test_data/results/{suite}/result_{plan_num}.csv")
            res_out_path.parent.mkdir(parents=True, exist_ok=True)
            result_df.to_csv(res_out_path, index=False)
            print(f"Final result saved to {res_out_path.resolve()}")
            
        typer.echo("============================================")
        typer.echo(f"Completed running plans for suite '{suite}'.")
        typer.echo("============================================")


if __name__ == "__main__":
    app()