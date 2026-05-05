from app.models.response import GeneratedAnswer, RetrievedDoc


def normalize_citations(docs: list[RetrievedDoc]) -> list[str]:
    citations: list[str] = []
    seen: set[str] = set()

    for doc in docs:
        doc_id = doc.doc_id.strip()
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        citations.append(doc_id)

    return citations


def clean_answer_text(text: str | None) -> str:
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return ""

    lines = [line.strip() for line in raw.split("\n")]
    cleaned_lines: list[str] = []
    prev_blank = False

    for line in lines:
        if not line:
            if prev_blank:
                continue
            cleaned_lines.append("")
            prev_blank = True
            continue

        cleaned_lines.append(line)
        prev_blank = False

    return "\n".join(cleaned_lines).strip()


def postprocess_no_context(docs: list[RetrievedDoc]) -> GeneratedAnswer:
    return GeneratedAnswer(
        text="未检索到相关资料，暂时无法基于知识库回答这个问题。",
        citations=normalize_citations(docs),
        model="no-context",
    )


def postprocess_no_llm(docs: list[RetrievedDoc], context: str) -> GeneratedAnswer:
    return GeneratedAnswer(
        text="未配置可用的 LLM，当前返回检索到的资料片段：\n\n" + clean_answer_text(context),
        citations=normalize_citations(docs),
        model="fallback-no-openai",
    )


def postprocess_llm_success(
    docs: list[RetrievedDoc],
    raw_text: str | None,
    model: str,
    context: str,
) -> GeneratedAnswer:
    text = clean_answer_text(raw_text)
    if not text:
        return GeneratedAnswer(
            text="LLM 返回空答案，当前返回检索到的资料片段：\n\n" + clean_answer_text(context),
            citations=normalize_citations(docs),
            model="fallback-empty-answer",
        )

    # TODO: 后续补答案长度控制、引用插入策略、以及更细的输出质量校验。
    return GeneratedAnswer(
        text=text,
        citations=normalize_citations(docs),
        model=model,
    )


def postprocess_llm_error(docs: list[RetrievedDoc], context: str) -> GeneratedAnswer:
    return GeneratedAnswer(
        text="LLM 调用失败，当前返回检索到的资料片段：\n\n" + clean_answer_text(context),
        citations=normalize_citations(docs),
        model="fallback-llm-error",
    )
