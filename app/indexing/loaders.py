import json
from pathlib import Path

from app.models.document import SourceDocument


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


class DocumentLoader:
    def load(self, input_path: str) -> list[SourceDocument]:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"输入路径不存在: {input_path}")

        if path.is_file():
            return self._load_file(path)

        documents: list[SourceDocument] = []
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES | {".jsonl"}:
                documents.extend(self._load_file(file_path))
        return documents

    def _load_file(self, file_path: Path) -> list[SourceDocument]:
        if file_path.suffix.lower() == ".jsonl":
            return self._load_jsonl(file_path)

        # TODO: 后续补 doc_id 冲突规避、编码探测、以及更丰富的 source metadata。
        text = file_path.read_text(encoding="utf-8")
        return [
            SourceDocument(
                doc_id=file_path.stem,
                text=text,
                source=str(file_path),
            )
        ]

    def _load_jsonl(self, file_path: Path) -> list[SourceDocument]:
        documents: list[SourceDocument] = []
        with file_path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                text = (record.get("text") or "").strip()
                if not text:
                    continue
                doc_id = str(record.get("id") or f"{file_path.stem}-{idx}")
                source = str(record.get("source") or file_path)
                documents.append(SourceDocument(doc_id=doc_id, text=text, source=source))
        return documents
