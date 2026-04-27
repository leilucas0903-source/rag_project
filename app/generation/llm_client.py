from typing import List
from multiprocessing import context
from app.models.response import RetrievedDoc, GeneratedAnswer

class LLMClient:
    def generator(self, query: str, docs: List[RetrievedDoc]) -> GeneratedAnswer:
        context = ';'.join([d.snippet for d in docs])
        return GeneratedAnswer(
            text=f"基于检索结果，关于「{query}」”的回答是：{context}",
            citations=[d.doc_id for d in docs],
            model="mock-llm-v1",
        )