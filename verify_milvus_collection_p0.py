#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pymilvus import MilvusClient  # noqa: E402
from app.core.config import settings  # noqa: E402

SUSPECT_GARBLED_PATTERNS = [
    "浣", "鎴", "绯", "鍚", "妫", "璇", "鐨", "銆", "锛", "锟", "�"
]


def has_garbled_text(text: str) -> bool:
    if not text:
        return False
    return any(token in text for token in SUSPECT_GARBLED_PATTERNS)


def short_text(text: str, limit: int = 160) -> str:
    text = (text or "").replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


def main():
    print("=" * 80)
    print("P0-3 Milvus 集合核验")
    print("=" * 80)

    client = MilvusClient(
        uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
        user=settings.milvus_user or None,
        password=settings.milvus_password or None,
    )

    collection_name = settings.milvus_collection
    print(f"目标集合: {collection_name}")

    exists = client.has_collection(collection_name)
    print(f"集合存在: {exists}")

    if not exists:
        print("结论: 业务集合还没准备好，当前 RAG 检索不成立。")
        return

    try:
        stats = client.get_collection_stats(collection_name=collection_name)
        print(f"集合统计: {stats}")
    except Exception as e:
        print(f"读取集合统计失败: {e}")

    print("\n尝试抽样查询 text 字段...")
    try:
        rows = client.query(
            collection_name=collection_name,
            filter="id != ''",
            output_fields=["id", "text"],
            limit=10,
        )
    except Exception as e:
        print(f"抽样查询失败: {e}")
        return

    if not rows:
        print("集合存在，但没有可读样本，基本等于没数据。")
        return

    normal_count = 0
    garbled_count = 0
    empty_count = 0

    for idx, row in enumerate(rows, start=1):
        doc_id = row.get("id", "")
        text = row.get("text", "")

        if not text:
            empty_count += 1
            flag = "空文本"
        elif has_garbled_text(text):
            garbled_count += 1
            flag = "疑似乱码"
        else:
            normal_count += 1
            flag = "正常"

        print(f"[{idx}] id={doc_id} | {flag} | text={short_text(text)}")

    print("\n统计:")
    print(f"正常样本: {normal_count}")
    print(f"疑似乱码样本: {garbled_count}")
    print(f"空文本样本: {empty_count}")

    if garbled_count > 0:
        print("结论: Milvus 内部 text 字段存在乱码风险。")
    elif normal_count > 0:
        print("结论: Milvus 至少有部分文本样本是正常的。")
    else:
        print("结论: 当前集合数据质量可疑。")


if __name__ == "__main__":
    main()
