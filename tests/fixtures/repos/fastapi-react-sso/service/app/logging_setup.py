"""Structured JSON logs with a request ID on every line."""

import contextvars
import json
import logging
import uuid

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "request_id": request_id.get(),
            }
        )


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def new_request_id(incoming: str | None) -> str:
    value = incoming or uuid.uuid4().hex
    request_id.set(value)
    return value
