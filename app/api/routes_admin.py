from fastapi import APIRouter

from app.core.config import settings
from app.retrieval.milvus_retriever import MilvusRetriever
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
def admin_status():
    # TODO: 后续为 admin 路由补鉴权，避免运维信息直接暴露。
    result = {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "embedding_model": settings.embedding_model,
        "mysql": {"ok": False},
        "milvus": {"ok": False},
    }

    try:
        result["mysql"] = MysqlFAQRetriever().health_status()
    except Exception as e:
        result["mysql"] = {
            "ok": False,
            "error": str(e),
        }

    try:
        result["milvus"] = MilvusRetriever().health_status()
    except Exception as e:
        result["milvus"] = {
            "ok": False,
            "error": str(e),
        }

    return result


@router.get("/milvus/sample")
def milvus_sample(limit: int = 5):
    # TODO: 后续将 limit 提取为 schema 参数，并补返回脱敏 / 截断策略。
    retriever = MilvusRetriever()
    return {
        "collection": settings.milvus_collection,
        "limit": limit,
        "items": retriever.sample_documents(limit=max(1, min(limit, 20))),
    }
