from dataclasses import dataclass
from enum import Enum

"""
  #### 查询决策模型

  - Intent
  - RetrievalStrategy
  - RouteDecision
"""



# TODO 将其升级为 Pydantic 的 BaseModel

class Intent(str,Enum): 
    FAQ = 'faq'                # FAQ: Frequently Asked Questions
    KNOWLEDGE = 'knowledge'

class RetrievalStrategy(str,Enum): #当你继承 Enum 时，Python 自动把你定义里的所有类属性（如 RAG）都转换成了一个对象（Instance）
    DIRECT_FAQ = "direct_faq"      #若不继承str，则输出: <enum 'MyEnum'> (它不是字符串，它是 MyEnum 这个枚举类的一个实例)
    RAG = "rag"

@dataclass  
class RouteDecision:    # if decision.confidence > 0.95: ...
    intent:Intent        # Python 的 “委托” (Delegation) 和 “混入” (Mixin)
    strategy:RetrievalStrategy
    confidence:float  
    direct_answer:str | None = None