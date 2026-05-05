from typing import List

from app.core.logger import get_logger
from app.indexing.embedding_worker import EmbeddingWorker
from app.models.response import RetrievedDoc
from app.retrieval.milvus_retriever import MilvusRetriever

logger = get_logger(__name__)


class HybridRetriever:
    def __init__(self):
        self.embedder = EmbeddingWorker()
        self._milvus_retriever: MilvusRetriever | None = None

    def _get_milvus_retriever(self) -> MilvusRetriever | None:
        if self._milvus_retriever is not None:
            return self._milvus_retriever

        try:
            self._milvus_retriever = MilvusRetriever()
            return self._milvus_retriever
        except Exception as e:
            logger.warning(f"Milvus 初始化失败: {e}")
            return None

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedDoc]:
        query = query.strip()
        if not query:
            return []

        milvus_retriever = self._get_milvus_retriever()
        if not milvus_retriever:
            return []

        try:
            query_vector = self.embedder.embed_query(query)
        except Exception as e:
            logger.error(f"Embedding query failed: {e}")
            return []

        # TODO: 当前只有向量检索；后续接入 BM25 / RRF / rerank，才算真正的 Hybrid Retrieval。
        logger.info(f"Searching Milvus for query: {query}")
        docs: List[RetrievedDoc] = milvus_retriever.search(query_vector, top_k)

        if not docs:
            logger.warning("No documents found in Milvus, returning empty results")
            return []

        return docs
