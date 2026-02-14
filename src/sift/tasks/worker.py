from sift.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"[worker] starting with redis={settings.redis_url}")
    print("[worker] TODO: initialize RQ worker queues and handlers")


if __name__ == "__main__":
    main()

