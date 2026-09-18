"""
Tool 1: Rail Skeleton Tool

Input: a list of centerline rectangles (x y w h), one per line -- each
representing the MIDLINE of a 10mm-wide rail loop/cell (already shrunk 5mm
per side from the outer design size).

Output: a canvas showing the rail skeleton with nodes color-coded by type
(L / T / + / T-rot), plus the resulting cut-list (rail lengths to cut).

Run locally with: python rail_skeleton_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox

from rail_skeleton_core import build_skeleton, cut_list, NODE_COLOR

# ----------------------------------------------------------------------------
# Windows DPI-awareness fix (prevents blurry/broken text on high-DPI screens)
# ----------------------------------------------------------------------------
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Custom font -- change these two to adjust the whole app's font in one place
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 10


class SkeletonApp:
    def __init__(self, root):
        self.root = root
        if hasattr(root, "title"):
            root.title("Rail Skeleton Tool")
        self.cutlist_text = ""

        self._build_input_panel()
        self._build_canvas_panel()

    def _build_input_panel(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="ns")

        ttk.Label(frame, text="Centerline rectangles (x y w h, one per line):").grid(
            row=0, column=0, sticky="w")
        self.rect_text = tk.Text(frame, width=28, height=14)
        self.rect_text.grid(row=1, column=0, pady=4)
        self.rect_text.insert("1.0", "0 0 90 90")

        self.generate_btn = ttk.Button(frame, text="Generate Skeleton", command=self.on_generate)
        self.generate_btn.grid(row=2, column=0, pady=8, sticky="ew")

        ttk.Label(frame, text="Cut list (rail lengths, mm):").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.cutlist_box = tk.Text(frame, width=28, height=6, state="disabled")
        self.cutlist_box.grid(row=4, column=0, pady=4)

        self.copy_btn = ttk.Button(frame, text="Copy cut-list", command=self.on_copy, state="disabled")
        self.copy_btn.grid(row=5, column=0, pady=2, sticky="ew")

        self.result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.result_var, wraplength=220, foreground="#555"
                  ).grid(row=6, column=0, pady=(8, 0), sticky="w")

        legend = ttk.Frame(frame)
        legend.grid(row=7, column=0, pady=(16, 0), sticky="w")
        for i, (label, color) in enumerate(NODE_COLOR.items()):
            sw = tk.Canvas(legend, width=14, height=14, highlightthickness=1,
                            highlightbackground="black", bg=color)
            sw.grid(row=i, column=0, padx=(0, 5), pady=2)
            ttk.Label(legend, text=label).grid(row=i, column=1, sticky="w")

    def _build_canvas_panel(self):
        outer = ttk.Frame(self.root)
        outer.grid(row=0, column=1, sticky="nsew")
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        hbar = ttk.Scrollbar(outer, orient="horizontal")
        vbar = ttk.Scrollbar(outer, orient="vertical")
        self.canvas = tk.Canvas(outer, bg="white",
                                 xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        hbar.config(command=self.canvas.xview)
        vbar.config(command=self.canvas.yview)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

    def _parse_rects(self):
        rects = []
        for line in self.rect_text.get("1.0", "end").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.replace(",", " ").split()
            if len(parts) != 4:
                raise ValueError(f"Invalid line (need 4 numbers): '{line}'")
            x, y, w, h = (float(p) for p in parts)
            if w <= 0 or h <= 0:
                raise ValueError(f"Width/height must be positive: '{line}'")
            rects.append((x, y, w, h))
        return rects

    def on_generate(self):
        try:
            rects = self._parse_rects()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return
        if not rects:
            messagebox.showerror("Invalid input", "Enter at least one rectangle.")
            return

        sk = build_skeleton(rects)
        lengths = cut_list(sk)
        self.cutlist_text = ",".join(str(round(v, 2)) if v != int(v) else str(int(v)) for v in lengths)

        self.cutlist_box.config(state="normal")
        self.cutlist_box.delete("1.0", "end")
        self.cutlist_box.insert("1.0", self.cutlist_text)
        self.cutlist_box.config(state="disabled")
        self.copy_btn.config(state="normal")

        warn = ""
        if sk["free_ends"]:
            warn = f"\n\nWarning: {len(sk['free_ends'])} free/dangling end(s) found (unbraced, not adjusted)."
        self.result_var.set(f"{len(lengths)} rails, {len(sk['nodes'])} nodes.{warn}")

        self._draw_canvas(sk)

    def _draw_canvas(self, sk):
        self.canvas.delete("all")
        scale = 3.0
        margin = 30

        xs = [n["x"] for n in sk["nodes"]] or [0]
        ys = [n["y"] for n in sk["nodes"]] or [0]
        max_x, max_y = max(xs, default=100), max(ys, default=100)

        def to_px(x, y):
            return x * scale + margin, y * scale + margin

        for s in sk["segments"]:
            if s["orient"] == "H":
                x0, y0 = to_px(s["x0"], s["y"])
                x1, y1 = to_px(s["x1"], s["y"])
            else:
                x0, y0 = to_px(s["x"], s["y0"])
                x1, y1 = to_px(s["x"], s["y1"])
            self.canvas.create_line(x0, y0, x1, y1, fill="#333", width=4)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            self.canvas.create_text(mx, my - 8, text=f"{s['length']:g}", fill="#333", font=(FONT_FAMILY, 8))

        for n in sk["nodes"]:
            px, py = to_px(n["x"], n["y"])
            r = 6
            self.canvas.create_oval(px - r, py - r, px + r, py + r,
                                     fill=NODE_COLOR[n["label"]], outline="black")

        for (fx, fy) in sk["free_ends"]:
            px, py = to_px(fx, fy)
            r = 5
            self.canvas.create_oval(px - r, py - r, px + r, py + r,
                                     fill="", outline="red", width=2, dash=(2, 2))

        gw = max_x * scale + margin * 2
        gh = max_y * scale + margin * 2
        self.canvas.config(scrollregion=(0, 0, gw, gh))

    def on_copy(self):
        if not self.cutlist_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.cutlist_text)
        self.root.update()
        self.result_var.set(self.result_var.get() + "\n\nCut-list copied to clipboard.")


if __name__ == "__main__":
    root = tk.Tk()
    default_font = (FONT_FAMILY, FONT_SIZE)
    root.option_add("*Font", default_font)
    style = ttk.Style(root)
    style.configure(".", font=default_font)
    app = SkeletonApp(root)
    root.geometry("950x650")
    root.mainloop()
