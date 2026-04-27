import logging
from logging.config import dictConfig
from pathlib import Path
from app.core.config import settings


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logger() -> None:
    log_dir = getattr(settings, "log_dir", "logs")
    log_file = getattr(settings, "log_file", "app.log")
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id_filter": {"()": RequestIdFilter}
            },
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(Path(log_dir) / log_file),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                    "encoding": "utf-8",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": settings.log_level.upper(),
            },
        }
    )

    # 让 uvicorn 日志走 root，统一进入文件
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
