import typer
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import List
from pathlib import Path

from src.cli.formatters import CLIPrinter
from src.embedder import Embedder
from src.utils.sort import sort_execution_plan
from src.utils.metadata_extraction import extract_db_info
from src.translator import Translator
from src.prompts.registry import PROMPTS


app = typer.Typer()
printer = CLIPrinter()
embedder = Embedder()


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
    

    printer.saved_to(output_path, label="Metadata saved to")


@app.command("translate")
def translate(
    metadata_path: str = typer.Option(
        "./metadata.json", help="Path to the metadata JSON file"
    ),
    query: str = typer.Argument(..., help="Natural language query to translate"),
    output_path: str = typer.Option(
        None, help="Onde salvar o plano (padrão: execution_plan_YYYYmmdd-HHMMSS.json)"
    ),
    prompt_name: str = typer.Option(
        "v2", help="Prompt version to use (options: v1, v2)", show_default=True
    ),
):
    if prompt_name not in PROMPTS:
        raise typer.BadParameter(f"Invalid prompt_name '{prompt_name}'. Options: {', '.join(PROMPTS)}")

    translator = Translator(metadata_path, prompt_builder=PROMPTS[prompt_name])
    data = translator.translate(query)
    data.execution_plan = sort_execution_plan(data.execution_plan)
    
    if not output_path:
        Path("./plans").mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = str(Path("plans") / f"execution_plan_{ts}.json")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(
        json.dumps(data.model_dump(), indent=4, ensure_ascii=False), encoding="utf-8"
    )
    
    printer.print_execution_plan(data)
    printer.saved_to(out, label="Execution plan saved to")


if __name__ == "__main__":
    load_dotenv()
    app()
