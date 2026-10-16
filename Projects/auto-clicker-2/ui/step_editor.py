from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from models.image_library import ImageLibrary
from models.step import Step, StepType, default_params

BUTTON_CHOICES = ("left", "right", "middle")


class StepEditor(ttk.LabelFrame):
    def __init__(
        self,
        master: tk.Misc,
        library: ImageLibrary,
        on_change: Callable[[], None],
        on_capture_point: Callable[[], tuple[int, int] | None],
    ) -> None:
        super().__init__(master, text="Chi tiết bước", padding=10)
        self.library = library
        self._on_change = on_change
        self._on_capture_point = on_capture_point
        self._step: Step | None = None
        self._fields: ttk.Frame | None = None
        self._type_var = tk.StringVar()
        self._note_var = tk.StringVar()
        self._image_var = tk.StringVar()
        self._timeout_var = tk.StringVar()
        self._confidence_var = tk.StringVar()
        self._x_var = tk.StringVar()
        self._y_var = tk.StringVar()
        self._button_var = tk.StringVar()
        self._clicks_var = tk.StringVar()
        self._interval_var = tk.StringVar()
        self._keys_var = tk.StringVar()
        self._text_widget: tk.Text | None = None
        self._rebuilding = False
        self._image_ids: list[str] = []

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="Loại:").pack(side="left")
        self._type_combo = ttk.Combobox(
            header,
            textvariable=self._type_var,
            state="readonly",
            values=[item.label for item in StepType],
            width=22,
        )
        self._type_combo.pack(side="left", padx=(8, 0))
        self._type_combo.bind("<<ComboboxSelected>>", lambda _e: self._change_type())

        self._body = ttk.Frame(self)
        self._body.pack(fill="both", expand=True, pady=(10, 0))

        note_row = ttk.Frame(self)
        note_row.pack(fill="x", pady=(10, 0))
        ttk.Label(note_row, text="Ghi chú:").pack(side="left")
        ttk.Entry(note_row, textvariable=self._note_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._note_var.trace_add("write", lambda *_: self._emit())

        self._placeholder = ttk.Label(self._body, text="Chọn một bước để chỉnh sửa.")
        self._placeholder.pack(anchor="w")

        for var in (
            self._timeout_var,
            self._confidence_var,
            self._x_var,
            self._y_var,
            self._clicks_var,
            self._interval_var,
            self._keys_var,
            self._image_var,
            self._button_var,
        ):
            var.trace_add("write", lambda *_: self._emit())

    def load(self, step: Step | None) -> None:
        self._apply_current()
        self._step = step
        self._rebuilding = True
        try:
            if step is None:
                self._clear_fields()
                self._placeholder.pack(anchor="w")
                self._type_combo.configure(state="disabled")
                return
            self._placeholder.pack_forget()
            self._type_combo.configure(state="readonly")
            self._type_var.set(step.type.label)
            self._note_var.set(step.note)
            self._rebuild_fields()
            self._apply_current()
        finally:
            self._rebuilding = False

    def apply_current(self) -> None:
        self._apply_current()

    def _change_type(self) -> None:
        if self._rebuilding or self._step is None:
            return
        self._apply_current()
        selected = self._type_from_label(self._type_var.get())
        if selected is None or selected is self._step.type:
            return
        merged = default_params(selected)
        for key, value in self._step.params.items():
            if key in merged:
                merged[key] = value
        self._step.type = selected
        self._step.params = merged
        self._rebuilding = True
        try:
            self._rebuild_fields()
            self._apply_current()
        finally:
            self._rebuilding = False
        self._on_change()

    def _rebuild_fields(self) -> None:
        if self._fields is not None:
            self._fields.destroy()
            self._fields = None
        self._text_widget = None
        if self._step is None:
            return
        self._fields = ttk.Frame(self._body)
        self._fields.pack(fill="both", expand=True)
        params = self._step.params
        if self._step.type in (StepType.WAIT_IMAGE, StepType.CLICK_IMAGE):
            self._add_image_row(self._fields, 0)
            self._confidence_var.set(str(params.get("confidence", 0.8)))
            self._add_labeled_entry(self._fields, 1, "Độ khớp (0-1):", self._confidence_var)
            if self._step.type is StepType.WAIT_IMAGE:
                self._timeout_var.set(str(params.get("timeout_seconds", 10)))
                self._add_labeled_entry(self._fields, 2, "Timeout (giây):", self._timeout_var)
            else:
                self._fill_click_options(self._fields, 2, params)
        elif self._step.type is StepType.CLICK_COORDINATE:
            self._x_var.set(str(params.get("x", 0)))
            self._y_var.set(str(params.get("y", 0)))
            ttk.Label(self._fields, text="Tọa độ X:").grid(row=0, column=0, sticky="w", pady=4)
            ttk.Entry(self._fields, textvariable=self._x_var, width=10).grid(row=0, column=1, sticky="w")
            ttk.Label(self._fields, text="Tọa độ Y:").grid(row=1, column=0, sticky="w", pady=4)
            ttk.Entry(self._fields, textvariable=self._y_var, width=10).grid(row=1, column=1, sticky="w")
            ttk.Button(self._fields, text="Lấy tọa độ chuột", command=self._capture).grid(
                row=0, column=2, rowspan=2, padx=(8, 0)
            )
            self._fill_click_options(self._fields, 2, params)
        elif self._step.type is StepType.TYPE_TEXT:
            ttk.Label(self._fields, text="Nội dung:").grid(row=0, column=0, sticky="nw", pady=4)
            self._text_widget = tk.Text(self._fields, height=4, width=36, wrap="word")
            self._text_widget.grid(row=0, column=1, sticky="ew", pady=4)
            self._text_widget.insert("1.0", str(params.get("text", "")))
            self._text_widget.bind("<KeyRelease>", lambda _e: self._emit())
            self._interval_var.set(str(params.get("interval", 0.05)))
            self._add_labeled_entry(self._fields, 1, "Khoảng cách gõ (s):", self._interval_var)
            self._fields.columnconfigure(1, weight=1)
        elif self._step.type is StepType.PRESS_KEY:
            self._keys_var.set(str(params.get("keys", "enter")))
            self._add_labeled_entry(self._fields, 0, "Phím:", self._keys_var)
            ttk.Label(
                self._fields,
                text="Ví dụ: enter, tab, esc, ctrl+c",
                foreground="#667085",
            ).grid(row=1, column=0, columnspan=2, sticky="w")

    def _fill_click_options(self, parent: ttk.Frame, row: int, params: dict) -> None:
        self._button_var.set(str(params.get("button", "left")))
        self._clicks_var.set(str(params.get("clicks", 1)))
        ttk.Label(parent, text="Nút chuột:").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(
            parent,
            textvariable=self._button_var,
            values=BUTTON_CHOICES,
            state="readonly",
            width=12,
        ).grid(row=row, column=1, sticky="w")
        ttk.Label(parent, text="Số lần click:").grid(row=row + 1, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=self._clicks_var, width=10).grid(row=row + 1, column=1, sticky="w")

    def _add_labeled_entry(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var, width=18).grid(row=row, column=1, sticky="w")

    def _add_image_row(self, parent: ttk.Frame, row: int) -> None:
        images = self.library.all()
        self._image_ids = [item.id for item in images]
        labels = [item.name for item in images]
        current = str(self._step.params.get("image_id") or "") if self._step else ""
        if current and current in self._image_ids:
            selected = labels[self._image_ids.index(current)]
        elif labels:
            selected = labels[0]
        else:
            selected = ""
        self._image_var.set(selected)
        ttk.Label(parent, text="Ảnh:").grid(row=row, column=0, sticky="w", pady=4)
        combo = ttk.Combobox(
            parent,
            textvariable=self._image_var,
            values=labels or ["(chưa có ảnh)"],
            state="readonly" if labels else "disabled",
            width=28,
        )
        combo.grid(row=row, column=1, sticky="w")

    def _capture(self) -> None:
        point = self._on_capture_point()
        if point is None:
            return
        x, y = point
        self._x_var.set(str(x))
        self._y_var.set(str(y))
        self._emit()

    def _clear_fields(self) -> None:
        if self._fields is not None:
            self._fields.destroy()
            self._fields = None
        self._text_widget = None

    def _apply_current(self) -> None:
        step = self._step
        if step is None or self._rebuilding:
            return
        step.note = self._note_var.get()
        params = dict(step.params)
        if step.type in (StepType.WAIT_IMAGE, StepType.CLICK_IMAGE):
            params["image_id"] = self._selected_image_id()
            params["confidence"] = self._as_float(self._confidence_var.get(), 0.8)
            if step.type is StepType.WAIT_IMAGE:
                params["timeout_seconds"] = self._as_float(self._timeout_var.get(), 10.0)
            else:
                params["button"] = self._button_var.get() or "left"
                params["clicks"] = self._as_int(self._clicks_var.get(), 1)
        elif step.type is StepType.CLICK_COORDINATE:
            params["x"] = self._as_int(self._x_var.get(), 0)
            params["y"] = self._as_int(self._y_var.get(), 0)
            params["button"] = self._button_var.get() or "left"
            params["clicks"] = self._as_int(self._clicks_var.get(), 1)
        elif step.type is StepType.TYPE_TEXT:
            if self._text_widget is not None:
                params["text"] = self._text_widget.get("1.0", "end-1c")
            params["interval"] = self._as_float(self._interval_var.get(), 0.05)
        elif step.type is StepType.PRESS_KEY:
            params["keys"] = self._keys_var.get().strip() or "enter"
        step.params = params

    def _selected_image_id(self) -> str:
        name = self._image_var.get()
        for asset in self.library.all():
            if asset.name == name:
                return asset.id
        return ""

    def _emit(self) -> None:
        if self._rebuilding or self._step is None:
            return
        self._apply_current()
        self._on_change()

    @staticmethod
    def _type_from_label(label: str) -> StepType | None:
        return next((item for item in StepType if item.label == label), None)

    @staticmethod
    def _as_float(value: str, default: float) -> float:
        try:
            return float(value)
        except ValueError:
            return default

    @staticmethod
    def _as_int(value: str, default: int) -> int:
        try:
            return int(float(value))
        except ValueError:
            return default
