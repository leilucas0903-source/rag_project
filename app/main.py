from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.api.routes_admin import router as admin_router
from app.api.routes_query import router as query_router
from app.core.config import settings
from app.core.logger import setup_logger
from app.handlers.error_handler import register_exception_handlers
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware


def create_app() -> FastAPI:
    setup_logger()

    app = FastAPI(title=settings.app_name, debug=settings.debug)

    @app.middleware("http")
    async def ensure_utf8_json(request, call_next):
        # TODO: 后续可把这类通用响应头处理抽成独立中间件，避免 create_app 继续膨胀。
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
        # TODO: 后续将 /health 区分为 liveness / readiness，并补外部依赖探活结果。
        return {"status": "ok", "env": settings.app_env}

    # TODO: 后续使用 FastAPI lifespan 做启动自检、模型预热、连接准备。
    return app


app = create_app()
app.include_router(admin_router)
app.include_router(query_router)
