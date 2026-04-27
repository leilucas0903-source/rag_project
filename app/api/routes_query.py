from fastapi import APIRouter, Request

from app.api.schemas import QueryRequest, QueryResponse, DocItem
from app.router.intent_router import IntentRouter
from app.models.query import RetrievalStrategy
from app.retrieval.hybrid_retriever import HybridRetriever
from app.generation.llm_client import LLMClient

router = APIRouter(tags=["query"])

intent_router = IntentRouter()
retriever = HybridRetriever()
llm = LLMClient()


@router.post("/query", response_model=QueryResponse)
def query_api(req: QueryRequest, request: Request):
    
    trace_id = getattr(request.state, "request_id", "-")
    decision = intent_router.route(req.query)

    if decision.strategy == RetrievalStrategy.DIRECT_FAQ and decision.direct_answer:
        return QueryResponse(
            trace_id=trace_id,
            query=req.query,
            answer=decision.direct_answer,
            source="faq",
            route=decision.strategy.value,
            confidence=decision.confidence,
            citations=[],
            retrieved_docs=[],
        )

    docs = retriever.retrieve(req.query, req.top_k)
    ans = llm.generator(req.query, docs)

    return QueryResponse(
        trace_id=trace_id,
        query=req.query,
        answer=ans.text,
        source="rag",
        route=decision.strategy.value,
        confidence=decision.confidence,
        citations=ans.citations,
        retrieved_docs=[
            DocItem(doc_id=d.doc_id, score=float(d.score), snippet=d.snippet) for d in docs
        ],
    )
