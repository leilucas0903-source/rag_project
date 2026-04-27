from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logger import setup_logger

from app.handlers.error_handler import register_exception_handlers
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware
from app.api.routes_query import router as query_router

# 注册了哪些中间件？挂了哪些路由？异常处理在哪接入？

def create_app() -> FastAPI:

    setup_logger()

    app = FastAPI(title=settings.app_name,debug=settings.debug)
    @app.middleware("http")
    async def ensure_utf8_json(request, call_next):
        resp = await call_next(request)
        ct = resp.headers.get("content-type", "")
        if ct.startswith("application/json") and "charset" not in ct:
            resp.headers["content-type"] = "application/json; charset=utf-8"
        return resp

    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(MetricsMiddleware)

    register_exception_handlers(app)
    app.mount("/metrics", make_asgi_app())

    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.app_env}

    return app

app = create_app()
app.include_router(query_router)