import logging
import os
import signal
from threading import Event

from app.db import close_engine
from app.services.indexing_jobs import IndexingRunWorker


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    stop_event = Event()

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    poll_interval = max(0.1, float(os.getenv("INDEX_WORKER_POLL_SECONDS", "1")))
    worker = IndexingRunWorker()
    logging.getLogger(__name__).info("Indexing worker started")
    try:
        worker.run_forever(stop_event, poll_interval=poll_interval)
    finally:
        close_engine()
        logging.getLogger(__name__).info("Indexing worker stopped")


if __name__ == "__main__":
    main()
