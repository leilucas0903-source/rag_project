# Project Record

## Day 1

### [Step 1] 主链路骨架完成

- 时间：2026-04-28
- 目标：先跑通 `/query` 的最小主链路，具备 FAQ 直返和 RAG 回退骨架。
- 变更内容：
  - 搭建 FastAPI 应用入口与基础目录结构。
  - 增加 `/health` 健康检查接口。
  - 增加请求日志中间件，记录 `request_id`、耗时、状态码。
  - 增加指标中间件与统一异常处理。
  - 增加 `IntentRouter`、`HybridRetriever`、`LLMClient` 的最小链路。
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_query.py`
  - `app/router/intent_router.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/generation/llm_client.py`
  - `app/middleware/request_logger.py`
  - `app/middleware/metrics_middleware.py`
  - `app/handlers/error_handler.py`
- 当前结果：
  - `/query` 主链路代码可运行。
  - FAQ 命中可直接返回，未命中可进入 RAG 骨架。
- 验证方式：
  - 本地联调 `/query`
  - 检查日志输出与 `/health`
- 下一步：
  - 拆出 FAQ 检索器，替换硬编码 FAQ。

## Day 2

### [Step 1] 拆分 FAQ 检索职责

- 时间：2026-04-28
- 目标：将 FAQ 问答能力从路由层拆出，形成独立 FAQ 检索器。
- 变更内容：
  - 新增 `MysqlFAQRetriever`，封装 FAQ 查询接口。
  - 新增 `FAQHit` 结构，统一 FAQ 命中结果。
  - 将 `IntentRouter` 从“直接返回 FAQ 内容”调整为“只负责路由判断”。
  - 在 `/query` 主链路中接入 FAQ 检索。
- 涉及文件：
  - `app/retrieval/mysql_faq_retriever.py`
  - `app/router/intent_router.py`
  - `app/api/routes_query.py`
- 当前结果：
  - FAQ 命中逻辑已从路由层剥离。
  - 主链路职责更清晰。
- 验证方式：
  - FAQ 问题优先命中 FAQ 检索器。
  - 非 FAQ 问题继续走 RAG 路径。
- 下一步：
  - 将 FAQ 数据源接到真实 MySQL。

### [Step 2] FAQ 检索器接入 MySQL 查询骨架

- 时间：2026-04-28
- 目标：把 FAQ 检索从 mock 升级成真实数据库访问骨架。
- 变更内容：
  - 在 `config.py` 中增加 MySQL FAQ 相关配置。
  - 将 `MysqlFAQRetriever` 改为访问 MySQL。
  - FAQ 查询策略先采用精确匹配。
- 涉及文件：
  - `app/core/config.py`
  - `app/retrieval/mysql_faq_retriever.py`
- 当前结果：
  - FAQ 数据源已切到 MySQL。
  - 为后续真实 FAQ 维护预留了接口。
- 验证方式：
  - 在 MySQL 中准备 FAQ 测试数据。
  - 请求 FAQ 问题并确认返回数据库结果。
- 下一步：
  - 接入向量检索，补齐 RAG 链路。

### [架构补充] 同步 I/O 策略评估与异步升级计划

- 时间：2026-04-28
- 背景：当前 `/query`、`MysqlFAQRetriever` 先以同步实现满足低并发联调。
- 当前判断：
  - 本地开发与演示阶段，同步实现成本更低。
  - 随着 Milvus 与 LLM 调用接入，外部 I/O 会增加，同步模式会逐渐成为瓶颈。
- 风险点：
  - MySQL 每次请求新建连接，存在重复连接开销。
  - Milvus / LLM 持续用同步调用会影响并发能力。
- 结论：
  - 当前阶段先不强制异步化。
  - 后续真实外部 I/O 接入后，再评估 `async` 改造时机。
- 后续升级项：
  - `/query` 改为 `async def`
  - FAQ / Milvus / LLM 逐步异步化
  - 引入连接复用或连接池

### [环境准备] FAQ MySQL 数据表初始化

- 时间：2026-04-28
- 目标：为 FAQ 检索准备 MySQL 数据源。
- 变更内容：
  - 设计 `rag.faq` 表结构。
  - 准备 FAQ 初始化数据。
- 验证方式：
  - 直接 SQL 查询 `faq` 表。
  - 验证关键 FAQ 问题是否可精确命中。
- 下一步：
  - 完成 Docker 化部署并接通应用访问。

### [环境准备] MySQL Docker Compose 方案

- 时间：2026-04-28
- 目标：通过 Docker Compose 启动 MySQL，并自动初始化 FAQ 数据表。
- 变更内容：
  - 设计 `docker-compose.yml` 中的 MySQL 服务。
  - 暴露宿主机端口供本地 Python 应用访问。
  - 挂载初始化 SQL 目录。
- 配置约定：
  - 数据库：`rag`
  - FAQ 表：`faq`
  - 宿主机连接：`127.0.0.1:3307`
- 下一步：
  - 启动 MySQL 并验证 FAQ 表初始化。

## Day 3

### [Step 3] 接入 Milvus 向量检索

- 时间：2026-04-29
- 目标：将 RAG 链路从 mock 检索升级为真实向量检索。
- 变更内容：
  - 新增 `MilvusRetriever`，封装向量检索能力。
  - 增加 Milvus 相关配置项。
  - 将 `HybridRetriever` 改为调用 `MilvusRetriever`。
- 涉及文件：
  - `app/retrieval/milvus_retriever.py`
  - `app/core/config.py`
  - `app/retrieval/hybrid_retriever.py`
- 当前结果：
  - RAG 检索层具备真实向量检索骨架。
- 验证方式：
  - 启动 Milvus 容器并准备测试数据。
  - 请求非 FAQ 问题，确认能检索到文档。
- 下一步：
  - 完善真实 embedding 与索引链路。

### [环境准备] Milvus Docker Compose 配置

- 时间：2026-04-29
- 目标：为向量检索准备完整 Docker 环境。
- 变更内容：
  - 在 `docker-compose.yml` 中增加 `etcd`、`minio`、`milvus-standalone` 服务。
  - 配置依赖关系、健康检查、端口与数据卷。
- 配置约定：
  - Milvus：`19530`
  - MinIO：`9000 / 9001`
- 下一步：
  - 启动 Milvus 服务栈并验证健康状态。

### [测试验证] Milvus 服务健康性检查

- 时间：2026-04-29
- 目标：确认 Milvus 服务栈可用。
- 变更内容：
  - 通过 Compose 启动服务。
  - 编写 / 执行基础测试脚本验证连接与集合操作。
- 涉及文件：
  - `docker-compose.yml`
  - `test_milvus.py`
- 验证方式：
  - `docker compose ps`
  - `curl http://localhost:9091/healthz`
  - Python 连接测试
