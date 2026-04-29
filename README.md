## 项目目标
基于 FastAPI 的 RAG 问答系统：FAQ 直查 + RAG 回退，采用 MySQL/Milvus/Redis 架构，支持结构化日志与 Prometheus 监控

## 技术栈
* **API Framework**: FastAPI
* **Vector Store**: Milvus
* **Metadata Store**: MySQL
* **Monitoring**: Prometheus
* **Core Design**: Hybrid Retrieval & Intent Routing

## 当前进度 (Day 1)
- [x] 工程骨架搭建
- [x] 日志链路追踪 (RequestID)
- [x] 统一异常处理与指标监控
- [x] 意图路由基础占位
- [x] Mock 主链路联调

## 下一步计划
- [x] 接入 MySQL FAQ 检索
- [x] 接入 Milvus 向量检索
- [x] 实现 RRF 混合重排算法

### 今日任务概述(Day 2)

- 修复 MySQL 连接与 FAQ 初始化环境
- 接入最小真实 RAG 链路
- 抽离离线索引流数据结构

### 关键改动

- 修复 Docker / .env.example / 初始化 SQL / test_sql.py
- 新增 indexing 模块与 scripts/reindex.py
- HybridRetriever 改为真实 embedding 检索
- LLMClient 改为真实调用骨架
- 新增 app/models/document.py
- 修复并重建 Record.md

### 当前结果

- FAQ 链路可用
- MySQL 连接稳定
- reindex 入口可用
- RAG 主链路已从 mock 走向真实实现


### 后续计划

- 解耦 generation 层
- 准备真实文档并完成 reindex
- 验证 /query 的完整 RAG 路径
