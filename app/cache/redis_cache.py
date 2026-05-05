"""
Redis 缓存占位模块。

TODO:
1. 后续封装 FAQ 热点缓存、检索结果缓存、LLM 响应缓存。
2. 缓存层统一放在 cache/ 下，不污染 retrieval / generation 层职责。
3. 引入 Redis 前，先明确 key 设计和过期策略。
"""

