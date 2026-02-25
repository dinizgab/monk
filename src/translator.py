from openai import OpenAI
from typing import Callable

from src.models.execution_plan import TranslationReturn
from src.utils import extract_json
  

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
  
		data = extract_json(response.output_text)
		return TranslationReturn(**data)
  
	def _load_metadata(self) -> str:
		with open(self.metadata_path, "rb") as f:
			return f.read().decode("utf-8")
    
