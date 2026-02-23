import json
import logging
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any, Final

_REQUEST_ID_CONTEXT: ContextVar[str | None] = ContextVar("sift_request_id", default=None)

_DEFAULT_REDACT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "set-cookie",
        "session_id",
        "session_token",
        "content",
        "content_text",
        "content_html",
        "payload",
    }
)

_RESERVED_RECORD_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }
)

_LOG_LEVEL_BY_NAME: Final[dict[str, int]] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

_APPLIED_LOG_CONFIG: tuple[str, str, str, str, tuple[str, ...]] | None = None


def bind_request_id(request_id: str) -> Token[str | None]:
    return _REQUEST_ID_CONTEXT.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _REQUEST_ID_CONTEXT.reset(token)


def get_request_id() -> str | None:
    return _REQUEST_ID_CONTEXT.get()


def configure_logging(
    *,
    service: str,
    env: str,
    level: str,
    log_format: str,
    redact_fields: list[str],
) -> None:
    global _APPLIED_LOG_CONFIG

    normalized_level = level.strip().upper() if level.strip() else "INFO"
    normalized_format = log_format.strip().lower() if log_format.strip() else "json"
    normalized_redact_fields = tuple(sorted({item.strip().lower() for item in redact_fields if item.strip()}))
    signature = (service, env, normalized_level, normalized_format, normalized_redact_fields)
    if _APPLIED_LOG_CONFIG == signature:
        return

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(_LOG_LEVEL_BY_NAME.get(normalized_level, logging.INFO))

    handler = logging.StreamHandler()
    if normalized_format == "json":
        redact_set = set(_DEFAULT_REDACT_FIELDS)
        redact_set.update(normalized_redact_fields)
        handler.setFormatter(JsonLogFormatter(service=service, env=env, redact_fields=redact_set))
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
        )
    root_logger.addHandler(handler)

    _APPLIED_LOG_CONFIG = signature


class JsonLogFormatter(logging.Formatter):
    def __init__(self, *, service: str, env: str, redact_fields: set[str]) -> None:
        super().__init__()
        self._service = service
        self._env = env
        self._redact_fields = {field.lower() for field in redact_fields}

    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", record.getMessage())
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "service": self._service,
            "env": self._env,
            "event": str(event),
            "message": record.getMessage(),
        }

        extras = _extract_record_extras(record)
        request_id = extras.get("request_id")
        if request_id is None:
            context_request_id = get_request_id()
            if context_request_id is not None:
                extras["request_id"] = context_request_id

        for key, value in extras.items():
            payload[key] = self._redact_value(key=key, value=value)

        if record.exc_info is not None:
            exception_value = record.exc_info[1]
            payload.setdefault("error_type", type(exception_value).__name__)
            payload.setdefault("error_message", str(exception_value))

        return json.dumps(payload, separators=(",", ":"), default=str)

    def _redact_value(self, *, key: str, value: Any) -> Any:
        normalized_key = key.strip().lower()
        if normalized_key in self._redact_fields:
            return "[REDACTED]"
        return value


def _extract_record_extras(record: logging.LogRecord) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    for key, value in record.__dict__.items():
        if key in _RESERVED_RECORD_ATTRS or key.startswith("_"):
            continue
        extras[key] = value
    return extras

