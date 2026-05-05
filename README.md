# rag_project

基于 **FastAPI** 的最小可用 RAG 问答系统，支持：

- **FAQ 直查**
- **RAG 回退**
- **MySQL + Milvus**
- **本地 LLM（Ollama）/ OpenAI Compatible API**
- **结构化日志**
- **Prometheus 指标监控**

> 当前项目已打通：**FAQ + 向量检索 + 本地模型生成** 的最小 RAG 闭环。

---

## 项目目标

构建一个可持续演进的 RAG 问答系统：

- FAQ 问题优先直查
- FAQ 未命中时走 RAG
- 支持离线索引重建
- 支持本地模型与兼容 OpenAI 的模型调用
- 具备基础观测、日志、异常处理与工程化扩展能力

---

## 当前能力

### 已完成
- [x] FastAPI 工程骨架
- [x] `/health` 健康检查
- [x] 请求日志链路追踪（Request ID）
- [x] Prometheus 指标监控
- [x] 全局异常处理
- [x] MySQL FAQ 检索
- [x] Milvus 向量检索
- [x] 离线索引重建脚本 `scripts/reindex.py`
- [x] generation 层解耦
- [x] 本地 Ollama 模型接入
- [x] `/admin/status` 观测接口
- [x] 最小 RAG 闭环打通

### 进行中 / 待完成
- [ ] BM25 检索
- [ ] RRF 混合重排
- [ ] rerank
- [ ] `threshold_policy.py`
- [ ] Redis 缓存层
- [ ] eval / tests / configs 完善

---

## 技术栈

- **API Framework**: FastAPI
- **Vector Store**: Milvus
- **Metadata Store**: MySQL
- **Monitoring**: Prometheus
- **LLM Runtime**: Ollama / OpenAI Compatible API
- **Embedding**: sentence-transformers
- **Core Design**: Hybrid Retrieval & Intent Routing

---

## 项目结构

```text
rag_project/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ routes_query.py
│  │  ├─ routes_admin.py
│  │  └─ schemas.py
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ logger.py
│  │  └─ metrics.py
│  ├─ middleware/
│  │  ├─ request_context.py
│  │  ├─ request_logger.py
│  │  └─ metrics_middleware.py
│  ├─ handlers/
│  │  └─ error_handler.py
│  ├─ models/
│  │  ├─ document.py
│  │  ├─ query.py
│  │  └─ response.py
│  ├─ router/
│  │  ├─ intent_router.py
│  │  └─ threshold_policy.py
│  ├─ retrieval/
│  │  ├─ mysql_faq_retriever.py
│  │  ├─ bm25_retriever.py
│  │  ├─ milvus_retriever.py
│  │  ├─ hybrid_retriever.py
│  │  └─ reranker.py
│  ├─ generation/
│  │  ├─ prompt_builder.py
│  │  ├─ answer_postprocess.py
│  │  └─ llm_client.py
│  └─ indexing/
│     ├─ loaders.py
│     ├─ splitter.py
│     ├─ embedding_worker.py
│     └─ milvus_upsert.py
├─ app/cache/
│  ├─ redis_cache.py
│  └─ cache_keys.py
├─ app/eval/
│  ├─ dataset.py
│  ├─ offline_eval.py
│  └─ online_eval.py
├─ app/tests/
│  ├─ test_api.py
│  ├─ test_router.py
│  ├─ test_retrieval.py
│  └─ test_generation.py
├─ scripts/
│  ├─ reindex.py
│  ├─ warmup_cache.py
│  ├─ replay_logs.py
│  └─ trace_log.py
├─ configs/
│  ├─ config.dev.yaml
│  ├─ config.prod.yaml
│  └─ prompts.yaml
├─ docker/
├─ data/
│  └─ seed/
├─ Record.md
├─ roadmap.md
├─ requirements.txt
└─ README.md
```

---

## 系统流程

### 在线查询链路

```text
用户问题
  -> IntentRouter
  -> FAQ 命中？是 -> MySQL FAQ 返回
  -> 否 -> HybridRetriever
  -> Milvus 检索
  -> generation 组装 prompt
  -> LLM 生成答案
  -> 返回结果
```

### 离线索引链路

```text
原始文档
  -> DocumentLoader
  -> TextSplitter
  -> EmbeddingWorker
  -> MilvusUpserter
  -> 写入 Milvus
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

---

### 2. 启动 MySQL / Milvus

```bash
docker compose up -d
```

建议先确认容器状态：

```bash
docker compose ps
```

---

### 3. 配置环境变量

复制并修改：

```bash
cp .env.example .env
```

你至少需要关注这些配置：

```env
APP_NAME=rag-project
APP_ENV=dev
LOG_LEVEL=INFO
DEBUG=false

