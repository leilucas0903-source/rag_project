"""
TODO: 后续在这里实现关键词检索能力，用于和向量检索组成真正的 Hybrid Retrieval。

最小落地方向：
1. 定义统一的 retrieve(query, top_k) 接口
2. 明确 BM25 使用的数据来源（离线索引语料 / 本地倒排 / 外部搜索引擎）
3. 返回结构统一为 RetrievedDoc，便于和 Milvus 结果做融合
4. 后续在 HybridRetriever 中接入 RRF / rerank
"""
