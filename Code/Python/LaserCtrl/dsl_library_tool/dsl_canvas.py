import tkinter as tk
import math


class DSLCanvas(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, background="white", highlightthickness=1)
        self.result = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.font = ("Segoe UI", 9)

        self.bind("<Configure>", lambda e: self.render(self.result) if self.result else None)
        self.bind("<MouseWheel>", self._wheel)

    def clear(self):
        self.delete("all")
        self.result = None

    def _wheel(self, event):
        if not self.result:
            return
        factor = 1.15 if event.delta > 0 else 1 / 1.15
        self.scale *= factor
        self.scale = max(0.05, min(self.scale, 1000))
        self._redraw()

    def render(self, result):
        self.result = result
        self._redraw()

    def _redraw(self):
        self.delete("all")
        result = self.result
        if not result or not result.bounds:
            self.create_text(self.winfo_width()/2, self.winfo_height()/2,
                             text="No geometry", font=self.font)
            return

        min_x, min_y, max_x, max_y = result.bounds
        w = max(max_x - min_x, 1e-6)
        h = max(max_y - min_y, 1e-6)

        cw = max(self.winfo_width(), 100)
        ch = max(self.winfo_height(), 100)

        # Auto-fit on every render; leave enough room for axis/grid labels.
        self.scale = min((cw - 90) / w, (ch - 70) / h)
        self.scale = max(self.scale, 0.01)

        cx = cw / 2
        cy = ch / 2
        world_cx = (min_x + max_x) / 2
        world_cy = (min_y + max_y) / 2

        def xy(x, y):
            return (
                cx + (x - world_cx) * self.scale,
                cy - (y - world_cy) * self.scale
            )

        # Expand visual world enough to include origin.
        vx0 = world_cx - (cw / 2) / self.scale
        vx1 = world_cx + (cw / 2) / self.scale
        vy0 = world_cy - (ch / 2) / self.scale
        vy1 = world_cy + (ch / 2) / self.scale

        grid = self._grid_step(100 / self.scale)
        gx = math.floor(vx0 / grid) * grid
        while gx <= vx1:
            x1, y1 = xy(gx, vy0)
            x2, y2 = xy(gx, vy1)
            self.create_line(x1, y1, x2, y2, fill="#e8e8e8")
            gx += grid

        gy = math.floor(vy0 / grid) * grid
        while gy <= vy1:
            x1, y1 = xy(vx0, gy)
            x2, y2 = xy(vx1, gy)
            self.create_line(x1, y1, x2, y2, fill="#e8e8e8")
            gy += grid

        # Axes.
        if vx0 <= 0 <= vx1:
            x, _ = xy(0, 0)
            self.create_line(x, 0, x, ch, width=1)
            self.create_text(x + 8, 12, text="Oy", anchor="w", font=("Segoe UI", 9, "bold"))
        if vy0 <= 0 <= vy1:
            _, y = xy(0, 0)
            self.create_line(0, y, cw, y, width=1)
            self.create_text(cw - 10, y - 8, text="Ox", anchor="e", font=("Segoe UI", 9, "bold"))

        # Grid labels.
        label_step = grid
        if label_step * self.scale < 45:
            label_step *= 2
        x = math.ceil(vx0 / label_step) * label_step
        while x <= vx1:
            px, py = xy(x, 0)
            self.create_text(px + 3, min(max(py + 12, 12), ch - 5),
                             text=self._fmt(x), anchor="nw", font=self.font)
            x += label_step

        y = math.ceil(vy0 / label_step) * label_step
        while y <= vy1:
            px, py = xy(0, y)
            self.create_text(min(max(px + 5, 5), cw - 5), py - 3,
                             text=self._fmt(y), anchor="sw", font=self.font)
            y += label_step

        # Geometry.
        for seg in result.segments:
            x1, y1, x2, y2 = seg
            a, b = xy(x1, y1)
            c, d = xy(x2, y2)
            self.create_line(a, b, c, d, width=2)

        # ADD labels.
        for x, y, label in result.labels:
            px, py = xy(x, y)
            self.create_text(px + 7, py - 7, text=label,
                             anchor="sw", font=("Segoe UI", 9, "bold"))

        if result.errors:
            msg = f"{len(result.errors)} DSL error(s)"
            self.create_text(8, ch - 8, text=msg, anchor="sw",
                             font=("Segoe UI", 9, "bold"))

    @staticmethod
    def _grid_step(target):
        if target <= 0:
            return 1
        power = 10 ** math.floor(math.log10(target))
        for m in (1, 2, 5, 10):
            if m * power >= target:
                return m * power
        return 10 * power

    @staticmethod
    def _fmt(v):
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return f"{v:.2f}".rstrip("0").rstrip(".")
