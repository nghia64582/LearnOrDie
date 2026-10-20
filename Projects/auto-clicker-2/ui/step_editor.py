from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from engine import windows
from models.image_library import ImageLibrary
from models.step import Step, StepType, default_params

BUTTON_CHOICES = ("left", "right", "middle")
# Đếm ngược trước khi đọc vị trí chuột, để kịp di chuột tới chỗ cần lấy
CAPTURE_COUNTDOWN_SECONDS = 3
WINDOW_MODES = {"position": "Vị trí & kích thước", "maximize": "Phóng to (maximize)"}


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
        self._duration_var = tk.StringVar()
        self._x1_var = tk.StringVar()
        self._y1_var = tk.StringVar()
        self._x2_var = tk.StringVar()
        self._y2_var = tk.StringVar()
        self._title_var = tk.StringVar()
        self._mode_var = tk.StringVar()
        self._left_var = tk.StringVar()
        self._top_var = tk.StringVar()
        self._width_var = tk.StringVar()
        self._height_var = tk.StringVar()
        self._capture_after_id: str | None = None
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
            self._duration_var,
            self._x1_var,
            self._y1_var,
            self._x2_var,
            self._y2_var,
            self._title_var,
            self._mode_var,
            self._left_var,
            self._top_var,
            self._width_var,
            self._height_var,
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
        self._cancel_capture()
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
        elif self._step.type is StepType.MOVE_MOUSE:
            self._x_var.set(str(params.get("x", 0)))
            self._y_var.set(str(params.get("y", 0)))
            self._add_point_rows(self._fields, 0, "Tọa độ", self._x_var, self._y_var)
            self._duration_var.set(str(params.get("duration", 0.2)))
            self._add_labeled_entry(self._fields, 3, "Thời gian di (s):", self._duration_var)
        elif self._step.type is StepType.DRAG_MOUSE:
            self._x1_var.set(str(params.get("x1", 0)))
            self._y1_var.set(str(params.get("y1", 0)))
            self._x2_var.set(str(params.get("x2", 0)))
            self._y2_var.set(str(params.get("y2", 0)))
            self._add_point_rows(self._fields, 0, "Từ", self._x1_var, self._y1_var)
            self._add_point_rows(self._fields, 3, "Đến", self._x2_var, self._y2_var)
            self._button_var.set(str(params.get("button", "left")))
            ttk.Label(self._fields, text="Nút chuột:").grid(row=6, column=0, sticky="w", pady=4)
            ttk.Combobox(
                self._fields,
                textvariable=self._button_var,
                values=BUTTON_CHOICES,
                state="readonly",
                width=12,
            ).grid(row=6, column=1, sticky="w")
            self._duration_var.set(str(params.get("duration", 0.5)))
            self._add_labeled_entry(self._fields, 7, "Thời gian kéo (s):", self._duration_var)
        elif self._step.type.is_window_step:
            self._add_window_rows(self._fields, params)
        if self._step.type in (StepType.MOVE_MOUSE, StepType.DRAG_MOUSE):
            self._capture_status = ttk.Label(self._fields, text="", foreground="#667085")
            self._capture_status.grid(row=8, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def _add_point_rows(
        self, parent: ttk.Frame, row: int, label: str, x_var: tk.StringVar, y_var: tk.StringVar
    ) -> None:
        ttk.Label(parent, text=f"{label} X:").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=x_var, width=10).grid(row=row, column=1, sticky="w")
        ttk.Label(parent, text=f"{label} Y:").grid(row=row + 1, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=y_var, width=10).grid(row=row + 1, column=1, sticky="w")
        ttk.Button(
            parent,
            text=f"Lấy vị trí chuột ({CAPTURE_COUNTDOWN_SECONDS}s)",
            command=lambda: self._start_capture(x_var, y_var),
        ).grid(row=row + 2, column=1, sticky="w", pady=(0, 6))

    def _add_window_rows(self, parent: ttk.Frame, params: dict) -> None:
        self._title_var.set(str(params.get("title", "")))
        ttk.Label(parent, text="Cửa sổ:").grid(row=0, column=0, sticky="w", pady=4)
        # Combobox cho gõ tự do: khớp theo tiêu đề (chứa chuỗi, không phân biệt hoa thường)
        self._title_combo = ttk.Combobox(parent, textvariable=self._title_var, width=20)
        self._title_combo.grid(row=0, column=1, sticky="ew")
        ttk.Button(parent, text="Làm mới danh sách", command=self._refresh_window_titles).grid(
            row=1, column=1, sticky="w"
        )
        self._window_status = ttk.Label(parent, text="", foreground="#667085", wraplength=260)
        self._window_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self._refresh_window_titles()
        self._timeout_var.set(str(params.get("timeout_seconds", 5.0)))
        self._add_labeled_entry(parent, 3, "Đợi cửa sổ tối đa (s):", self._timeout_var)
        parent.columnconfigure(1, weight=1)
        if self._step is None or self._step.type is not StepType.SET_WINDOW:
            return
        self._mode_var.set(WINDOW_MODES.get(str(params.get("mode", "position")), WINDOW_MODES["position"]))
        ttk.Label(parent, text="Kiểu:").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Combobox(
            parent,
            textvariable=self._mode_var,
            values=list(WINDOW_MODES.values()),
            state="readonly",
            width=20,
        ).grid(row=4, column=1, sticky="ew")
        for row, (label, var, key, default) in enumerate(
            (
                ("Trái (left):", self._left_var, "left", 0),
                ("Trên (top):", self._top_var, "top", 0),
                ("Rộng (width):", self._width_var, "width", 800),
                ("Cao (height):", self._height_var, "height", 600),
            ),
            start=5,
        ):
            var.set(str(params.get(key, default)))
            self._add_labeled_entry(parent, row, label, var)
        ttk.Button(parent, text="Lấy từ cửa sổ", command=self._read_window_geometry).grid(
            row=9, column=1, sticky="w"
        )

    def _refresh_window_titles(self) -> None:
        try:
            titles = windows.list_window_titles()
        except Exception as exc:
            titles = []
            self._window_status.configure(text=str(exc), foreground="#b42318")
        else:
            self._window_status.configure(
                text=f"{len(titles)} cửa sổ đang mở. Có thể gõ một phần tiêu đề.",
                foreground="#667085",
            )
        self._title_combo.configure(values=titles)

    def _read_window_geometry(self) -> None:
        try:
            win = windows.find_window(self._title_var.get())
        except Exception as exc:
            self._window_status.configure(text=str(exc), foreground="#b42318")
            return
        self._left_var.set(str(int(win.left)))
        self._top_var.set(str(int(win.top)))
        self._width_var.set(str(int(win.width)))
        self._height_var.set(str(int(win.height)))
        self._window_status.configure(text=f'Đã lấy vị trí của "{win.title}".', foreground="#667085")

    def _start_capture(self, x_var: tk.StringVar, y_var: tk.StringVar) -> None:
        # Đếm ngược không chặn UI, hết giờ thì đọc vị trí chuột hiện tại
        self._cancel_capture()
        self._capture_tick(CAPTURE_COUNTDOWN_SECONDS, x_var, y_var)

    def _capture_tick(self, remaining: int, x_var: tk.StringVar, y_var: tk.StringVar) -> None:
        if remaining > 0:
            self._capture_status.configure(
                text=f"Di chuột tới vị trí cần lấy… {remaining}", foreground="#667085"
            )
            self._capture_after_id = self.after(1000, self._capture_tick, remaining - 1, x_var, y_var)
            return
        self._capture_after_id = None
        try:
            import pyautogui

            position = pyautogui.position()
        except Exception as exc:
            self._capture_status.configure(text=f"Không lấy được vị trí chuột: {exc}", foreground="#b42318")
            return
        x_var.set(str(int(position.x)))
        y_var.set(str(int(position.y)))
        self._capture_status.configure(text=f"Đã lấy ({int(position.x)}, {int(position.y)}).")
        self._emit()

    def _cancel_capture(self) -> None:
        if self._capture_after_id is not None:
            try:
                self.after_cancel(self._capture_after_id)
            except tk.TclError:
                pass
            self._capture_after_id = None

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
        self._cancel_capture()
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
        elif step.type is StepType.MOVE_MOUSE:
            params["x"] = self._as_int(self._x_var.get(), 0)
            params["y"] = self._as_int(self._y_var.get(), 0)
            params["duration"] = self._as_float(self._duration_var.get(), 0.2)
        elif step.type is StepType.DRAG_MOUSE:
            params["x1"] = self._as_int(self._x1_var.get(), 0)
            params["y1"] = self._as_int(self._y1_var.get(), 0)
            params["x2"] = self._as_int(self._x2_var.get(), 0)
            params["y2"] = self._as_int(self._y2_var.get(), 0)
            params["button"] = self._button_var.get() or "left"
            params["duration"] = self._as_float(self._duration_var.get(), 0.5)
        elif step.type.is_window_step:
            params["title"] = self._title_var.get().strip()
            params["timeout_seconds"] = self._as_float(self._timeout_var.get(), 5.0)
            if step.type is StepType.SET_WINDOW:
                mode = next((key for key, label in WINDOW_MODES.items() if label == self._mode_var.get()), "position")
                params["mode"] = mode
                params["left"] = self._as_int(self._left_var.get(), 0)
                params["top"] = self._as_int(self._top_var.get(), 0)
                params["width"] = self._as_int(self._width_var.get(), 800)
                params["height"] = self._as_int(self._height_var.get(), 600)
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
