#!/usr/bin/env python3
"""
Milvus服务健康性测试脚本
测试Milvus连接、集合创建、文档插入和向量搜索功能
"""

import sys
import time
from pymilvus import MilvusClient, DataType
import numpy as np

def test_milvus_health():
    """测试Milvus服务健康性"""
    print("🔍 开始测试Milvus服务健康性...")

    try:
        # 连接Milvus
        client = MilvusClient(uri="http://127.0.0.1:19530")
        print("✅ 成功连接到Milvus")

        # 测试集合操作
        collection_name = "test_collection"

        # 删除已存在的测试集合
        if client.has_collection(collection_name):
            client.drop_collection(collection_name)
            print(f"🗑️ 删除已存在的测试集合: {collection_name}")

        # 创建测试集合
        schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=768)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=2000)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="FLAT", metric_type="COSINE")

        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )
        print(f"✅ 成功创建测试集合: {collection_name}")

        # 插入测试数据
        test_docs = [
            {
                "id": "doc1",
                "vector": np.random.rand(768).tolist(),
                "text": "这是一个测试文档，关于人工智能和机器学习。"
            },
            {
                "id": "doc2",
                "vector": np.random.rand(768).tolist(),
                "text": "另一个测试文档，讨论自然语言处理技术。"
            },
            {
                "id": "doc3",
                "vector": np.random.rand(768).tolist(),
                "text": "第三个测试文档，涉及向量数据库和检索系统。"
            }
        ]

        client.insert(collection_name=collection_name, data=test_docs)
        print(f"✅ 成功插入 {len(test_docs)} 条测试文档")

        # 等待索引构建
        time.sleep(2)

        # 测试向量搜索
        query_vector = np.random.rand(768).tolist()
        search_results = client.search(
            collection_name=collection_name,
            data=[query_vector],
            anns_field="vector",
            search_params={"metric_type": "COSINE", "params": {}},
            limit=3,
            output_fields=["text"]
        )

        print(f"✅ 向量搜索成功，返回 {len(search_results[0])} 条结果")
        for i, hit in enumerate(search_results[0]):
            print(f"  结果{i+1}: ID={hit['id']}, 相似度={hit['distance']:.4f}")

        # 清理测试集合
        client.drop_collection(collection_name)
        print(f"🧹 清理测试集合: {collection_name}")

        print("\n🎉 Milvus服务健康性测试全部通过！")
        return True

    except Exception as e:
        print(f"❌ Milvus测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_milvus_health()
    sys.exit(0 if success else 1)