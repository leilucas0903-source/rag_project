

from typing import List

from openai import OpenAI

from app.core.config import settings
from app.models.response import GeneratedAnswer, RetrievedDoc

"""
  - client 初始化
  - 发送请求
  - 返回原始模型结果或最小标准结果
"""

class LLMClient:
    def __init__(self):
        self.api_key = settings.openai_api_key.strip()
        self.base_url = settings.openai_base_url.strip()
        self.model = settings.openai_model
        self.max_output_tokens = settings.openai_max_output_tokens
        self.client = None

        if self.api_key:
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)

    def generator(self, query: str, docs: List[RetrievedDoc]) -> GeneratedAnswer:
        citations = [d.doc_id for d in docs]
        if not docs:
            return GeneratedAnswer(
                text="未检索到相关资料，暂时无法基于知识库回答这个问题。",
                citations=citations,
                model="no-context",
            )

        context = "\n\n".join(
            [f"[文档 {doc.doc_id}]\n{doc.snippet}" for doc in docs]
        )

        if not self.client:
            return GeneratedAnswer(
                text="未配置 OPENAI_API_KEY，当前仅返回检索到的资料片段：\n\n" + context,
                citations=citations,
                model="fallback-no-openai",
            )

        response = self.client.responses.create(
            model=self.model,
            instructions=(
                "你是一个RAG问答助手。"
                "只能基于提供的检索资料回答。"
                "如果资料不足，就明确说不知道，不要编造。"
                "回答尽量简洁、直接。"
            ),
            input=f"用户问题：{query}\n\n检索资料：\n{context}",
            max_output_tokens=self.max_output_tokens,
        )

        return GeneratedAnswer(
            text=response.output_text.strip(),
            citations=citations,
            model=self.model,
        )
