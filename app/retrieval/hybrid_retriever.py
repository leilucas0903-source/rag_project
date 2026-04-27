from app.models.response import RetrievedDoc
from typing import List

# 在 FastAPI 中，所有的 I/O 操作（未来你的数据库查询、LLM 调用）都是异步的

class HybridRetriever:
    def retrieve(self,query:str,top_k:int = 3) -> List[RetrievedDoc]:
        docs = [
            RetrievedDoc(doc_id="doc-1", score=0.89, snippet=f"与“{query}”相关的知识片段A"),
            RetrievedDoc(doc_id="doc-2", score=0.82, snippet=f"与“{query}”相关的知识片段B"),
            RetrievedDoc(doc_id="doc-3", score=0.77, snippet=f"与“{query}”相关的知识片段C"),
        ]
        return docs[:top_k]

