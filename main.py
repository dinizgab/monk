from datetime import datetime
import typer
import json
from typing import List
from pathlib import Path

from src.utils.metadata_extraction import extract_db_info
from src.query_translation import translate_query

# oracle://user:password@host:1521/dbname
# postgresql://user:password@host:5432/dbname
# mysql://user:password@host:3306/dbname
# mssql://user:password@host:1433/dbname

app = typer.Typer()


@app.command("extract_metadata")
def extract_metadata(
    db_urls: List[str] = typer.Argument(..., help="List of database URLs"),
    output_path: str = typer.Option(
        "./metadata.json", help="Path to save the extracted metadata"
    ),
):
    info = extract_db_info(db_urls)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(info, f, indent=4, ensure_ascii=False)

    print(f"Databases metadata extracted and saved to {output_path}")


@app.command("translate")
def translate(
    metadata_path: str = typer.Option(
        "./metadata.json", help="Path to the metadata JSON file"
    ),
    query: str = typer.Argument(..., help="Natural language query to translate"),
    output_path: str = typer.Option(None, help="Onde salvar o plano (padrão: execution_plan-YYYYmmdd-HHMMSS.json)"),
):

    data = translate_query(metadata_path, query)

    if not output_path:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = f"execution_plan-{ts}.json"

    out = Path(output_path)
    out.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")

    print(f"Execution plan saved to {out.resolve()}")


if __name__ == "__main__":
    app()
