"""DSL nesting panel — pack top-level ADD ... END blocks (CP-SAT)."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from common.ui import (
    SIZE_MD,
    SIZE_SM,
    JF_HIGHLIGHT,
    JM_HIGHLIGHT,
    attach_scrollbars,
    canvas_font,
    make_button,
    mono_font,
    ui_font,
)
from engraver_ctrl.dsl_highlight import polygons_from_joint_segments
from engraver_ctrl.dsl_nest import nest_dsl
from engraver_ctrl.dsl_parse import (
    all_segments,
    bbox_from_segments,
    parse_blocks,
    parse_text,
)

# Preview-only semantic colors (not control chrome).
CANVAS_BG = "#fbfcfd"
GRID_LINE = "#e2e8ee"
BORDER_STRONG = "#b7c2cc"
TEXT = "#1b232c"
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

    def is_busy(self):
        return bool(self.dsl_solving)

    def _panel(self, parent, title, expand=False):
        wrap = ttk.LabelFrame(parent, text=title, padding=8)
        wrap.pack(fill="both", expand=expand, pady=(0, 8))
        return wrap

    def _field(self, parent, label, default, width=10):
        box = ttk.Frame(parent)
        box.pack(side="left", padx=(0, 12))
        ttk.Label(box, text=label).pack(anchor="w")
        e = ttk.Entry(box, width=width)
        e.insert(0, default)
        e.pack(anchor="w", pady=(2, 0))
        return e

    def _stat(self, parent, label):
        box = ttk.Frame(parent)
        box.pack(side="left", padx=(0, 18))
        ttk.Label(box, text=label).pack(anchor="w")
        val = ttk.Label(box, text="—", style="Heading.TLabel")
        val.pack(anchor="w")
        return val

    def _build_ui(self):
        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, width=440)
        left.pack(side="left", fill="both", padx=(0, 12))
        left.pack_propagate(False)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        in_panel = self._panel(left, "INPUT DSL", expand=True)
        in_head = ttk.Frame(in_panel)
        in_head.pack(fill="x", pady=(0, 6))
        make_button(in_head, "Load file...", command=self.load_dsl_file).pack(side="left")

        in_box = ttk.Frame(in_panel)
        in_box.pack(fill="both", expand=True)
        self.dsl_in_text = tk.Text(
            in_box, height=18, wrap="none", undo=True, font=mono_font(SIZE_SM),
        )
        self.dsl_in_vbar, self.dsl_in_hbar = attach_scrollbars(
            in_box, self.dsl_in_text, vertical=True, horizontal=True,
        )

        cfg_panel = self._panel(left, "SHEET")
        row = ttk.Frame(cfg_panel)
        row.pack(fill="x")
        self.e_dsl_height = self._field(row, "H (mm, empty = tallest block)", "", width=16)
        self.e_dsl_timelimit = self._field(row, "Time limit (s)", "15", width=8)
        rot_row = ttk.Frame(cfg_panel)
        rot_row.pack(fill="x", pady=(10, 0))
        self.dsl_rotate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            rot_row, text="Allow 90° rotation", variable=self.dsl_rotate_var,
        ).pack(side="left")

        calc_panel = ttk.Frame(left)
        calc_panel.pack(fill="x", pady=(4, 0))
        self.dsl_calc_btn = make_button(calc_panel, "Solve", command=self.solve_dsl)
        self.dsl_calc_btn.pack(fill="x")
        self.dsl_status_lbl = ttk.Label(calc_panel, text="", wraplength=400)
        self.dsl_status_lbl.pack(fill="x", pady=(6, 0))

        canvas_panel = self._panel(right, "PREVIEW", expand=True)
        cv_wrap = ttk.Frame(canvas_panel)
        cv_wrap.pack(fill="both", expand=True)
        self.dsl_canvas = tk.Canvas(cv_wrap, bg=CANVAS_BG, highlightthickness=1, height=420)
        self.dsl_canvas.pack(fill="both", expand=True)
        self.dsl_canvas.bind("<Configure>", lambda e: self.redraw_dsl())

        results = ttk.Frame(canvas_panel)
        results.pack(fill="x", pady=(12, 0))
        self.dsl_stat_width = self._stat(results, "Result width")
        self.dsl_stat_height = self._stat(results, "Sheet height H used")
        self.dsl_stat_eff = self._stat(results, "Utilization")

        self.dsl_warn_lbl = ttk.Label(canvas_panel, text="", wraplength=760)

        out_panel = self._panel(right, "OUTPUT DSL", expand=True)
        out_head = ttk.Frame(out_panel)
        out_head.pack(fill="x")
        ttk.Label(out_head, text="").pack(side="left", expand=True, fill="x")
        self.dsl_copy_status = ttk.Label(out_head, text="Copied")
        make_button(out_head, "Copy DSL", command=self.copy_nested_dsl).pack(side="right")
        make_button(out_head, "Save DSL...", command=self.save_nested_dsl).pack(
            side="right", padx=(0, 8)
        )

        out_box = ttk.Frame(out_panel)
        out_box.pack(fill="both", expand=True, pady=(6, 0))
        self.dsl_out_text = tk.Text(
            out_box, height=10, wrap="none", undo=True, font=mono_font(SIZE_SM),
        )
        self.dsl_out_vbar, self.dsl_out_hbar = attach_scrollbars(
            out_box, self.dsl_out_text, vertical=True, horizontal=True,
        )

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
        # JM/JF fills first so G-code strokes paint on top.
        hl_colors = {"JM": JM_HIGHLIGHT, "JF": JF_HIGHLIGHT}
        for cmd, segs in parsed["shapes"]:
            fill = hl_colors.get(cmd)
            if not fill:
                continue
            for poly in polygons_from_joint_segments(cmd, segs):
                coords = []
                for x, y in poly:
                    coords.extend(to_canvas(x, y))
                if len(coords) >= 6:
                    canvas.create_polygon(
                        *coords, fill=fill, outline="", tags="jmjf_hl",
                    )
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
                x1 + 4, y1 + 10, text=label, fill=TEXT, anchor="w",
                font=canvas_font(),
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
