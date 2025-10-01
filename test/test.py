import json
from pathlib import Path
import pandas as pd

from sqlalchemy import create_engine, text


with open("test.json", "r") as f:
    items = json.load(f)
    failed = []
    engine = create_engine("sqlite:///schemas/sqlite/crossing_data_db.db")

    with engine.connect() as conn:
        for i, item in enumerate(items):
            print(f"Running query {i+1}/{len(items)} on sqlite_crossing_db")
            print(f"Question: {item['question']}")
            try:
                query = item["query"]
                out_path = Path(f"./crossing_data/result_{i+1}.csv")

                out_path.parent.mkdir(parents=True, exist_ok=True)
                df = pd.read_sql(text(query), conn)
                df.to_csv(out_path, index=False)
                print(f"Result saved to {out_path.resolve()}")
            except Exception as e:
                print(f"Error occurred: {e}")
                failed.append(item)

            print("=" * 80)

    if failed:
        print("The following queries failed:")
        for item in failed:
            print(f" - {item['question']}")
