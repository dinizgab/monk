from datetime import datetime
import typer
import json
from typing import List
from pathlib import Path

from src.utils.sort import sort_execution_plan
from src.utils.metadata_extraction import extract_db_info
from src.query_translation import TranslationReturn, translate_query
from src.plan_execution import execute_plan

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
    output_path: str = typer.Option(
        None, help="Onde salvar o plano (padrão: execution_plan_YYYYmmdd-HHMMSS.json)"
    ),
):
    data = translate_query(metadata_path, query)

    if not output_path:
        Path("./plans").mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = f"/plans/execution_plan_{ts}.json"

    print("-" * 40)
    data.execution_plan = sort_execution_plan(data.execution_plan)
    print("Execution Plan Steps:")
    for step in data.execution_plan:
        print(f" - {step.id}: {step.description}")

    print("-" * 40)
    out = Path(output_path)
    out.write_text(
        json.dumps(data.model_dump(), indent=4, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Execution plan saved to {out.resolve()}")
    print("-" * 40)

    # print(f"Executing plan...")
    # result_df = execute_plan(data)

    # result_df.to_csv("result.csv", index=False)
    # print("Final result saved to result.csv")

    # print(result_df.head())
    # print("-" * 40)


if __name__ == "__main__":
    #with open("./test/sales_questions.json", "r") as f:
    #    items = json.load(f)
    #
    #    Path("./plans").mkdir(parents=True, exist_ok=True)
    #    for i, item in enumerate(items):
    #        print(f"Running test {i+1}/{len(items)}")
    #        print(f"Question: {item['question']}")
    #        translate(
    #            metadata_path="./metadata.json",
    #            query=item["question"],
    #            output_path=f"./plans/sales/plan_{i+1}.json",
    #        )
    #        print("=" * 80)

    #errors = {}
    #test_domains = ["bakery_1", "ecommerce", "sales"] 
    #
    #for domain in test_domains:
    #    for plan in Path(f"./plans/{domain}").glob("*.json"):
    #        print(f"Executing plan {plan.name}...")
    #        with open(plan, "r") as f:
    #            data = json.load(f)
    #            data = TranslationReturn(**data)
    #            try:
    #                result_df = execute_plan(data)
    #            except Exception as e:
    #                print(f"Error executing plan {domain}/{plan.name}: {e}")
    #                errors[f'{domain}/{plan.name}'] = str(e)
    #                continue
    #
    #            out_path = Path(f"./test_data/results/{domain}/result_{plan.stem}.csv")
    #            out_path.parent.mkdir(parents=True, exist_ok=True)
    #            result_df.to_csv(out_path, index=False)
    #            print(f"Final result saved to {out_path.resolve()}")
    #
    #print("All plans executed.")
    #print(f"total errors: {len(errors)}")
    #for p, e in errors.items():
    #    print(f"{p} : {e}")

    app()
