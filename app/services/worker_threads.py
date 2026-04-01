import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Coroutine, Any, Optional

from app.services.logger import get_logger

logger = get_logger(__name__, level="INFO")


class AsyncWorker:
    """
    Background async worker running in its own event loop thread.
    """

    def __init__(self, max_workers: int = 5):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._start_loop,
            daemon=True,
            name="AsyncWorkerLoop",
        )
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._started = False

    def start(self) -> None:
        if not self._started:
            logger.info("Starting async worker thread")
            self._thread.start()
            self._started = True

    def _start_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.set_default_executor(self._executor)
        self._loop.run_forever()

    def submit(
        self,
        coro: Coroutine[Any, Any, Any],
        wait: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[Any]:
        """
        Submit async coroutine to background loop.
        """
        if not self._started:
            raise RuntimeError("AsyncWorker not started. Call start().")

        future: Future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _on_done(f: Future) -> None:
            exc = f.exception()
            if exc is not None:
                logger.error(
                    f"[worker] Unhandled exception in background coroutine: {exc}",
                    exc_info=exc,
                )

        future.add_done_callback(_on_done)

        if wait:
            return future.result(timeout=timeout)

        return None

    def shutdown(self) -> None:
        logger.info("Shutting down async worker")
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._executor.shutdown(wait=True)


_worker: Optional[AsyncWorker] = None


def init_worker(max_workers: int = 5, force: bool = False) -> None:
    global _worker
    if force and _worker:
        logger.info("Forcing re-initialization of async worker")
        _worker.shutdown()
        _worker = None

    if _worker is None:
        _worker = AsyncWorker(max_workers=max_workers)
        _worker.start()


def submit_async(
    coro: Coroutine[Any, Any, Any],
    wait: bool = False,
    timeout: Optional[float] = None,
) -> Optional[Any]:
    if _worker is None:
        raise RuntimeError("Worker not initialized. Call init_worker().")
    return _worker.submit(coro, wait=wait, timeout=timeout)


def shutdown_worker() -> None:
    global _worker
    if _worker:
        _worker.shutdown()
        _worker = None


def submit_task(func: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Submit a synchronous function to the background executor.
    """
    if _worker is None:
        raise RuntimeError("Worker not initialized. Call init_worker().")

    logger.info(f"Submitting background task: {func.__name__}")
    _worker._executor.submit(func, *args, **kwargs)