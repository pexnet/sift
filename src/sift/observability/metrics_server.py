import logging
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from sift.observability.metrics import get_observability_metrics

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MetricsServerHandle:
    host: str
    port: int
    path: str
    server: ThreadingHTTPServer
    thread: Thread

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)


def _normalize_metrics_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not path:
        return "/metrics"
    if path.startswith("/"):
        return path
    return f"/{path}"


def start_metrics_http_server(
    *,
    service_name: str,
    enabled: bool,
    host: str,
    port: int,
    path: str,
    extra_renderers: list[Callable[[], str]] | None = None,
) -> MetricsServerHandle | None:
    if not enabled:
        return None

    normalized_path = _normalize_metrics_path(path)
    renderers = list(extra_renderers or [])

    class MetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != normalized_path:
                self.send_response(404)
                self.end_headers()
                return

            payload = get_observability_metrics().render_prometheus()
            for renderer in renderers:
                payload += renderer()
            body = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            # Keep HTTP server internals from writing unstructured stderr lines.
            return

    server = ThreadingHTTPServer((host, port), MetricsHandler)
    thread = Thread(target=server.serve_forever, name=f"{service_name}-metrics", daemon=True)
    thread.start()
    server_address = server.server_address
    bound_host = str(server_address[0])
    bound_port = int(server_address[1])
    logger.info(
        "metrics.server.start",
        extra={
            "event": "metrics.server.start",
            "service": service_name,
            "bind_host": bound_host,
            "bind_port": bound_port,
            "path": normalized_path,
        },
    )
    return MetricsServerHandle(
        host=bound_host,
        port=bound_port,
        path=normalized_path,
        server=server,
        thread=thread,
    )
