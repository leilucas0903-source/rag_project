from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(
            "http_exception status=%s detail=%s",
            exc.status_code,
            exc.detail,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": str(exc.detail),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        logger.exception(
            "unhandled_exception: %s",
            str(exc),
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal Server Error",
                "request_id": request_id,
            },
        )
