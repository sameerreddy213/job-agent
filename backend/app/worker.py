"""job-agent worker — runs the discovery scheduler (Phase 2+)."""
from .logging_config import configure_logging
from .scheduler import start


def main() -> None:
    configure_logging(service="worker")
    start()


if __name__ == "__main__":
    main()
