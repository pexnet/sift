import time

from sift.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"[scheduler] starting with redis={settings.redis_url}")
    print("[scheduler] TODO: schedule feed polling and maintenance jobs")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()

