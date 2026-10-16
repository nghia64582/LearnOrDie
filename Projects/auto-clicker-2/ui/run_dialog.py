from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from engine.runner import RunEvent, WorkflowRunner
from models.image_library import ImageLibrary
from models.workflow import Workflow

COUNTDOWN_SECONDS = 3


class RunDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        workflow: Workflow,
        library: ImageLibrary,
        on_event: Callable[[RunEvent], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.title(f"Chạy: {workflow.name}")
        self.geometry("560x420")
        self.minsize(480, 360)
        self.transient(master.winfo_toplevel())
        self.attributes("-topmost", True)

        self._workflow = workflow
        self._library = library
        self._on_event = on_event
        self._on_close = on_close
        self._queue: queue.Queue[RunEvent] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._countdown = COUNTDOWN_SECONDS
        self._closed = False

        self.protocol("WM_DELETE_WINDOW", self._request_close)
        self._build()
        self.after(400, self._tick_countdown)
        self.after(120, self._drain_queue)

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(
            self,
            text="Chuyển sang cửa sổ cần thao tác. Đưa chuột lên góc trên-trái để dừng khẩn cấp.",
            wraplength=520,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        self._status = ttk.Label(self, text=f"Bắt đầu sau {self._countdown}s…", font=("Segoe UI", 11, "bold"))
        self._status.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        self._log = tk.Text(self, height=16, wrap="word", state="disabled")
        self._log.grid(row=2, column=0, sticky="nsew", padx=12)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self._log.yview)
        scroll.grid(row=2, column=1, sticky="ns", pady=0, padx=(0, 8))
        self._log.configure(yscrollcommand=scroll.set)

        buttons = ttk.Frame(self)
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        self._stop_btn = ttk.Button(buttons, text="Dừng", command=self._stop_run)
        self._stop_btn.pack(side="left")
        self._close_btn = ttk.Button(buttons, text="Đóng", command=self._request_close, state="disabled")
        self._close_btn.pack(side="right")

        self._append(f"Chuẩn bị chạy workflow \"{self._workflow.name}\" ({len(self._workflow.steps)} bước).")

    def _tick_countdown(self) -> None:
        if self._closed or self._stop.is_set():
            self._finish_ui("Đã hủy trước khi chạy.", enable_close=True)
            return
        if self._countdown > 0:
            self._status.configure(text=f"Bắt đầu sau {self._countdown}s…")
            self._append(f"Đếm ngược: {self._countdown}")
            self._countdown -= 1
            self.after(1000, self._tick_countdown)
            return
        self._status.configure(text="Đang chạy…")
        self._append("Bắt đầu thực thi.")
        self._thread = threading.Thread(target=self._run_worker, daemon=True)
        self._thread.start()

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
        if self._closed:
            return
        while True:
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
        self.after(120, self._drain_queue)

    def _handle_event(self, event: RunEvent) -> None:
        self._append(event.message)
        if event.kind == "step_started":
            self._status.configure(text=event.message)
        elif event.kind == "finished":
            self._finish_ui("Hoàn thành.", enable_close=True)
        elif event.kind == "cancelled":
            self._finish_ui("Đã dừng.", enable_close=True)
        elif event.kind == "failed":
            self._finish_ui("Thất bại.", enable_close=True)
        self._on_event(event)

    def _stop_run(self) -> None:
        self._stop.set()
        self._stop_btn.configure(state="disabled")
        self._status.configure(text="Đang dừng…")
        self._append("Yêu cầu dừng.")

    def _finish_ui(self, status: str, enable_close: bool) -> None:
        self._status.configure(text=status)
        self._stop_btn.configure(state="disabled")
        if enable_close:
            self._close_btn.configure(state="normal")

    def _request_close(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._stop.set()
            self._append("Đang dừng trước khi đóng cửa sổ…")
            self.after(200, self._request_close)
            return
        self._closed = True
        self._on_close()
        self.destroy()

    def _append(self, message: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", message + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")
