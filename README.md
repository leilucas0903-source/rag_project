## 项目目标
构建一个生产级、可观测、高性能的 RAG（检索增强生成）系统。

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
- [ ] 接入 MySQL FAQ 检索
- [ ] 接入 Milvus 向量检索
- [ ] 实现 RRF 混合重排算法