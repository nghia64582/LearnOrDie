from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from engine.runner import RunEvent, validate_workflow
from models.image_library import ImageLibrary
from models.step import Step, StepType
from models.workflow import Workflow
from models.workflow_store import WorkflowStore
from ui.run_session import COUNTDOWN_SECONDS, RunSession
from ui.step_editor import StepEditor
from ui.toast import Toast
from ui.workflow_canvas import WorkflowCanvas

# Toast lỗi hiển thị lâu hơn toast thường (ms)
ERROR_TOAST_MS = 8000


class WorkflowsTab(ttk.Frame):
    def __init__(self, master: tk.Misc, store: WorkflowStore, library: ImageLibrary) -> None:
        super().__init__(master, padding=12)
        self.store = store
        self.library = library
        self._current: Workflow | None = None
        self._selected_step_id: str | None = None
        self._saving = False
        self._run_session: RunSession | None = None
        self._toast: Toast | None = None
        self._run_current_id: str | None = None
        self._run_failed_id: str | None = None
        self._run_completed: set[str] = set()
        self._build()
        self.refresh_list()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Danh sách workflow", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.tree = ttk.Treeview(
            left,
            columns=("name", "steps"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="Tên")
        self.tree.heading("steps", text="Số bước")
        self.tree.column("name", width=180, stretch=True)
        self.tree.column("steps", width=70, stretch=False, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._on_workflow_select())

        scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        list_buttons = ttk.Frame(left)
        list_buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(list_buttons, text="Thêm", command=self.add_workflow).pack(side="left")
        ttk.Button(list_buttons, text="Đổi tên", command=self.rename_workflow).pack(side="left", padx=6)
        ttk.Button(list_buttons, text="Xóa", command=self.delete_workflow).pack(side="left")

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        header = ttk.Frame(right)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Tên:").grid(row=0, column=0, sticky="w")
        self._name_var = tk.StringVar()
        self._name_entry = ttk.Entry(header, textvariable=self._name_var)
        self._name_entry.grid(row=0, column=1, sticky="ew", padx=8)
        self._name_var.trace_add("write", lambda *_: self._on_name_changed())
        self._status = ttk.Label(header, text="", foreground="#667085")
        self._status.grid(row=0, column=2, padx=(0, 8))
        ttk.Button(header, text="Lưu", command=self.save_current).grid(row=0, column=3)

        body = ttk.Panedwindow(right, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew")

        canvas_wrap = ttk.Frame(body)
        canvas_wrap.rowconfigure(0, weight=1)
        canvas_wrap.columnconfigure(0, weight=1)
        self.canvas = WorkflowCanvas(canvas_wrap, on_select=self.select_step)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        canvas_scroll = ttk.Scrollbar(canvas_wrap, orient="vertical", command=self.canvas.yview)
        canvas_scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=canvas_scroll.set)

        editor_wrap = ttk.Frame(body, padding=(10, 0, 0, 0))
        editor_wrap.columnconfigure(0, weight=1)
        editor_wrap.rowconfigure(0, weight=1)
        self.editor = StepEditor(
            editor_wrap,
            self.library,
            on_change=self._on_step_changed,
            on_capture_point=self._capture_mouse,
        )
        self.editor.grid(row=0, column=0, sticky="nsew")

        body.add(canvas_wrap, weight=1)
        body.add(editor_wrap, weight=1)

        tools = ttk.Frame(right)
        tools.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(tools, text="Thêm bước:").pack(side="left")
        self._new_type_var = tk.StringVar(value=StepType.CLICK_IMAGE.label)
        ttk.Combobox(
            tools,
            textvariable=self._new_type_var,
            values=[item.label for item in StepType],
            state="readonly",
            width=16,
        ).pack(side="left", padx=(6, 8))
        ttk.Button(tools, text="Thêm bước", command=self.add_step).pack(side="left")
        ttk.Button(tools, text="Lên", command=lambda: self.move_step(-1)).pack(side="left", padx=(12, 0))
        ttk.Button(tools, text="Xuống", command=lambda: self.move_step(1)).pack(side="left", padx=6)
        ttk.Button(tools, text="Xóa bước", command=self.delete_step).pack(side="left")
        self._run_btn = ttk.Button(tools, text="Chạy", command=self.run_workflow)
        self._run_btn.pack(side="right")
        # Trạng thái chạy hiển thị ngay trên tab (dòng riêng), thay cho cửa sổ popup
        self._run_status = ttk.Label(right, text="", foreground="#667085")
        self._run_status.grid(row=3, column=0, sticky="e", pady=(6, 0))

    def refresh_images(self) -> None:
        self.library.reload()
        if self._current is not None:
            self._render_editor()

    def refresh_list(self, select_id: str | None = None) -> None:
        selected = select_id or self._selected_workflow_id()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for workflow in self.store.all():
            self.tree.insert(
                "",
                "end",
                iid=workflow.id,
                values=(workflow.name, len(workflow.steps)),
            )
        if selected and self.tree.exists(selected):
            chosen = selected
        elif self.tree.get_children():
            chosen = self.tree.get_children()[0]
        else:
            chosen = None

        if chosen is None:
            self._load_workflow(None)
            return

        self.tree.selection_set(chosen)
        self.tree.focus(chosen)
        if self._current is None or self._current.id != chosen:
            self._load_workflow(self.store.get(chosen))

    def add_workflow(self) -> None:
        name = simpledialog.askstring("Thêm workflow", "Tên workflow:", parent=self)
        if name is None:
            return
        cleaned = name.strip()
        if not cleaned:
            messagebox.showerror("Thêm workflow", "Tên không được để trống.", parent=self)
            return
        workflow = Workflow.create(cleaned)
        self.store.save(workflow)
        self.refresh_list(select_id=workflow.id)

    def rename_workflow(self) -> None:
        workflow = self._current
        if workflow is None:
            messagebox.showinfo("Đổi tên", "Hãy chọn một workflow trước.", parent=self)
            return
        name = simpledialog.askstring(
            "Đổi tên workflow",
            "Tên mới:",
            initialvalue=workflow.name,
            parent=self,
        )
        if name is None:
            return
        cleaned = name.strip()
        if not cleaned:
            messagebox.showerror("Đổi tên", "Tên không được để trống.", parent=self)
            return
        workflow.name = cleaned
        self.store.save(workflow)
        self._saving = True
        self._name_var.set(cleaned)
        self._saving = False
        self.refresh_list(select_id=workflow.id)

    def delete_workflow(self) -> None:
        workflow = self._current
        if workflow is None:
            messagebox.showinfo("Xóa workflow", "Hãy chọn một workflow trước.", parent=self)
            return
        confirmed = messagebox.askyesno(
            "Xóa workflow",
            f'Xóa workflow "{workflow.name}"?',
            parent=self,
        )
        if not confirmed:
            return
        self.store.delete(workflow.id)
        self._current = None
        self._selected_step_id = None
        self.refresh_list()

    def save_current(self) -> bool:
        if self._current is None:
            return False
        self.editor.apply_current()
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("Lưu", "Tên workflow không được để trống.", parent=self)
            return False
        self._current.name = name
        self.store.save(self._current)
        self._status.configure(text="Đã lưu")
        self.refresh_list(select_id=self._current.id)
        return True

    def add_step(self) -> None:
        if self._current is None:
            messagebox.showinfo("Thêm bước", "Hãy tạo hoặc chọn một workflow trước.", parent=self)
            return
        step_type = next(
            (item for item in StepType if item.label == self._new_type_var.get()),
            StepType.CLICK_IMAGE,
        )
        step = Step.create(step_type)
        index = None
        if self._selected_step_id:
            current_index = next(
                (i for i, item in enumerate(self._current.steps) if item.id == self._selected_step_id),
                None,
            )
            if current_index is not None:
                index = current_index + 1
        self._current.add_step(step, index=index)
        self._selected_step_id = step.id
        self._persist_and_render()

    def move_step(self, offset: int) -> None:
        if self._current is None or not self._selected_step_id:
            return
        if self._current.move_step(self._selected_step_id, offset):
            self._persist_and_render()

    def delete_step(self) -> None:
        if self._current is None or not self._selected_step_id:
            messagebox.showinfo("Xóa bước", "Hãy chọn một bước trước.", parent=self)
            return
        step_id = self._selected_step_id
        remaining = [step.id for step in self._current.steps if step.id != step_id]
        self._current.remove_step(step_id)
        self._selected_step_id = remaining[-1] if remaining else None
        self._persist_and_render()

    def select_step(self, step_id: str) -> None:
        if self._current is None:
            return
        self.editor.apply_current()
        self._selected_step_id = step_id
        self._persist()
        self._render_editor()

    def run_workflow(self) -> None:
        if self._run_session is not None and self._run_session.active:
            # Nút "Chạy" thành "Dừng" khi đang chạy
            self._run_session.stop()
            self._run_btn.configure(state="disabled")
            self._set_run_status("Đang dừng…")
            return
        if self._current is None:
            messagebox.showinfo("Chạy workflow", "Hãy chọn một workflow trước.", parent=self)
            return
        if not self.save_current() or self._current is None:
            return
        snapshot = Workflow.from_dict(self._current.to_dict())
        errors = validate_workflow(snapshot, self.library)
        if errors:
            messagebox.showerror("Không chạy được", "\n".join(errors), parent=self)
            return
        self._run_completed = set()
        self._run_failed_id = None
        self._run_current_id = None
        self._run_btn.configure(text="Dừng")
        self._run_session = RunSession(
            self,
            snapshot,
            self.library,
            on_event=self._on_run_event,
            on_countdown=self._on_run_countdown,
            on_started=self._on_run_started,
            on_close=self._on_run_close,
        )

    def _on_run_countdown(self, seconds: int) -> None:
        text = f"Bắt đầu sau {seconds}s… Chuyển sang cửa sổ cần thao tác."
        self._set_run_status(text)
        if seconds == COUNTDOWN_SECONDS:
            self._show_toast(
                f'Chạy "{self._current.name if self._current else ""}" sau {seconds}s.\n'
                "Dừng khẩn cấp: đưa chuột lên góc trên-trái màn hình.",
                duration_ms=0,
            )

    def _on_run_started(self) -> None:
        # Đóng toast trước khi bắt đầu click để không che màn hình/ảnh mẫu
        self._hide_toast()
        self._set_run_status("Đang chạy…")

    def _set_run_status(self, text: str, error: bool = False) -> None:
        self._run_status.configure(text=text, foreground="#b42318" if error else "#667085")

    def _show_toast(self, text: str, kind: str = "info", duration_ms: int = 3000) -> None:
        self._hide_toast()
        self._toast = Toast(self, text, kind=kind, duration_ms=duration_ms)

    def _hide_toast(self) -> None:
        if self._toast is not None and self._toast.winfo_exists():
            self._toast.dismiss()
        self._toast = None

    def _on_run_event(self, event: RunEvent) -> None:
        if event.kind == "step_started":
            self._set_run_status(event.message)
        elif event.kind == "finished":
            self._set_run_status("Hoàn thành.")
            self._show_toast(event.message, kind="success")
        elif event.kind == "cancelled":
            self._set_run_status(event.message)
            self._show_toast(event.message)
        elif event.kind == "failed":
            # Lỗi vẫn hiển thị rõ: nhãn đỏ giữ đến lần chạy sau + toast đỏ lâu hơn
            self._set_run_status(event.message, error=True)
            self._show_toast(event.message, kind="error", duration_ms=ERROR_TOAST_MS)
        if event.kind == "step_started" and event.step_id:
            self._run_current_id = event.step_id
            self._selected_step_id = event.step_id
        elif event.kind == "step_success" and event.step_id:
            self._run_completed.add(event.step_id)
            self._run_current_id = None
        elif event.kind == "failed":
            self._run_failed_id = event.step_id or self._run_current_id
            self._run_current_id = None
        elif event.kind == "cancelled":
            self._run_current_id = None
        self._render_canvas()

    def _on_run_close(self) -> None:
        self._run_session = None
        self._run_current_id = None
        self._run_btn.configure(text="Chạy", state="normal")
        self._render_canvas()

    def _on_workflow_select(self) -> None:
        workflow_id = self._selected_workflow_id()
        if not workflow_id:
            return
        if self._current is not None and self._current.id == workflow_id:
            return
        loaded = self.store.get(workflow_id)
        self._load_workflow(loaded)

    def _load_workflow(self, workflow: Workflow | None) -> None:
        self._current = workflow
        self._selected_step_id = workflow.steps[0].id if workflow and workflow.steps else None
        self._saving = True
        self._name_var.set(workflow.name if workflow else "")
        self._saving = False
        self._status.configure(text="")
        self._render_editor()

    def _on_name_changed(self) -> None:
        if self._saving or self._current is None:
            return
        name = self._name_var.get().strip()
        if not name:
            return
        self._current.name = name
        self._persist()

    def _on_step_changed(self) -> None:
        self._persist_and_render(reload_editor=False)

    def _persist_and_render(self, reload_editor: bool = True) -> None:
        self._persist()
        if reload_editor:
            self._render_editor()
        else:
            self._render_canvas()
            self._refresh_tree_counts()

    def _persist(self) -> None:
        if self._current is None:
            return
        self.editor.apply_current()
        self.store.save(self._current)
        self._status.configure(text="Đã lưu")
        self._refresh_tree_counts()

    def _render_editor(self) -> None:
        step = None
        if self._current is not None and self._selected_step_id:
            step = self._current.step_by_id(self._selected_step_id)
        self.editor.load(step)
        self._render_canvas()
        self._refresh_tree_counts()

    def _render_canvas(self) -> None:
        lookup = {item.id: item.name for item in self.library.all()}
        self.canvas.render(
            self._current,
            self._selected_step_id,
            lookup,
            running_id=self._run_current_id,
            completed_ids=self._run_completed,
            failed_id=self._run_failed_id,
        )

    def _refresh_tree_counts(self) -> None:
        if self._current is None or not self.tree.exists(self._current.id):
            return
        self.tree.item(self._current.id, values=(self._current.name, len(self._current.steps)))

    def _selected_workflow_id(self) -> str | None:
        selection = self.tree.selection()
        return selection[0] if selection else None

    def _capture_mouse(self) -> tuple[int, int] | None:
        confirmed = messagebox.askokcancel(
            "Lấy tọa độ chuột",
            "Di chuyển chuột tới vị trí cần click, rồi nhấn OK để lấy tọa độ hiện tại.",
            parent=self,
        )
        if not confirmed:
            return None
        try:
            import pyautogui
        except ImportError:
            messagebox.showerror(
                "Lấy tọa độ",
                "Chưa cài pyautogui. Chạy: python -m pip install pyautogui",
                parent=self,
            )
            return None
        position = pyautogui.position()
        return int(position.x), int(position.y)
