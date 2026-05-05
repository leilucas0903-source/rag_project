from typing import List

from openai import OpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.generation.answer_postprocess import (
    postprocess_llm_error,
    postprocess_llm_success,
    postprocess_no_context,
    postprocess_no_llm,
)
from app.generation.prompt_builder import build_context, build_prompt
from app.models.response import GeneratedAnswer, RetrievedDoc

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.api_key = settings.openai_api_key.strip()
        self.base_url = settings.openai_base_url.strip()
        self.model = settings.openai_model
        self.max_output_tokens = settings.openai_max_output_tokens
        self.client = None

        if self.api_key:
            kwargs = {"api_key": self.api_key}
            if self.base_url and (
                self.base_url.startswith("http://") or self.base_url.startswith("https://")
            ):
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)

    def generator(self, query: str, docs: List[RetrievedDoc]) -> GeneratedAnswer:
        if not docs:
            return postprocess_no_context(docs)

        context = build_context(query, docs)
        if not self.client:
            return postprocess_no_llm(docs, context)

        instructions, user_input = build_prompt(query, docs)

        try:
            # TODO: 后续补 timeout、重试次数、模型路由与请求 tracing。
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=user_input,
                max_output_tokens=self.max_output_tokens,
            )
            return postprocess_llm_success(docs, response.output_text, self.model, context)
        except Exception as e:
            # TODO: 后续补更细的错误分类、重试策略和超时控制。
            logger.warning(f"LLM generation failed, fallback to retrieved docs: {e}")
            return postprocess_llm_error(docs, context)
