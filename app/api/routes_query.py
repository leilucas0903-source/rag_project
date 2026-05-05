from fastapi import APIRouter, Request

from app.api.schemas import DocItem, QueryRequest, QueryResponse
from app.core.logger import get_logger
from app.generation.llm_client import LLMClient
from app.models.query import RetrievalStrategy
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever
from app.router.intent_router import IntentRouter

logger = get_logger(__name__)

router = APIRouter(tags=["query"])

# TODO: 后续改成依赖注入或 service 层，避免模块级单例在测试和扩展时变得难控制。
intent_router = IntentRouter()
faq_retriever = MysqlFAQRetriever()
llm = LLMClient()
retriever = HybridRetriever()


@router.post("/query", response_model=QueryResponse)
def query_api(req: QueryRequest, request: Request):
    trace_id = getattr(request.state, "request_id", "-")
    decision = intent_router.route(req.query)

    logger.info(f"[{trace_id}] Query: {req.query} | Route Strategy: {decision.strategy}")

    if decision.strategy == RetrievalStrategy.DIRECT_FAQ:
        faq_hit = faq_retriever.retrieve(req.query)
        if faq_hit:
            return QueryResponse(
                trace_id=trace_id,
                query=req.query,
                answer=faq_hit.answer,
                source="faq",
                route=decision.strategy.value,
                confidence=faq_hit.score,
                citations=[faq_hit.faq_id],
                retrieved_docs=[],
            )

    # TODO: 后续补查询编排层，统一处理 FAQ 未命中、RAG 检索、生成、降级策略。
    docs = retriever.retrieve(req.query, req.top_k)
    ans = llm.generator(req.query, docs)

    return QueryResponse(
        trace_id=trace_id,
        query=req.query,
        answer=ans.text,
        source="rag",
        route=RetrievalStrategy.RAG.value,
        confidence=decision.confidence,
        citations=ans.citations,
        retrieved_docs=[
            DocItem(
                doc_id=d.doc_id,
                score=float(d.score),
                snippet=d.snippet,
            )
            for d in docs
        ],
    )
