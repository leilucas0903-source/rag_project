from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(3, ge=1, le=10)


class DocItem(BaseModel):
    doc_id: str
    score: float
    snippet: str


class QueryResponse(BaseModel):
    trace_id: str
    query: str
    answer: str
    source: str
    route: str
    confidence: float
    citations: list[str] = Field(default_factory=list)
    retrieved_docs: list[DocItem] = Field(default_factory=list)
