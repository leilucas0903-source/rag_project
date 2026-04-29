from pymilvus import DataType, MilvusClient

from app.core.config import settings
from app.core.logger import get_logger
from app.models.document import DocumentChunk

logger = get_logger(__name__)


class MilvusUpserter:
    def __init__(self):
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            user=settings.milvus_user or None,
            password=settings.milvus_password or None,
        )
        self.collection_name = settings.milvus_collection

    def ensure_collection(self, drop_old: bool = False) -> None:
        if drop_old and self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)
            logger.info(f"Dropped Milvus collection: {self.collection_name}")

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

    def upsert_chunks(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks 与 vectors 数量不一致")

        if not chunks:
            return 0

        rows = [
            {
                "id": chunk.chunk_id,
                "vector": vector,
                "text": chunk.text,
                "source": chunk.source,
            }
            for chunk, vector in zip(chunks, vectors)
        ]
        self.client.insert(collection_name=self.collection_name, data=rows)
        logger.info(f"Inserted {len(rows)} chunks into Milvus")
        return len(rows)