- 下一步：
  - 接入真实 embedding 与入库流程。

### [P0-1] 编码链路与 FAQ / Milvus 数据核验脚本

- 时间：2026-04-29
- 目标：定位乱码、FAQ 命中异常、Milvus 数据有效性问题。
- 变更内容：
  - 增加文本链路排查脚本。
  - 增加 FAQ 数据核验脚本。
  - 增加 Milvus 集合核验脚本。
- 涉及文件：
  - `scripts/check_text_chain.py`
  - `scripts/verify_mysql_faq_p0.py`
  - `scripts/verify_milvus_collection_p0.py`
- 当前结果：
  - 能独立判断乱码发生在源文件、入库链路、数据库存储还是日志显示。
- 下一步：
  - 修复 MySQL 字符集链路与脏数据。

### [P0-2] MySQL 字符集链路修正方案

- 时间：2026-04-29
- 目标：修正 FAQ 初始化链路中的字符集不一致问题，避免 UTF-8 中文被错误解释后写入 MySQL。
- 变更内容：
  - 统一应用、MySQL、初始化 SQL 的字符集链路。
  - 调整 `.env` / `docker-compose.yml` / 初始化 SQL 的相关配置。
- 涉及文件：
  - `app/core/config.py`
  - `docker-compose.yml`
  - `.env`
  - `.env.example`
  - `docker/mysql/init/001_init_faq.sql`
