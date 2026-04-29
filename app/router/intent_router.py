from app.models.query import Intent, RetrievalStrategy, RouteDecision
class IntentRouter:
    def route(self, query: str) -> RouteDecision:
        q = query.strip()
        # Day2 Step1: 这里只保留轻量路由判断，不再直接返回 FAQ 内容
        if len(q) <= 20:
            return RouteDecision(
                intent=Intent.FAQ,
                strategy=RetrievalStrategy.DIRECT_FAQ,
                confidence=0.80,
                direct_answer=None,
            )
        return RouteDecision(
            intent=Intent.KNOWLEDGE,
            strategy=RetrievalStrategy.RAG,
            confidence=0.60,
            direct_answer=None,
        )