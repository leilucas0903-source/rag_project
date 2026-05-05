from __future__ import annotations

import hashlib
import math

from app.core.config import settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class EmbeddingWorker:
    _model_cache: dict[str, object] = {}
    _model_load_failed: set[str] = set()

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self.dimension = settings.embedding_dimension

    @property
    def model(self):
        if self.model_name in self._model_cache:
            return self._model_cache[self.model_name]

        if self.model_name in self._model_load_failed:
            return None

        if SentenceTransformer is None:
            self._model_load_failed.add(self.model_name)
            return None

        try:
            # TODO: 后续结合启动预热和本地模型目录，避免首次请求时再判定模型可用性。
            model = SentenceTransformer(self.model_name, local_files_only=True)
            self._model_cache[self.model_name] = model
            return model
        except Exception:
            self._model_load_failed.add(self.model_name)
            return None

    def embed_query(self, query: str) -> list[float]:
        return self._embed_one(query)

    def embed_texts(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        if not texts:
            return []

        model = self.model
        if model is not None:
            vectors = model.encode(
                texts,
                batch_size=batch_size or settings.embedding_batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vectors.tolist()

        # TODO: 当前 fallback 向量只用于“先跑通”；后续应替换为真实可控的 embedding 方案。
        return [self._fallback_embed(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        model = self.model
        if model is not None:
            vector = model.encode(text, normalize_embeddings=True)
            return vector.tolist()
        return self._fallback_embed(text)

    def _fallback_embed(self, text: str) -> list[float]:
        text = (text or "").strip().lower()
        if not text:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        units = self._split_units(text)

        for idx, unit in enumerate(units):
            bucket = self._hash_to_bucket(unit)
            weight = 1.0 + min(idx, 8) * 0.03
            vector[bucket] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def _split_units(self, text: str) -> list[str]:
        units: list[str] = []
        for token in text.split():
            units.append(token)

        chars = [char for char in text if not char.isspace()]
        units.extend(chars)

        for i in range(len(chars) - 1):
            units.append(chars[i] + chars[i + 1])

        return units or [text]

    def _hash_to_bucket(self, text: str) -> int:
        digest = hashlib.md5(text.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dimension