- 当前结果：
  - 新导入 FAQ 数据可以稳定按 UTF-8 入库。
- 下一步：
  - 删除旧库数据并重建 FAQ 数据。

### [P0-4] 修复 MySQL 连接环境问题

- 时间：2026-04-29
- 目标：修复 MySQL 容器反复重启、`test_sql.py` 无法连接、FAQ 初始化 SQL 无法正确执行的问题。
- 变更内容：
  - 修复 `.env` / `.env.example` 的格式问题。
  - 修复 `docker-compose.yml` 中 MySQL 容器的环境注入问题。
  - 修复 `docker/mysql/init/001_init_faq.sql` 的编码与 SQL 语法问题。
  - 重写 `test_sql.py`，提供干净的 MySQL 连通性验证。
- 涉及文件：
  - `.env`
  - `.env.example`
  - `docker-compose.yml`
  - `docker/mysql/init/001_init_faq.sql`
  - `test_sql.py`
- 当前结果：
  - MySQL 容器可正常启动。
  - `test_sql.py` 可连接并命中 FAQ 数据。
- 验证方式：
  - `docker compose config`
  - `docker compose down -v`
  - `docker compose up -d mysql`
  - `docker compose logs -f mysql`
  - `python test_sql.py`
- 下一步：
  - 继续推进 P1 的真实检索与生成链路。

### [P1-1] 接入最小真实索引链路与生成链路

- 时间：2026-04-29
- 目标：把随机向量检索与 mock 生成升级为最小可用的真实 RAG 主链路。
- 变更内容：
  - 在 `app/indexing/` 下补齐最小索引层：`loaders.py`、`splitter.py`、`embedding_worker.py`、`milvus_upsert.py`。
  - 新增 `scripts/reindex.py` 作为统一重建入口。
  - 将 `HybridRetriever` 改为真实 embedding 检索。
  - 将 `MilvusRetriever` 统一到配置维度。
  - 将 `LLMClient` 接入真实 OpenAI Responses API，并提供未配置密钥时的明确降级提示。
  - 扩展 embedding / chunk / OpenAI 相关配置。
- 涉及文件：
  - `app/core/config.py`
  - `app/indexing/__init__.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/embedding_worker.py`
  - `app/indexing/milvus_upsert.py`
  - `scripts/reindex.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/retrieval/milvus_retriever.py`
  - `app/generation/llm_client.py`
  - `requirements.txt`
- 当前结果：
  - 已具备最小文档入库链路。
  - 查询链路已升级为真实 embedding 检索。
  - 生成链路具备真实 LLM 接入能力。
- 验证方式：
  - `python scripts/reindex.py <input_path> --drop-old`
  - 配置 `OPENAI_API_KEY` 后请求 `/query`
- 下一步：
  - 准备真实文档并完成一次完整 reindex。

### [P1-2] 抽离离线索引流数据结构

- 时间：2026-04-29
- 目标：让离线索引链路中的文档数据结构从具体实现模块中解耦，形成清晰的内部模型边界。
- 变更内容：
  - 新增 `app/models/document.py`，统一承载 `SourceDocument` 与 `DocumentChunk`。
  - 调整 `app/indexing/loaders.py` 引用 `app.models.document`。
  - 调整 `app/indexing/splitter.py` 引用 `app.models.document`。 //纯字符计数切分
  - 调整 `app/indexing/milvus_upsert.py` 统一依赖 `DocumentChunk`。
- 涉及文件：
  - `app/models/document.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/milvus_upsert.py`
- 当前结果：
  - 在线查询流与离线索引流都具备明确的数据结构承载位置。
  - `schemas` 负责 API 边界，`models` 负责内部对象，`indexing / retrieval / generation` 负责处理逻辑。
