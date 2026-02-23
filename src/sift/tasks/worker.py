import logging

from rq import Worker

from sift.config import get_settings
from sift.observability.logging import configure_logging
from sift.observability.metrics_server import start_metrics_http_server
from sift.tasks.queueing import get_ingest_queue, get_redis_connection

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(
        service="sift-worker",
        env=settings.env,
        level=settings.log_level,
        log_format=settings.log_format,
        redact_fields=settings.log_redact_fields,
    )
    metrics_server = start_metrics_http_server(
        service_name="sift-worker",
        enabled=settings.observability_enabled and settings.metrics_enabled,
        host=settings.metrics_bind_host,
        port=settings.metrics_worker_port,
        path=settings.metrics_path,
    )
    logger.info(
        "worker.process.start",
        extra={
            "event": "worker.process.start",
            "redis_url": settings.redis_url,
            "queue_name": settings.ingest_queue_name,
            "metrics_host": metrics_server.host if metrics_server else None,
            "metrics_port": metrics_server.port if metrics_server else None,
            "metrics_path": metrics_server.path if metrics_server else None,
        },
    )
    queue = get_ingest_queue()
    worker = Worker([queue], connection=get_redis_connection())
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
