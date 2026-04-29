from fastapi import APIRouter, Request

from app.api.schemas import QueryRequest, QueryResponse, DocItem
from app.router.intent_router import IntentRouter
from app.models.query import RetrievalStrategy
from app.retrieval.hybrid_retriever import HybridRetriever
from app.generation.llm_client import LLMClient
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["query"])

intent_router = IntentRouter()
faq_retriever = MysqlFAQRetriever()
retriever = HybridRetriever()
llm = LLMClient()


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
                snippet=d.snippet
            )for d in docs 
        ],
    )
