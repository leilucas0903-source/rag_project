from app.models.query import Intent,RetrievalStrategy,RouteDecision

FAQ_MAP = {
    "你是谁": "我是你的RAG助手。",
    "系统健康吗": "系统当前健康。"
}

class IntentRouter:
    def route(self,query:str) -> RouteDecision:
        q = query.strip()
        if q in FAQ_MAP:
            return RouteDecision(
                intent=Intent.FAQ,
                strategy=RetrievalStrategy.DIRECT_FAQ,
                confidence=0.95,
                direct_answer=FAQ_MAP[q]
            )
        return RouteDecision(
            intent=Intent.KNOWLEDGE,
            strategy=RetrievalStrategy.RAG,
            confidence=0.60,
            direct_answer=None,
        )
    