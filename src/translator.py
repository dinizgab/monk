import json
import re

from openai import OpenAI
from typing import Any, Callable

from src.models.execution_plan import TranslationReturn
  

class Translator():
	def __init__(self, metadata_path: str, prompt_builder: Callable[[str, str], str], model_name: str = "gpt-5-mini"):
		self.client = OpenAI()
		self.model_name = model_name
		self.prompt_builder = prompt_builder
		self.metadata_path = metadata_path
		
	def translate(self, query) -> TranslationReturn:
		metadata = self._load_metadata()
		prompt = self.prompt_builder(query, metadata)
     
		response = self.client.responses.create(
			model=self.model_name,
			input=[
				{
					"role": "user",
					"content": prompt,
				}
			],
		)
  
		data = self._extract_json(response.output_text)
		return TranslationReturn(**data)
  
  
	def _load_metadata(self) -> str:
		with open(self.metadata_path, "rb") as f:
			return f.read().decode("utf-8")
    
    
	def _extract_json(self, text: str) -> dict[str, Any]:
		cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

		start = cleaned.find("{")
		end = cleaned.rfind("}")
		if start == -1 or end == -1 or end <= start:
			raise ValueError(
				"Não foi possível localizar um objeto JSON no retorno do modelo."
			)

		snippet = cleaned[start : end + 1]
		return json.loads(snippet)
