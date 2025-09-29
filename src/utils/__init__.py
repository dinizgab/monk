import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            "Não foi possível localizar um objeto JSON no retorno do modelo."
        )

    snippet = cleaned[start : end + 1]
    return json.loads(snippet)
