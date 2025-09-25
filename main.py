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
):

    print(translate_query(metadata_path, query))


if __name__ == "__main__":
    app()
