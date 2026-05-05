import argparse
import sys
from pathlib import Path

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

    embedder = EmbeddingWorker()
    loader = DocumentLoader()
    splitter = TextSplitter(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    upserter = MilvusUpserter()

    documents = loader.load(args.input_path)
    if not documents:
        print("Error: 未找到任何文档。")
        return

    chunks = splitter.split_documents(documents)
    if not chunks:
        print("Error: 文档切分后没有可入库的 chunk。")
        return

    print(f"待处理 Chunks 总数: {len(chunks)}")

    upserter.ensure_collection(drop_old=args.drop_old)

    # TODO: 后续将 batch_size 做成命令行参数或配置项，便于按机器资源调优。
    batch_size = 64
    total_inserted = 0

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        batch_texts = [c.text for c in batch_chunks]

        # TODO: 后续补 tqdm / logging / dry-run，增强大规模重建时的可观测性。
        batch_vectors = embedder.embed_texts(batch_texts)
        inserted = upserter.upsert_chunks(batch_chunks, batch_vectors)
        total_inserted += inserted

    print("\n重建完成！")
    print(f"- 原始文档数: {len(documents)}")
    print(f"- 成功写入 Chunk 数: {total_inserted}")
    print(f"- Collection: {settings.milvus_collection}")


if __name__ == "__main__":
    main()
