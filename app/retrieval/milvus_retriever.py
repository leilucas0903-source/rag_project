from typing import List

from pymilvus import DataType, MilvusClient

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
        self._ensure_collection()

    def _ensure_collection(self):
        if self.client.has_collection(self.collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=settings.embedding_dimension,
        )
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4000)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=500)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def search(self, query_vector: List[float], top_k: int = 3) -> List[RetrievedDoc]:
        try:
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
            return []

    def insert_documents(self, documents: List[dict]):
        try:
            self.client.insert(collection_name=self.collection_name, data=documents)
            logger.info(f"Inserted {len(documents)} documents to Milvus")
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")
