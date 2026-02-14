from rq import Worker

from sift.config import get_settings
from sift.tasks.queueing import get_ingest_queue, get_redis_connection


def main() -> None:
    settings = get_settings()
    print(f"[worker] starting with redis={settings.redis_url}")
    queue = get_ingest_queue()
    worker = Worker([queue], connection=get_redis_connection())
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()

