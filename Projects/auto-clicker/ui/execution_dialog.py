"""Dialog displaying live execution progress and logs for a running workflow."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from engine.executor import WorkflowExecutor
from models.workflow import Workflow
from storage.image_repository import ImageRepository


class ExecutionDialog(tk.Toplevel):
    """Modal/Toplevel window monitoring workflow execution with live logs and stop control."""

    def __init__(
        self,
        parent: tk.Widget,
        workflow: Workflow,
        image_repo: ImageRepository,
    ) -> None:
        super().__init__(parent)
        self.workflow = workflow
        self.image_repo = image_repo

        self.title(f"Running: {workflow.workflow.name}")
        self.geometry("680x480")
        self.minsize(500, 350)
        self.transient(parent)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initialize and start executor
        self.executor = WorkflowExecutor(
            workflow=self.workflow,
            image_repo=self.image_repo,
            on_log=self._on_log,
            on_finish=self._on_finish,
        )
        self.executor.start()

    def _build_ui(self) -> None:
        # Header banner
        header = ttk.Frame(self, padding=(14, 10))
        header.pack(fill=tk.X, side=tk.TOP)

        self.lbl_status = ttk.Label(
            header,
            text=f"▶ Running '{self.workflow.workflow.name}'...",
            font=("Segoe UI", 12, "bold"),
            foreground="#1976d2",
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.btn_stop = ttk.Button(header, text="⏹ Stop", command=self._on_stop)
        self.btn_stop.pack(side=tk.RIGHT, padx=(6, 0))

        # Log text area
        log_frame = ttk.Frame(self, padding=(14, 0, 14, 10))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#e0e0e0",
            insertbackground="#ffffff",
            font=("Consolas", 10),
            padx=8,
            pady=8,
        )
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom actions
        bottom_frame = ttk.Frame(self, padding=(14, 8))
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.btn_close = ttk.Button(
            bottom_frame, text="Close", command=self._on_close, state=tk.DISABLED
        )
        self.btn_close.pack(side=tk.RIGHT)

    def _on_log(self, message: str) -> None:
        def append() -> None:
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)

        self.after(0, append)

    def _on_finish(self, success: bool, final_msg: str) -> None:
        def update_ui() -> None:
            if success:
                self.lbl_status.configure(
                    text=f"✔ Finished: {final_msg}", foreground="#2e7d32"
                )
            else:
                self.lbl_status.configure(
                    text=f"❌ Finished: {final_msg}", foreground="#d32f2f"
                )
            self.btn_stop.configure(state=tk.DISABLED)
            self.btn_close.configure(state=tk.NORMAL)

        self.after(0, update_ui)

    def _on_stop(self) -> None:
        self.executor.stop()
        self.btn_stop.configure(state=tk.DISABLED)

    def _on_close(self) -> None:
        if self.executor.is_running:
            self.executor.stop()
        self.destroy()
