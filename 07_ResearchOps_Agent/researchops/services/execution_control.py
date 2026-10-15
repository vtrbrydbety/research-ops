"""One shared, fixed-size execution scheduler for every public model operation."""

from concurrent.futures import Future, TimeoutError
from dataclasses import replace
from queue import Queue
from threading import Lock, Thread

from researchops.core.access_context import current_access
from researchops.services.access_store import AccessError, AccessStore


class ExecutionController:
    def __init__(self, store: AccessStore):
        self.store = store
        self.queue = Queue(
            maxsize=store.settings.execution_concurrency + store.settings.execution_queue_size
        )
        self._lock = Lock()
        self._started = False

    def submit(self, function, *, prepare=None):
        context = current_access.get()
        if context is None:
            raise RuntimeError("Public execution requires a trusted principal")
        operation = self.store.reserve(context.principal)
        future = Future()
        try:
            if prepare:
                prepare(operation)
            with self._lock:
                if not self._started:
                    for index in range(self.store.settings.execution_concurrency):
                        Thread(
                            target=self._worker, daemon=True, name=f"researchops-worker-{index}"
                        ).start()
                    self._started = True
                self.queue.put_nowait(
                    (operation, replace(context, operation=operation), function, future)
                )
        except BaseException:
            self.store.finish(operation, "failed")
            raise
        return operation, future

    def run(self, function):
        _, future = self.submit(function)
        config = self.store.settings
        try:
            return future.result(
                timeout=config.execution_queue_seconds + config.execution_timeout_seconds
            )
        except TimeoutError:
            # Do not release an execution slot while the underlying call is still running.
            raise AccessError("EXECUTION_TIMEOUT", "任务执行超时，请查询任务状态。", 504) from None

    def _worker(self):
        while True:
            operation, context, function, future = self.queue.get()
            marker = current_access.set(context)
            try:
                self.store.start(operation)
                result = function()
                self.store.check_operation(operation)
                self.store.finish(operation)
                future.set_result(result)
            except BaseException as exc:
                try:
                    self.store.finish(operation, "failed")
                except Exception:
                    # Never reopen a slot in the persistent ledger if storage failed.
                    pass
                future.set_exception(exc)
            finally:
                current_access.reset(marker)
                self.queue.task_done()


def controller(context=None):
    context = context or current_access.get()
    if context is None:
        return None
    store = context.store
    # Creation is called from concurrent API worker threads.
    with _creation_lock:
        if not hasattr(store, "execution_controller"):
            store.execution_controller = ExecutionController(store)
        return store.execution_controller


def run_controlled(function):
    executor = controller()
    return executor.run(function) if executor else function()


_creation_lock = Lock()
