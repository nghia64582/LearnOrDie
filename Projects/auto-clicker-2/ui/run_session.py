from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable

from engine.runner import RunEvent, WorkflowRunner
from models.image_library import ImageLibrary
from models.workflow import Workflow

COUNTDOWN_SECONDS = 3


class RunSession:
    """Chạy một workflow nền (không mở cửa sổ/popup).

    Đếm ngược COUNTDOWN_SECONDS giây để người dùng chuyển sang cửa sổ cần
    thao tác, rồi chạy WorkflowRunner trên thread riêng. Sự kiện được đưa
    về main thread qua queue và báo lại bằng callback.
    """

    def __init__(
        self,
        master: tk.Misc,
        workflow: Workflow,
        library: ImageLibrary,
        on_event: Callable[[RunEvent], None],
        on_countdown: Callable[[int], None],
        on_started: Callable[[], None],
        on_close: Callable[[], None],
    ) -> None:
        self._master = master
        self._workflow = workflow
        self._library = library
        self._on_event = on_event
        self._on_countdown = on_countdown
        self._on_started = on_started
        self._on_close = on_close
        self._queue: queue.Queue[RunEvent] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._countdown = COUNTDOWN_SECONDS
        self._closed = False

        self._master.after(0, self._tick_countdown)

    @property
    def active(self) -> bool:
        return not self._closed

    def stop(self) -> None:
        self._stop.set()

    def _tick_countdown(self) -> None:
        if self._stop.is_set():
            self._on_event(RunEvent("cancelled", "Đã hủy trước khi chạy."))
            self._close()
            return
        if self._countdown > 0:
            self._on_countdown(self._countdown)
            self._countdown -= 1
            self._master.after(1000, self._tick_countdown)
            return
        self._on_started()
        self._thread = threading.Thread(target=self._run_worker, daemon=True)
        self._thread.start()
        self._master.after(120, self._drain_queue)

    def _run_worker(self) -> None:
        runner = WorkflowRunner(
            self._workflow,
            self._library,
            should_stop=self._stop.is_set,
            emit=self._queue.put,
        )
        try:
            runner.run()
        except Exception as exc:
            self._queue.put(RunEvent("failed", str(exc)))

    def _drain_queue(self) -> None:
        while True:
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                break
            self._on_event(event)
        if self._thread is not None and self._thread.is_alive():
            self._master.after(120, self._drain_queue)
            return
        # Thread đã xong: lấy nốt sự kiện còn lại rồi kết thúc phiên chạy
        while not self._queue.empty():
            self._on_event(self._queue.get_nowait())
        self._close()

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._on_close()