MYSQL_ROOT_PASSWORD=root
MYSQL_DATABASE=rag
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_FAQ_TABLE=faq

MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=rag_docs

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384
EMBEDDING_BATCH_SIZE=32
CHUNK_SIZE=500
CHUNK_OVERLAP=80

OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1/
OPENAI_MODEL=qwen2.5:7b
OPENAI_MAX_OUTPUT_TOKENS=800
```

---

### 4. 启动本地模型（推荐 Ollama）

先拉模型：

```bash
ollama pull qwen2.5:7b
```

确认 Ollama 已启动后，可测试：

```bash
curl http://localhost:11434/api/generate \
  -d '{
    "model": "qwen2.5:7b",
    "prompt": "你好，介绍一下RAG",
    "stream": false
  }'
```

---

### 5. 重建索引

使用种子数据快速验证：

```bash
python scripts/reindex.py data/seed --drop-old
```

成功后你应该看到类似输出：

```text
加载文档数: 5
切分后 chunk 数: 5
已写入 Milvus chunk 数: 5
集合名: rag_docs
重建完成
```

---

### 6. 启动服务

```bash
uvicorn app.main:app --reload
```

---

### 7. 验证接口

#### 健康检查

```http
GET /health
```

#### 系统状态

```http
GET /admin/status
```

#### 查看 Milvus 样本

```http
GET /admin/milvus/sample
```

#### FAQ 查询示例

```http
POST /query
Content-Type: application/json

{
  "query": "什么是RAG",
  "top_k": 3
}
```

#### RAG 查询示例

```http
POST /query
Content-Type: application/json

{
  "query": "RAG为什么要先检索再生成答案",
  "top_k": 3
}
```

---

## 返回示例

```json
{
  "trace_id": "d108891c-cf07-4c63-a17f-7baf8bf90bb1",
  "query": "RAG为什么要先检索再生成答案",
  "answer": "RAG 先检索再生成答案的原因是：可以降低模型幻觉，并让回答更贴近企业私有知识。",
  "source": "rag",
  "route": "rag",
  "confidence": 0.8,
  "citations": [
    "faq-vs-rag#chunk-0",
    "rag-intro#chunk-0",
    "fallback-answer#chunk-0"
  ],
  "retrieved_docs": [
    {
      "doc_id": "faq-vs-rag#chunk-0",
      "score": 0.44566601514816284,
      "snippet": "FAQ 更适合固定问题和固定答案，通常使用精确匹配、模糊匹配或规则命中。RAG 更适合开放问题，需要从文档中检索上下文后再生成回答。FAQ 和 RAG 可以组合：先查 FAQ，FAQ 未命中时再回退到 RAG。"
    }
  ]
}
```

---

## 当前已验证结果

- FAQ 链路可用
- MySQL 连接稳定
- Milvus 检索可用
- `reindex` 可用
- 本地 Ollama 模型可生成答案
- `/query` 已打通最小完整 RAG 闭环
- generation 层已按职责拆分为：
  - `prompt_builder`
  - `answer_postprocess`
  - `llm_client`

---

## 当前限制

当前项目仍然是**最小可用原型**，还存在以下限制：

- FAQ 仍为精确匹配
- `IntentRouter` 仍是最小规则版
- `HybridRetriever` 目前本质上还是向量检索主导
- 尚未接入 BM25 / RRF / rerank
- Redis 仍未接入
- 测试、评估、配置分层还未完善

---

## 工程化方向

项目中已补充大量 `TODO`，后续可按模块逐步推进：

- `scripts/reindex.py`
- `app/indexing/`
- `app/retrieval/`
- `app/generation/`
- `app/router/`

推荐推进顺序：

1. 离线索引链路优化
2. 检索决策层优化
3. 混合检索能力补齐
4. generation 质量增强
5. 测试 / 评估 / 缓存工程化

---

## 开发记录

详细开发过程见：

- `Record.md`
- `roadmap.md`

---

## 下一阶段重点

- 实现 `threshold_policy.py`
- 接入 `bm25_retriever.py`
- 升级 `HybridRetriever`
- 实现 RRF 融合
- 补 rerank
- 增加 Redis 缓存层
- 完善 tests / eval / configs

---

## 当前结论

这个项目已经从最初的 mock 原型，演进成了一个：

> **可索引、可检索、可生成、可观测** 的最小 RAG 系统

下一步重点不再是盲目堆功能，而是：

> **补齐检索决策层、混合检索能力与工程化完善。**
