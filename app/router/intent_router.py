from app.models.query import Intent, RetrievalStrategy, RouteDecision


class IntentRouter:
    def route(self, query: str) -> RouteDecision:
        q = query.strip()

        # TODO: 当前仅按长度做最小路由；后续抽到 threshold_policy，
        # TODO: 并结合 FAQ 命中分数、关键词规则或小模型分类一起决策。
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
