from app.models.document import DocumentChunk, SourceDocument


class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: list[SourceDocument]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for doc in documents:
            chunks.extend(self._split_one(doc))
        return chunks

    def _split_one(self, document: SourceDocument) -> list[DocumentChunk]:
        text = document.text.strip()
        if not text:
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        index = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            chunk_text = text[start:end].strip()
            if chunk_text:
                # TODO: 当前是纯字符窗口切分；后续升级为段落/标题/语义切分，并记录 offset metadata。
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document.doc_id}#chunk-{index}",
                        text=chunk_text,
                        source=document.source,
                    )
                )
                index += 1
            if end >= len(text):
                break
            start += step

        return chunks
