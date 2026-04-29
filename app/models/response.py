from dataclasses import dataclass

"""
  #### 查询结果模型

  - RetrievedDoc
  - GeneratedAnswer
"""

# TODO 将其升级为 Pydantic 的 BaseModel

@dataclass
class  RetrievedDoc:

    # TODO 后续扩充 metadata: dict 字段,把页码、章节、文件来源 URL 塞进去
    
    doc_id: str
    score: float
    snippet: str
    # matadata: json
     
@dataclass
class GeneratedAnswer:
    text: str
    citations: list[str]
    model: str # 不同模型间进行 A/B 测试或者平滑迁移时，这个字段能帮你追踪到：这条答案到底是哪个模型生成的。