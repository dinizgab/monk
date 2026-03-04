from openai import OpenAI
import numpy as np


class Embedder():
    def __init__(self, model_name: str = "gpt-5-mini"):
        self.client = OpenAI()
        self.model_name = model_name
        self.index = []
    
    
    def save_to_index(self, metadata: list[str]):
        for db in metadata:
            for table_name, columns in db["tables"].items():
                col_descriptions = [
                    f"{c["name"]} ({c["type"]}){': ' + c['comment'] if c.get('comment') else ''}"
                    for c in columns
                ]
                
                text = (
                    f"Table: {table_name}\n"
                    f"Database: {db.get('description', db['database'])}\n"
                    f"columns: {', '.join(col_descriptions)}"
                )
                embedding = self._embed(text)
                
                self.index.append({
                    "db_url": db["database"],
                    "table": table_name,
                    "text": text,
                    "embedding": embedding,
                })
                
    def fetch_relevant_tables(self, query: str, top_k: int = 2) -> list[dict]:
        query_embedding = self._embed(query)
        
        scored = []
        for entry in self.index:
            score = self._cosine_similarity(query_embedding, entry["embedding"])
            scored.append((score, entry))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]
    
    
    def _embed(self, metadata: str) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.model_name,
            input=metadata,
        )
        return np.array(response.data[0].embedding)
    
    
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))