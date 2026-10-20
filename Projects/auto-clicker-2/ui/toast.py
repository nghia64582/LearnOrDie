from __future__ import annotations

import tkinter as tk

TOAST_COLORS = {
    "info": ("#1f2937", "#ffffff"),
    "success": ("#065f46", "#ffffff"),
    "error": ("#b42318", "#ffffff"),
}


class Toast(tk.Toplevel):
    """Thông báo nhỏ, không chặn (non-modal), tự đóng sau vài giây.

    Hiện ở góc dưới-phải cửa sổ chính, không lấy focus; click để đóng sớm.
    """

    def __init__(self, master: tk.Misc, text: str, kind: str = "info", duration_ms: int = 3000) -> None:
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        background, foreground = TOAST_COLORS.get(kind, TOAST_COLORS["info"])
        self.configure(background=background)

        label = tk.Label(
            self,
            text=text,
            background=background,
            foreground=foreground,
            font=("Segoe UI", 10),
            justify="left",
            wraplength=360,
            padx=14,
            pady=10,
        )
        label.pack()
        for widget in (self, label):
            widget.bind("<Button-1>", lambda _e: self.dismiss())

        self._place(master.winfo_toplevel())
        self._after_id = self.after(duration_ms, self.dismiss) if duration_ms > 0 else None

    def _place(self, window: tk.Misc) -> None:
        self.update_idletasks()
        # Góc dưới-phải, chừa khoảng phía dưới để không che thanh nút
        margin = 16
        bottom_gap = 96
        x = window.winfo_rootx() + window.winfo_width() - self.winfo_reqwidth() - margin
        y = window.winfo_rooty() + window.winfo_height() - self.winfo_reqheight() - bottom_gap
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def dismiss(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        if self.winfo_exists():
            self.destroy()
