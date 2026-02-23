import json
import logging

from sift.observability.logging import JsonLogFormatter, bind_request_id, reset_request_id


def test_json_log_formatter_redacts_sensitive_fields() -> None:
    formatter = JsonLogFormatter(
        service="sift-api",
        env="test",
        redact_fields={"password", "authorization", "content_text"},
    )
    record = logging.makeLogRecord(
        {
            "name": "test.logger",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "message",
            "event": "test.event",
            "password": "supersecret",
            "authorization": "Bearer token",
            "content_text": "body",
            "safe_value": "ok",
        }
    )

    payload = json.loads(formatter.format(record))
    assert payload["password"] == "[REDACTED]"
    assert payload["authorization"] == "[REDACTED]"
    assert payload["content_text"] == "[REDACTED]"
    assert payload["safe_value"] == "ok"


def test_json_log_formatter_uses_bound_request_id_when_missing_from_record() -> None:
    formatter = JsonLogFormatter(service="sift-api", env="test", redact_fields=set())
    token = bind_request_id("req-bound-123")
    try:
        record = logging.makeLogRecord(
            {
                "name": "test.logger",
                "levelno": logging.INFO,
                "levelname": "INFO",
                "msg": "message",
                "event": "test.event",
            }
        )
        payload = json.loads(formatter.format(record))
    finally:
        reset_request_id(token)

    assert payload["request_id"] == "req-bound-123"


def test_json_log_formatter_redaction_is_case_insensitive() -> None:
    formatter = JsonLogFormatter(service="sift-api", env="test", redact_fields={"session_token"})
    record = logging.makeLogRecord(
        {
            "name": "test.logger",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "message",
            "event": "test.event",
            "Session_Token": "abc123",
        }
    )

    payload = json.loads(formatter.format(record))
    assert payload["Session_Token"] == "[REDACTED]"

