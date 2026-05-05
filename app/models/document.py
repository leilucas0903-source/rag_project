from dataclasses import dataclass
"""
  #### 索引文档模型

  - SourceDocument
  - DocumentChunk
"""


@dataclass
class SourceDocument:
    """
    - title
    - metadata
    - tags
    - section
    - source_type
    """
    doc_id: str
    text: str
    source: str


@dataclass
class DocumentChunk:
    """
    - title
    - metadata
    - tags
    - section
    - source_type
    """
    chunk_id: str
    text: str
    source: str
