rag_project/
├─ app/
│    ├─ main.py  ✅应用入口与装配层    
      初始化日志；注册中间件（请求日志、指标采集）；注册全局异常处理；挂载 /metrics；提供 /health 健康检查。
│    ├─ api/  
│    │  ├─ routes_query.py
│    │  ├─ routes_admin.py
│    │  └─ schemas.py

│    ├─ core/    ✅
│    │  ├─ config.py    #统一配置源
│    │  ├─ logger.py    #统一日志格式与输出通道
         通过 RequestIdFilter 给日志补 request_id；配置 console + file 双输出；格式统一；可接管 uvicorn 日志写入同一文件。
│    │  └─ metrics.py   #指标定义层

│    ├─ middleware/  ✅
│    │  ├─ request_context.py
│    │  ├─ request_logger.py    #请求日志中间件
│    │  └─ metrics_middleware.py    #请求指标中间件

│    ├─ handlers/   ✅
│    │  └─ error_handler.py     #统一异常出口

│    ├─ models/
│    │  ├─ document.py
│    │  ├─ query.py
│    │  └─ response.py

│    ├─ router/
│    │  ├─ intent_router.py
│    │  └─ threshold_policy.py

│    ├─ retrieval/
│    │  ├─ mysql_faq_retriever.py
│    │  ├─ bm25_retriever.py
│    │  ├─ milvus_retriever.py
│    │  ├─ hybrid_retriever.py
│    │  └─ reranker.py

│    ├─ generation/
│    │  ├─ prompt_builder.py
│    │  ├─ llm_client.py
│    │  └─ answer_postprocess.py

│    ├─ indexing/
│    │  ├─ loaders.py
│    │  ├─ splitter.py
│    │  ├─ embedding_worker.py
│    │  └─ milvus_upsert.py

│    ├─ cache/
│    │  ├─ redis_cache.py
│    │  └─ cache_keys.py

│    ├─ eval/
│    │  ├─ dataset.py
│    │  ├─ offline_eval.py
│    │  └─ online_eval.py

│    └─ tests/
│       ├─ test_api.py
│       ├─ test_router.py
│       ├─ test_retrieval.py
│       └─ test_generation.py

├─ scripts/
│  ├─ reindex.py
│  ├─ warmup_cache.py
│  └─ replay_logs.py

├─ configs/
│  ├─ config.dev.yaml
│  ├─ config.prod.yaml
│  └─ prompts.yaml

├─ requirements.txt

└─ README.md
