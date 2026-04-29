import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.indexing.embedding_worker import EmbeddingWorker
from app.indexing.loaders import DocumentLoader
from app.indexing.milvus_upsert import MilvusUpserter
from app.indexing.splitter import TextSplitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="重建 Milvus 文档索引")
    parser.add_argument("input_path", help="输入文件或目录，支持 txt/md/jsonl")
    parser.add_argument("--drop-old", action="store_true", help="重建前删除旧集合")
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    loader = DocumentLoader()
    splitter = TextSplitter(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    embedder = EmbeddingWorker()
    upserter = MilvusUpserter()

    documents = loader.load(args.input_path)
    print(f"加载文档数: {len(documents)}")
    if not documents:
        print("没有可索引文档，退出")
        return

    chunks = splitter.split_documents(documents)
    print(f"切分后 chunk 数: {len(chunks)}")
    if not chunks:
        print("切分后没有有效 chunk，退出")
        return

    vectors = embedder.embed_texts([chunk.text for chunk in chunks])
    upserter.ensure_collection(drop_old=args.drop_old)
    inserted = upserter.upsert_chunks(chunks, vectors)

    print(f"已写入 Milvus chunk 数: {inserted}")
    print(f"集合名: {settings.milvus_collection}")
    print("重建完成")


if __name__ == "__main__":
    main()
