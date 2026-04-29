from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingWorker:
    _model_cache: dict[str, SentenceTransformer] = {}

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model

    @property
    def model(self) -> SentenceTransformer:
        if self.model_name not in self._model_cache:
            self._model_cache[self.model_name] = SentenceTransformer(self.model_name)
        return self._model_cache[self.model_name]

    def embed_query(self, query: str) -> list[float]:
        vector = self.model.encode(query, normalize_embeddings=True)
        return vector.tolist()

    def embed_texts(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=batch_size or settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()
