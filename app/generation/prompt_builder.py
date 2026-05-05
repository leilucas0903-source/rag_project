from __future__ import annotations

from app.models.response import RetrievedDoc


def build_context(query: str, docs: list[RetrievedDoc]) -> str:
    del query  # 当前上下文仅由检索结果构成，先保留签名便于后续扩展。
    return "\n\n".join([f"[文档 {doc.doc_id.strip()}]\n{doc.snippet}" for doc in docs])


def build_prompt(query: str, docs: list[RetrievedDoc]) -> tuple[str, str]:
    context = build_context(query, docs)

    # TODO: 后续将 prompt 文案抽到配置文件，并按 FAQ / RAG / admin 等场景分开维护。
    instructions = (
        "你是一个 RAG 问答助手。"
        "只能基于提供的检索资料回答。"
        "如果资料不足，就明确说不知道，不要编造。"
        "回答尽量简洁直接。"
    )
    user_input = f"用户问题：{query}\n\n检索资料：\n{context}"
    return instructions, user_input
