"""
Utility CLI for interacting with the test databases.

Supported commands:
- extract_metadata: generate metadata JSON by listing database container names instead of full URLs.
- translate: translate the test suite questions into SQL execution plans using the metadata file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import typer

from src.query_translation import translate_query
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
        dialect="postgresql", username="app_chat_user", password="app_chat_pass", database="app_chat_db", port=5439
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

# Allow common aliases such as container_name from docker-compose or shorter identifiers
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

QUESTIONS_ROOT = Path("test/schema")
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


@app.command()
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


@app.command()
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


if __name__ == "__main__":
    app()