- 验证方式：
  - `python -m py_compile app/models/document.py app/indexing/loaders.py app/indexing/splitter.py app/indexing/milvus_upsert.py`
  - `python scripts/reindex.py --help`
- 下一步：
  - 后续按需要扩展更细粒度的索引元数据模型。

## Day 4

### [P1-3] 增加最小管理观测接口，作为 RAG 下一阶段切入口

- 时间：2026-05-05
- 目标：在继续构建 RAG 主链路前，先补齐最小观测能力，明确 FAQ、Milvus、集合数据状态，避免后续开发过程“代码写了但不知道是否真的生效”。
- 变更内容：
  - 新增 `GET /admin/status`，统一暴露应用、FAQ、Milvus 的运行状态。
  - 新增 `GET /admin/milvus/sample`，用于抽样查看 Milvus 中的文档内容。
  - 为 `MysqlFAQRetriever` 增加 `health_status()`，返回 MySQL 连通性、FAQ 表存在性和 FAQ 数量。
  - 为 `MilvusRetriever` 增加 `health_status()`，返回 collection 状态和文档数量。
  - 为 `MilvusRetriever` 增加 `sample_documents()`，支持抽样查看当前集合中的 `id/text/source`。
  - 在 `app/main.py` 中挂载 `admin_router`。
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_admin.py`
  - `app/retrieval/mysql_faq_retriever.py`
  - `app/retrieval/milvus_retriever.py`
- 当前结果：
  - `/admin/status` 已可返回当前系统关键状态。
  - FAQ 链路状态明确：MySQL 正常、FAQ 表存在、FAQ 数量为 `6`。
  - Milvus 链路状态明确：`rag_docs` collection 已存在，但 `row_count = 0`，当前还没有正式文档入库。
  - 这说明 FAQ 已经跑通，但最小 RAG 主链路还卡在“知识库数据尚未完成入库”这一层。
- 当前状态快照：
  - `/admin/status` 返回：
    ```json
    {
      "app_name": "rag-project",
      "app_env": "dev",
      "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
      "mysql": {
        "ok": true,
        "host": "127.0.0.1",
        "port": 3307,
        "database": "rag",
        "table": "faq",
        "table_exists": true,
        "faq_count": 6
      },
      "milvus": {
        "ok": true,
        "host": "127.0.0.1",
        "port": 19530,
        "collection": "rag_docs",
        "collection_exists": true,
        "stats": {
          "row_count": 0
        },
        "doc_count": 0
      }
    }
    ```
- 验证方式：
  - 请求 `GET /admin/status`
  - 请求 `GET /admin/milvus/sample`
  - 检查返回中的 `faq_count`、`collection_exists`、`row_count`
- 下一步：
  - 准备最小测试文档并执行一次 `python scripts/reindex.py <input_path> --drop-old`
  - 先把 Milvus 中的 `row_count` 从 `0` 推进到“大于 0”
  - 然后再继续验证 `/query` 的向量检索链路

### [P1-4] 打通最小 RAG 闭环：本地 embedding 降级 + 种子数据入库 + 查询降级返回

- 时间：2026-05-05
- 目标：在不依赖外部模型下载、也不依赖真实 LLM 联网可用的前提下，先把最小 RAG 闭环打通。
- 变更内容：
  - 重写 `EmbeddingWorker`，增加本地降级 embedding：
    - 优先尝试本地缓存的 `SentenceTransformer`
    - 若本地模型不可用，则自动退化为纯本地哈希向量
  - 将 `SentenceTransformer` 调整为 `local_files_only=True`，避免请求时卡在 HuggingFace 下载重试。
  - 调整 `HybridRetriever`，对 query embedding 失败增加兜底保护，避免直接抛异常。
  - 修复 `MilvusUpserter`，在写入后补 `flush`，保证 `row_count` 能正确反映入库数量。
  - 新增 `data/seed/demo_knowledge.jsonl`，提供最小测试知识库数据。
  - 重写 `LLMClient`：
    - 当未配置可用 LLM 时，直接返回检索片段
    - 当 LLM 调用失败时，不再返回 500，而是降级返回检索片段
- 涉及文件：
  - `app/indexing/embedding_worker.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/indexing/milvus_upsert.py`
  - `app/generation/llm_client.py`
  - `data/seed/demo_knowledge.jsonl`
- 当前结果：
  - 已成功执行 `python scripts/reindex.py data/seed --drop-old`
  - 种子知识库成功写入 Milvus
  - `rag_docs` 当前 `row_count = 5`
  - 非 FAQ 问题已能走到 Milvus 检索
  - 即使 OpenAI 调用失败，`/query` 也会以 200 正常返回检索片段，不再直接报 500
- 验证方式：
  - `python scripts/reindex.py data/seed --drop-old`
  - 检查 `GET /admin/status` 中 `milvus.stats.row_count == 5`
  - 检查 `GET /admin/milvus/sample`
  - 使用非 FAQ 问题请求 `/query`，确认返回 `source = "rag"` 且带 `retrieved_docs`
- 验证结果：
  - 重建输出：
    - `加载文档数: 5`
    - `切分后 chunk 数: 5`
    - `已写入 Milvus chunk 数: 5`
  - Milvus 状态：
    - `collection_exists = true`
    - `row_count = 5`
    - `doc_count = 5`
  - `/query` 非 FAQ 验证：
    - 请求：`RAG为什么要先检索再生成答案`
    - 返回：HTTP `200`
    - 路由：`rag`
    - 结果：成功返回检索片段 fallback
- 下一步：
  - 用真实业务文档替换 `data/seed/demo_knowledge.jsonl`
  - 再做一次正式 reindex
  - 然后开始优化 FAQ 路由规则和检索效果

### [P1-5] 为后续优化点补充 TODO 注释

- 时间：2026-05-05
- 目标：把已经识别出的后续优化方向直接标在代码里，方便后续按模块逐步学习和逐步优化，避免遗忘。
- 变更内容：
  - 在 `MysqlFAQRetriever` 中补充 TODO：
    - 后续评估接入 MySQL 连接池
    - 后续把 FAQ 精确匹配升级为模糊匹配、全文检索或 FAQ 向量检索
  - 在 `scripts/reindex.py` 中补充 TODO：
    - 后续将 `batch_size` 做成参数或配置项
    - 后续增加 `tqdm / logging` 提升重建过程可观测性
  - 在 `MilvusUpserter` 中补充 TODO：
    - 当前每批写入后立即 `flush`
    - 后续可改为全部写完后统一 `flush` 提升性能
  - 在 `HybridRetriever` 中补充 TODO：
    - 后续补 BM25 / RRF / rerank，真正升级为 Hybrid Retrieval
  - 在 `LLMClient` 中补充 TODO：
    - 后续把 prompt 构造拆到 `prompt_builder`
    - 后续补更细的错误分类、重试和超时控制
  - 在 `IntentRouter` 中补充 TODO：
    - 当前仅按长度路由
    - 后续升级为关键词规则、FAQ 分数或小模型分类
- 涉及文件：
  - `app/retrieval/mysql_faq_retriever.py`
  - `scripts/reindex.py`
  - `app/indexing/milvus_upsert.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/generation/llm_client.py`
  - `app/router/intent_router.py`
- 当前结果：
  - 代码中已经明确标出后续优化切入点。
  - 后续可以按模块逐个学习，而不用一次记住全部优化方向。
- 验证方式：
  - 直接查看上述文件中的 `TODO` 注释
  - 执行基础语法检查，确认仅补注释未引入新问题
- 下一步：
  - 按模块逐个消化 TODO
  - 优先从 `scripts/reindex.py` 和 `app/indexing/milvus_upsert.py` 开始学习离线入库链路

### [P1-6] 修正 Milvus 查询层职责边界，移除自动建空集合行为

- 时间：2026-05-05
- 目标：避免在线查询模块在 collection 缺失时悄悄创建空集合，导致“索引缺失”被伪装成“检索无结果”。
- 变更内容：
  - 移除 `MilvusRetriever.__init__()` 中的自动建集合逻辑。
  - 删除查询层中的 `_ensure_collection()` 行为。
  - 新增 `_require_collection()`，在查询前强制检查 collection 是否存在。
  - 当 collection 不存在时，直接抛出明确错误：
    - `Milvus collection '<name>' 不存在，请先执行 reindex 初始化知识库。`
- 涉及文件：
  - `app/retrieval/milvus_retriever.py`
- 当前结果：
  - 查询模块不再具备“创建空集合”的能力。
  - collection 丢失时，问题会被立即暴露，而不是继续返回空结果。
  - Milvus 的职责边界更清晰：
    - 查询层只负责查
    - 建集合仍由离线入库链路负责
- 验证方式：
  - 查看 `app/retrieval/milvus_retriever.py`
  - 语法检查：
    - `python -m py_compile app/retrieval/milvus_retriever.py`
- 下一步：
  - 后续继续学习离线入库链路与查询链路的职责边界
  - 保持“在线查询不做初始化、离线链路负责准备资源”的原则

### [P1-7] 拆分 generation 层职责：prompt / postprocess / client

- 时间：2026-05-05
- 目标：把 `LLMClient` 中混在一起的 prompt 构造、答案包装、模型调用职责拆开，按 `generation/` 目录结构落地。
- 变更内容：
  - 实现 `app/generation/prompt_builder.py`
    - 新增 `build_context()`
    - 新增 `build_prompt()`
    - 负责把 `query + docs` 组装成 `instructions` 和 `input`
  - 实现 `app/generation/answer_postprocess.py`
    - 新增 `build_citations()`
    - 新增无上下文、无 LLM、LLM 成功、LLM 失败四类标准答案构造函数
  - 重写 `app/generation/llm_client.py`
    - `LLMClient` 只负责 client 初始化与模型调用
    - 调用 `prompt_builder` 构造 prompt
    - 调用 `answer_postprocess` 统一返回 `GeneratedAnswer`
  - 保持 `routes_query.py` 的调用方式不变，仍然使用：
    - `ans = llm.generator(req.query, docs)`
- 涉及文件：
  - `app/generation/prompt_builder.py`
  - `app/generation/answer_postprocess.py`
  - `app/generation/llm_client.py`
- 当前结果：
  - generation 层职责边界更清晰：
    - `prompt_builder` 负责 prompt
    - `llm_client` 负责调用
    - `answer_postprocess` 负责标准化输出
  - 上层查询接口无需改调用方式
  - LLM 失败时仍可正常降级返回检索片段
- 验证方式：
  - 语法检查：
    - `python -m py_compile app/generation/prompt_builder.py app/generation/answer_postprocess.py app/generation/llm_client.py`
  - 最小调用验证：
    - 构造 `RetrievedDoc`
    - 调用 `LLMClient().generator(...)`
    - 确认可返回 `GeneratedAnswer`
- 下一步：
  - 后续继续细化 `prompt_builder`
  - 再按需要补 `answer_postprocess` 的引用整理与输出清洗

### [P1-8] 修正 answer_postprocess 职责，落实为真正的“结果后处理”

- 时间：2026-05-05
- 目标：让 `answer_postprocess.py` 从“答案装配器”回归为真正的后处理模块，负责清洗文本、整理引用、处理空答案和统一 fallback。
- 变更内容：
  - 重写 `app/generation/answer_postprocess.py`
    - 新增 `normalize_citations()`：去空、去重、清理 `doc_id`
    - 新增 `clean_answer_text()`：统一换行、去掉多余空行、清理空白
    - 新增 `postprocess_no_context()`：处理无检索结果场景
    - 新增 `postprocess_no_llm()`：处理无可用 LLM 场景
    - 新增 `postprocess_llm_success()`：处理正常生成结果，并对空答案做二次兜底
    - 新增 `postprocess_llm_error()`：处理 LLM 调用失败场景
  - 调整 `app/generation/llm_client.py`
    - 不再自己构造各种答案对象
    - 统一调用 `answer_postprocess` 返回 `GeneratedAnswer`
  - 微调 `app/generation/prompt_builder.py`
    - 在上下文展示时对 `doc_id` 做 `strip()`，避免 fallback 文本里出现脏引用
- 涉及文件：
  - `app/generation/answer_postprocess.py`
  - `app/generation/llm_client.py`
  - `app/generation/prompt_builder.py`
- 当前结果：
  - `answer_postprocess.py` 的职责更贴合命名本身。
  - generation 层边界进一步清晰：
    - `prompt_builder` 负责组织输入
    - `llm_client` 负责模型调用
    - `answer_postprocess` 负责结果规范化
  - 空答案、脏 citation、LLM 失败 fallback 都有统一落点。
- 验证方式：
  - `python -m py_compile app/generation/answer_postprocess.py app/generation/llm_client.py app/generation/prompt_builder.py`
  - 构造最小 `RetrievedDoc`，调用 `LLMClient().generator(...)`
  - 检查：
    - `citations` 是否去重并去空白
    - fallback 文本中的 `doc_id` 是否已清理
- 下一步：
  - 后续继续增强 `answer_postprocess`
  - 再视需要补输出长度控制、引用展示格式和答案质量校验

### [P1-9] 全项目补工程化 TODO，建立后续优化主线

- 时间：2026-05-05
- 目标：先不继续扩功能，而是把当前项目中已经识别出的工程化优化点系统性标到代码里，作为后续逐模块学习和演进的入口。
- 变更内容：
  - 在 `app/main.py` 中补 TODO：
    - `lifespan` 启动自检
    - `/health` 区分 `liveness/readiness`
    - 通用响应头处理中间件抽离
  - 在 `app/api/routes_query.py` 中补 TODO：
    - 模块级单例改依赖注入 / service 层
    - 查询编排层抽离
  - 在 `app/api/routes_admin.py` 中补 TODO：
    - admin 鉴权
    - 返回脱敏 / 截断
  - 在 `app/router/intent_router.py` 中补 TODO：
    - 抽 `threshold_policy`
    - 升级路由决策逻辑
  - 在 `app/retrieval/` 中补 TODO：
    - `bm25_retriever.py` 明确 BM25 落地方向
    - `milvus_retriever.py` 补 metadata、错误分类、调试接口优化
    - `hybrid_retriever.py` 标出 BM25 / RRF / rerank 后续接入点
  - 在 `app/indexing/` 中补 TODO：
    - embedding 预热与 fallback 替换
    - loader 的 doc_id 冲突与 metadata 扩展
    - splitter 的语义切分与 offset metadata
    - Milvus upsert 的统一 flush、幂等、去重
  - 在 `app/generation/` 中补 TODO：
    - prompt 配置化
    - answer 后处理增强
    - LLM timeout / retry / tracing
  - 在 `scripts/reindex.py` 中补 TODO：
    - `batch_size` 参数化
    - `tqdm / logging / dry-run`
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_query.py`
  - `app/api/routes_admin.py`
  - `app/router/intent_router.py`
  - `app/retrieval/bm25_retriever.py`
  - `app/retrieval/milvus_retriever.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/indexing/embedding_worker.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/milvus_upsert.py`
  - `app/generation/prompt_builder.py`
  - `app/generation/answer_postprocess.py`
  - `app/generation/llm_client.py`
  - `scripts/reindex.py`
- 当前结果：
  - 项目主要模块都已有明确的工程化切入口。
  - 后续可以按模块逐步推进，而不是零散地临时想到哪里改哪里。
  - TODO 已覆盖应用装配、API、路由、检索、索引、生成、脚本等主干路径。
- 验证方式：
  - 直接查看上述文件中的 `TODO` 注释
  - 对修改文件执行基础语法检查，确认仅补注释未破坏代码结构
- 下一步：
  - 优先从 `scripts/reindex.py`、`app/indexing/`、`app/retrieval/` 这条主链开始逐个消化 TODO
  - 按“先离线入库、再在线检索、最后生成优化”的顺序继续推进
