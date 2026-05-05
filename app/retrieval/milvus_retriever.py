from typing import List

from pymilvus import MilvusClient

from app.core.config import settings
from app.core.logger import get_logger
from app.models.response import RetrievedDoc

logger = get_logger(__name__)


class MilvusRetriever:
    def __init__(self):
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            user=settings.milvus_user or None,
            password=settings.milvus_password or None,
        )
        self.collection_name = settings.milvus_collection

    def _require_collection(self) -> None:
        if not self.client.has_collection(self.collection_name):
            raise RuntimeError(
                f"Milvus collection '{self.collection_name}' 不存在，请先执行 reindex 初始化知识库。"
            )

    def search(self, query_vector: List[float], top_k: int = 3) -> List[RetrievedDoc]:
        self._require_collection()

        try:
            # TODO: 后续补 score 归一化、更多 metadata 字段、以及对空集合/冷集合的更细错误分类。
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                anns_field="vector",
                search_params={"metric_type": "COSINE", "params": {}},
                limit=top_k,
                output_fields=["text"],
            )

            docs: list[RetrievedDoc] = []
            for hits in results:
                for hit in hits:
                    entity = hit.get("entity", {})
                    docs.append(
                        RetrievedDoc(
                            doc_id=str(hit["id"]),
                            score=float(hit["distance"]),
                            snippet=entity.get("text", ""),
                        )
                    )
            return docs
        except Exception as e:
            logger.error(f"Milvus search failed: {e}")
            raise

    def insert_documents(self, documents: List[dict]):
        # TODO: 该写入方法后续可删除或迁移到 indexing 层，避免 retrieval 层承担写职责。
        try:
            self.client.insert(collection_name=self.collection_name, data=documents)
            logger.info(f"Inserted {len(documents)} documents to Milvus")
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")

    def health_status(self) -> dict:
        exists = self.client.has_collection(self.collection_name)
        info = {
            "ok": True,
            "host": settings.milvus_host,
            "port": settings.milvus_port,
            "collection": self.collection_name,
            "collection_exists": exists,
        }

        if not exists:
            info["doc_count"] = 0
            return info

        try:
            stats = self.client.get_collection_stats(collection_name=self.collection_name)
            info["stats"] = stats
            info["doc_count"] = int(stats.get("row_count", 0))
        except Exception as e:
            info["stats_error"] = str(e)
            info["doc_count"] = None

        return info

    def sample_documents(self, limit: int = 5) -> list[dict]:
        if not self.client.has_collection(self.collection_name):
            return []

        # TODO: 后续补 source 截断、snippet 截断和排序字段，避免 admin 调试接口返回过重。
        rows = self.client.query(
            collection_name=self.collection_name,
            filter="id != ''",
            output_fields=["id", "text", "source"],
            limit=limit,
        )
        return [
            {
                "id": row.get("id", ""),
                "text": row.get("text", ""),
                "source": row.get("source", ""),
            }
            for row in rows
        ]
