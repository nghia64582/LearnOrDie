"""
Beam Stick DSL Tool - GUI

Generates DSL for L / T / Plus cross-section beam sticks (finger-jointed
from flat sheet material, 3mm joint feature size).

Input: number of L sticks, T sticks, Plus sticks, and a single stick length
(mm) shared by all of them.

Output: DSL text (ADD/M/P/R/RC/END blocks) + canvas preview + Copy DSL button.

Run locally with: python beam_dsl_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox

from beam_dsl_core import build_sheet

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

KIND_COLOR = {"L": "#a8d0f0", "T": "#b8e6b0", "P": "#f5c99b"}


class BeamDslApp:
    def __init__(self, root):
        self.root = root
        root.title("Beam Stick DSL Tool")
        self.dsl_text = ""

        self._build_input_panel()
        self._build_canvas_panel()

    def _build_input_panel(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="ns")
        self.vars = {}

        def add_row(r, label, key, default):
            ttk.Label(frame, text=label).grid(row=r, column=0, sticky="w", pady=2)
            v = tk.StringVar(value=str(default))
            ttk.Entry(frame, textvariable=v, width=8).grid(row=r, column=1, pady=2)
            self.vars[key] = v

        add_row(0, "Stick length (mm):", "length", 60)
        ttk.Separator(frame).grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)
        add_row(2, "Number of L sticks:", "n_L", 3)
        add_row(3, "Number of T sticks:", "n_T", 3)
        add_row(4, "Number of Plus sticks:", "n_plus", 3)

        self.generate_btn = ttk.Button(frame, text="Generate", command=self.on_generate)
        self.generate_btn.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

        self.copy_btn = ttk.Button(frame, text="Copy DSL", command=self.on_copy, state="disabled")
        self.copy_btn.grid(row=6, column=0, columnspan=2, pady=2, sticky="ew")

        self.result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.result_var, wraplength=200, font=(FONT_FAMILY, 9, "bold")
                  ).grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="w")

        legend = ttk.Frame(frame)
        legend.grid(row=8, column=0, columnspan=2, pady=(20, 0), sticky="w")
        for i, (kind, label) in enumerate([("L", "L stick"), ("T", "T stick"), ("P", "Plus stick")]):
            sw = tk.Canvas(legend, width=14, height=14, highlightthickness=1,
                            highlightbackground="black", bg=KIND_COLOR[kind])
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

    def _read_inputs(self):
        try:
            length = float(self.vars["length"].get())
            n_L = int(self.vars["n_L"].get())
            n_T = int(self.vars["n_T"].get())
            n_plus = int(self.vars["n_plus"].get())
        except ValueError:
            raise ValueError("All inputs must be numbers.")
        if length <= 0:
            raise ValueError("Length must be positive.")
        if min(n_L, n_T, n_plus) < 0:
            raise ValueError("Counts must be >= 0.")
        return length, n_L, n_T, n_plus

    def on_generate(self):
        try:
            length, n_L, n_T, n_plus = self._read_inputs()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return

        if n_L + n_T + n_plus == 0:
            messagebox.showerror("Invalid input", "Enter at least one stick.")
            return

        dsl_text, instances, total_width = build_sheet(n_L, n_T, n_plus, length)
        self.dsl_text = dsl_text
        self.copy_btn.config(state="normal")
        self.result_var.set(
            f"Sheet size: {total_width:g} x {length:g} mm\n"
            f"Total sticks: {n_L + n_T + n_plus}")
        self._draw_canvas(instances, total_width, length)

    def _draw_canvas(self, instances, total_width, length):
        self.canvas.delete("all")
        scale = 3.0
        margin = 20

        def to_px(x, y):
            return x * scale + margin, y * scale + margin

        for inst in instances:
            ox = inst["x"]
            color = KIND_COLOR[inst["kind"]]
            draw = inst["draw"]

            for r in draw.get("rects", []):
                x0, y0 = to_px(r["x"] + ox, r["y"])
                x1, y1 = to_px(r["x"] + ox + r["w"], r["y"] + r["h"])
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="black")

            for c in draw.get("cuts", []):
                x0, y0 = to_px(c["x"] + ox, c["y"])
                x1, y1 = to_px(c["x"] + ox + c["w"], c["y"] + c["h"])
                self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="black")

            for poly in draw.get("polys", []):
                pox, poy = poly.get("offset", (0, 0))
                pts = []
                for x, y in poly["points"]:
                    px, py = to_px(x + ox + pox, y + poy)
                    pts += [px, py]
                self.canvas.create_polygon(*pts, fill=color, outline="black")
                for c in poly.get("cuts", []):
                    x0, y0 = to_px(c["x"] + ox + pox, c["y"] + poy)
                    x1, y1 = to_px(c["x"] + ox + pox + c["w"], c["y"] + poy + c["h"])
                    self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="black")

            for line in draw.get("lines", []):
                pts = []
                for x, y in line:
                    px, py = to_px(x + ox, y)
                    pts += [px, py]
                self.canvas.create_line(*pts, fill="black", width=2)

        gw = total_width * scale + margin * 2
        gh = length * scale + margin * 2
        self.canvas.create_rectangle(margin, margin,
                                      total_width * scale + margin,
                                      length * scale + margin,
                                      outline="red", width=2)
        self.canvas.config(scrollregion=(0, 0, gw, gh))

    def on_copy(self):
        if not self.dsl_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.dsl_text)
        self.root.update()
        self.result_var.set(self.result_var.get() + "\n\nDSL copied to clipboard.")


if __name__ == "__main__":
    root = tk.Tk()
    default_font = (FONT_FAMILY, FONT_SIZE)
    root.option_add("*Font", default_font)
    style = ttk.Style(root)
    style.configure(".", font=default_font)
    app = BeamDslApp(root)
    root.geometry("1000x700")
    root.mainloop()