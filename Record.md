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
