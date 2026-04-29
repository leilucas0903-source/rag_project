from typing import List

from app.core.logger import get_logger
from app.indexing.embedding_worker import EmbeddingWorker
from app.models.response import RetrievedDoc
from app.retrieval.milvus_retriever import MilvusRetriever

logger = get_logger(__name__)


class HybridRetriever:
    def __init__(self):
        self.embedder = EmbeddingWorker()
        self.milvus_retriever = MilvusRetriever()

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedDoc]:
        query = query.strip()
        if not query:
            return []

        query_vector = self.embedder.embed_query(query)
        ##TODO后续添加 bm25
        
        logger.info(f"Searching Milvus for query: {query}")
        docs: List[RetrievedDoc] = self.milvus_retriever.search(query_vector, top_k)

        if not docs:
            logger.warning("No documents found in Milvus, returning empty results")
            return []

        return docs
