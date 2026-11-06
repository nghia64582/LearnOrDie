"""DSL nesting panel — pack top-level ADD ... END blocks (CP-SAT)."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from engraver_ctrl.dsl_nest import nest_dsl
from engraver_ctrl.dsl_parse import (
    all_segments,
    bbox_from_segments,
    parse_blocks,
    parse_text,
)

BG = "#f3f5f7"
PANEL = "#ffffff"
PANEL_ALT = "#eef1f5"
BORDER = "#d7dee5"
BORDER_STRONG = "#b7c2cc"
TEXT = "#1b232c"
TEXT_DIM = "#5b6774"
ACCENT = "#d9590c"
ACCENT_ON = "#ffffff"
DANGER = "#b91c1c"
DANGER_SOFT = "#fdeceb"
SUCCESS = "#15803d"
CANVAS_BG = "#fbfcfd"
GRID_LINE = "#e2e8ee"

PALETTE = [
    "#d9590c", "#0f8f83", "#7c3aed", "#be185d",
    "#a16207", "#1d4ed8", "#15803d", "#c2410c",
]

SHAPE_COLORS = {
    "C": "#111111", "R": "#15803d", "RC": "#0f8f83",
    "L": "#1d4ed8", "LH": "#1d4ed8", "LV": "#1d4ed8",
    "A": "#7c3aed", "P": "#7c3aed", "M": "#c2410c",
    "JF": "#b91c1c", "JM": "#1d4ed8",
}


class DSLNestingPanel(ttk.Frame):
    """Single-panel DSL nesting UI (ADD-block strip packing)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.root = self.winfo_toplevel()
        self.dsl_result_queue = queue.Queue()
        self.dsl_solving = False
        self.last_dsl = ""
        self.last_dsl_W = 0.0
        self.last_dsl_H = 0.0
        self._build_ui()

    # ---- busy flag for app-level close guard ----
    def is_busy(self):
        return bool(self.dsl_solving)

    def _panel(self, parent, title, expand=False):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=expand, pady=(0, 10))
        tk.Label(wrap, text=title, bg=BG, fg=TEXT_DIM, anchor="w").pack(fill="x")
        body = tk.Frame(wrap, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        body.pack(fill="both", expand=True, pady=(4, 0))
        inner = tk.Frame(body, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=10, pady=10)
        return inner

    def _field(self, parent, label, default, width=10):
        box = tk.Frame(parent, bg=PANEL)
        box.pack(side="left", padx=(0, 12))
        tk.Label(box, text=label, bg=PANEL, fg=TEXT_DIM, anchor="w").pack(anchor="w")
        e = tk.Entry(box, width=width, bg=PANEL_ALT, relief="flat",
                     highlightthickness=1, highlightbackground=BORDER)
        e.insert(0, default)
        e.pack(anchor="w", pady=(2, 0))
        return e

    def _stat(self, parent, label, accent=False):
        box = tk.Frame(parent, bg=PANEL)
        box.pack(side="left", padx=(0, 18))
        tk.Label(box, text=label, bg=PANEL, fg=TEXT_DIM).pack(anchor="w")
        val = tk.Label(box, text="—", bg=PANEL,
                       fg=ACCENT if accent else TEXT)
        val.pack(anchor="w")
        return val

    def _build_ui(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        left = tk.Frame(body, bg=BG, width=440)
        left.pack(side="left", fill="both", padx=(0, 16))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        in_panel = self._panel(left, "INPUT DSL", expand=True)
        in_head = tk.Frame(in_panel, bg=PANEL)
        in_head.pack(fill="x", pady=(0, 6))
        tk.Button(
            in_head, text="Load file...", command=self.load_dsl_file,
            bg=PANEL_ALT, fg=TEXT, relief="flat", highlightthickness=1,
            highlightbackground=BORDER, cursor="hand2", padx=10, pady=4,
        ).pack(side="left")

        in_box = tk.Frame(in_panel, bg=PANEL)
        in_box.pack(fill="both", expand=True)
        self.dsl_in_text = tk.Text(
            in_box, bg=PANEL_ALT, fg=TEXT, insertbackground=TEXT,
            relief="flat", highlightthickness=1, highlightbackground=BORDER,
            height=18, wrap="none",
        )
        in_scroll = tk.Scrollbar(in_box, orient="vertical", command=self.dsl_in_text.yview)
        self.dsl_in_text.configure(yscrollcommand=in_scroll.set)
        self.dsl_in_text.pack(side="left", fill="both", expand=True)
        in_scroll.pack(side="right", fill="y")

        cfg_panel = self._panel(left, "SHEET")
        row = tk.Frame(cfg_panel, bg=PANEL)
        row.pack(fill="x")
        self.e_dsl_height = self._field(row, "H (mm, empty = tallest block)", "", width=16)
        self.e_dsl_timelimit = self._field(row, "Time limit (s)", "15", width=8)
        rot_row = tk.Frame(cfg_panel, bg=PANEL)
        rot_row.pack(fill="x", pady=(10, 0))
        self.dsl_rotate_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            rot_row, text="Allow 90° rotation", variable=self.dsl_rotate_var,
            bg=PANEL, fg=TEXT, activebackground=PANEL, selectcolor=PANEL,
            highlightthickness=0,
        ).pack(side="left")

        calc_panel = tk.Frame(left, bg=BG)
        calc_panel.pack(fill="x", pady=(4, 0))
        self.dsl_calc_btn = tk.Button(
            calc_panel, text="Solve", command=self.solve_dsl,
            bg=ACCENT, fg=ACCENT_ON, activebackground=ACCENT,
            activeforeground=ACCENT_ON, relief="flat", cursor="hand2", pady=10,
        )
        self.dsl_calc_btn.pack(fill="x")
        self.dsl_status_lbl = tk.Label(
            calc_panel, text="", bg=BG, fg=TEXT_DIM, wraplength=400, justify="left",
        )
        self.dsl_status_lbl.pack(fill="x", pady=(6, 0))

        canvas_panel = self._panel(right, "PREVIEW", expand=True)
        cv_wrap = tk.Frame(
            canvas_panel, bg=CANVAS_BG, highlightbackground=BORDER, highlightthickness=1,
        )
        cv_wrap.pack(fill="both", expand=True)
        self.dsl_canvas = tk.Canvas(cv_wrap, bg=CANVAS_BG, highlightthickness=0, height=420)
        self.dsl_canvas.pack(fill="both", expand=True, padx=2, pady=2)
        self.dsl_canvas.bind("<Configure>", lambda e: self.redraw_dsl())

        results = tk.Frame(canvas_panel, bg=PANEL)
        results.pack(fill="x", pady=(12, 0))
        self.dsl_stat_width = self._stat(results, "Result width", accent=True)
        self.dsl_stat_height = self._stat(results, "Sheet height H used")
        self.dsl_stat_eff = self._stat(results, "Utilization")

        self.dsl_warn_lbl = tk.Label(
            canvas_panel, text="", bg=DANGER_SOFT, fg=DANGER,
            justify="left", anchor="w", wraplength=760,
        )

        out_panel = self._panel(right, "OUTPUT DSL", expand=True)
        out_head = tk.Frame(out_panel, bg=PANEL)
        out_head.pack(fill="x")
        tk.Label(out_head, text="", bg=PANEL).pack(side="left", expand=True, fill="x")
        self.dsl_copy_status = tk.Label(out_head, text="Copied", bg=PANEL, fg=SUCCESS)
        tk.Button(
            out_head, text="Copy DSL", command=self.copy_nested_dsl,
            bg=PANEL_ALT, fg=TEXT, relief="flat", highlightthickness=1,
            highlightbackground=BORDER, cursor="hand2", padx=10, pady=4,
        ).pack(side="right")
        tk.Button(
            out_head, text="Save DSL...", command=self.save_nested_dsl,
            bg=PANEL_ALT, fg=TEXT, relief="flat", highlightthickness=1,
            highlightbackground=BORDER, cursor="hand2", padx=10, pady=4,
        ).pack(side="right", padx=(0, 8))

        out_box = tk.Frame(out_panel, bg=PANEL)
        out_box.pack(fill="both", expand=True, pady=(6, 0))
        self.dsl_out_text = tk.Text(
            out_box, bg=PANEL_ALT, fg=TEXT, insertbackground=TEXT,
            relief="flat", highlightthickness=1, highlightbackground=BORDER,
            height=10, wrap="none",
        )
        out_scroll = tk.Scrollbar(out_box, orient="vertical", command=self.dsl_out_text.yview)
        self.dsl_out_text.configure(yscrollcommand=out_scroll.set)
        self.dsl_out_text.pack(side="left", fill="both", expand=True)
        out_scroll.pack(side="right", fill="y")

    def load_dsl_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text/DSL", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.dsl_in_text.delete("1.0", "end")
        self.dsl_in_text.insert("1.0", text)

    def solve_dsl(self):
        dsl = self.dsl_in_text.get("1.0", "end")
        if not dsl.strip():
            messagebox.showwarning("No DSL", "Paste or load a DSL first.")
            return
        raw_h = self.e_dsl_height.get().strip()
        height = None
        if raw_h:
            try:
                height = float(raw_h)
            except ValueError:
                messagebox.showerror("Error", "Sheet height H is not a valid number.")
                return
            if height <= 0:
                messagebox.showerror("Error", "Sheet height H must be greater than 0.")
                return
        try:
            time_limit = max(1.0, float(self.e_dsl_timelimit.get()))
        except ValueError:
            time_limit = 15.0
        allow_rotate = bool(self.dsl_rotate_var.get())

        self.dsl_solving = True
        self.dsl_calc_btn.config(state="disabled", text="Solving...")
        self.dsl_status_lbl.config(text="CP-SAT is solving, please wait...")
        self.dsl_warn_lbl.pack_forget()

        def worker():
            try:
                result = nest_dsl(
                    dsl, height=height, allow_rotate=allow_rotate, time_limit=time_limit
                )
                self.dsl_result_queue.put(("ok", result))
            except Exception as exc:
                self.dsl_result_queue.put(("err", exc))

        threading.Thread(target=worker, daemon=True).start()
        self.after(150, self._poll_dsl_result)

    def _poll_dsl_result(self):
        try:
            kind, payload = self.dsl_result_queue.get_nowait()
        except queue.Empty:
            self.after(150, self._poll_dsl_result)
            return

        self.dsl_solving = False
        self.dsl_calc_btn.config(state="normal", text="Solve")
        if kind == "err":
            self.dsl_status_lbl.config(text="Solve failed.")
            messagebox.showerror("Cannot solve", str(payload))
            return

        result = payload
        self.last_dsl = result["dsl"]
        self.last_dsl_W = result["W"]
        self.last_dsl_H = result["H"]
        src = "heuristic fallback" if result.get("heuristic") else result["status"]
        self.dsl_status_lbl.config(
            text=f"{src}  •  {result['n_blocks']} blocks  •  {result['elapsed']:.2f}s"
        )
        self.e_dsl_height.delete(0, "end")
        self.e_dsl_height.insert(0, f"{result['H']:.2f}".rstrip("0").rstrip("."))
        self.dsl_stat_width.config(text=f"{result['W']:.2f} mm")
        self.dsl_stat_height.config(text=f"{result['H']:.2f} mm")
        area = sum(p["w"] * p["h"] for p in result["placements"])
        eff = (area / (result["W"] * result["H"]) * 100) if result["W"] > 0 else 0
        self.dsl_stat_eff.config(text=f"{eff:.1f}%")

        if result["infeasible"]:
            names = ", ".join(it["name"] for it in result["infeasible"])
            self.dsl_warn_lbl.config(
                text=(
                    "Could not place (does not fit H even after rotation, "
                    f"or solver timed out): {names}"
                )
            )
            self.dsl_warn_lbl.pack(fill="x", pady=(10, 0))
        else:
            self.dsl_warn_lbl.pack_forget()

        self.dsl_out_text.delete("1.0", "end")
        self.dsl_out_text.insert("1.0", result["dsl"])
        self.redraw_dsl()

    def redraw_dsl(self):
        canvas = getattr(self, "dsl_canvas", None)
        if canvas is None:
            return
        canvas.delete("all")
        dsl = self.last_dsl
        if not dsl or self.last_dsl_W <= 0:
            return
        Wpx = max(canvas.winfo_width(), 100)
        Hpx = max(canvas.winfo_height(), 100)
        pad = 20
        avail_w, avail_h = Wpx - 2 * pad, Hpx - 2 * pad
        sheet_w, sheet_h = max(self.last_dsl_W, 1), max(self.last_dsl_H, 1)
        scale = min(avail_w / sheet_w, avail_h / sheet_h)
        draw_w, draw_h = sheet_w * scale, sheet_h * scale
        ox = pad + (avail_w - draw_w) / 2
        oy = pad + (avail_h - draw_h) / 2

        def to_canvas(x, y):
            return ox + x * scale, oy + draw_h - y * scale

        grid_step = 50
        while sheet_w / grid_step > 24 or sheet_h / grid_step > 24:
            grid_step *= 2
        gx = 0.0
        while gx <= sheet_w + 1e-6:
            x1, y1 = to_canvas(gx, 0)
            x2, y2 = to_canvas(gx, sheet_h)
            canvas.create_line(x1, y1, x2, y2, fill=GRID_LINE)
            gx += grid_step
        gy = 0.0
        while gy <= sheet_h + 1e-6:
            x1, y1 = to_canvas(0, gy)
            x2, y2 = to_canvas(sheet_w, gy)
            canvas.create_line(x1, y1, x2, y2, fill=GRID_LINE)
            gy += grid_step

        sx, sy = to_canvas(0, sheet_h)
        canvas.create_rectangle(
            sx, sy, sx + draw_w, sy + draw_h, outline=BORDER_STRONG, width=1.5
        )

        parsed = parse_text(dsl)
        for cmd, segs in parsed["shapes"]:
            color = SHAPE_COLORS.get(cmd, TEXT)
            for x1, y1, x2, y2 in segs:
                canvas.create_line(
                    *to_canvas(x1, y1), *to_canvas(x2, y2), fill=color, width=1.4
                )

        lines = dsl.splitlines()
        blocks = parse_blocks(dsl).blocks
        for i, block in enumerate(blocks):
            chunk = "\n".join(lines[block.start:block.end + 1])
            box = bbox_from_segments(all_segments(parse_text(chunk)))
            if not box:
                continue
            color = PALETTE[i % len(PALETTE)]
            x1, y1 = to_canvas(box["minx"], box["maxy"])
            x2, y2 = to_canvas(box["maxx"], box["miny"])
            canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=1.2, dash=(4, 3))
            label = block.label or f"#{i + 1}"
            canvas.create_text(
                x1 + 4, y1 + 10, text=label, fill=TEXT, anchor="w"
            )

    def copy_nested_dsl(self):
        text = self.dsl_out_text.get("1.0", "end")
        if not text.strip():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text if text.endswith("\n") else text)
        self.root.update()
        self.dsl_copy_status.pack(side="right", padx=(0, 10))
        self.after(1400, self.dsl_copy_status.pack_forget)

    def save_nested_dsl(self):
        text = self.dsl_out_text.get("1.0", "end")
        if not text.strip():
            messagebox.showinfo("No output", "Solve first, then save the nested DSL.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text/DSL", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text if text.endswith("\n") else text)


def build_dsl_nesting_panel(parent):
    panel = DSLNestingPanel(parent)
    panel.pack(fill="both", expand=True)
    return panel
