"""
Tool 2: Rail Cut-list to DSL Tool

Input: a comma-separated list of rail lengths (mm), e.g. "100,100,80,80"
(paste directly from Tool 1's cut-list output).

These rails are plain 10mm-wide strips (no zigzag / slot -- they plug
into the L/T/Plus joint connectors made by the earlier tool), so each is
just a rectangle.

Output: DSL (ADD/P/END blocks) laid out side by side on a sheet, canvas
preview, and a Copy DSL button.

Run locally with: python rail_cutlist_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox

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

RAIL_WIDTH = 10.0


def _g(v):
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def build_rail_dsl(lengths):
    dsl_lines = []
    x_cursor = 0.0
    instances = []
    for i, length in enumerate(lengths, start=1):
        name = f"rail-{i}"
        pts = [(0, 0), (0, length), (RAIL_WIDTH, length), (RAIL_WIDTH, 0), (0, 0)]
        dsl_lines.append(f"ADD {_g(x_cursor)} 0 {name}")
        dsl_lines.append("P " + " ".join(_g(v) for pt in pts for v in pt))
        dsl_lines.append("END")
        instances.append({"x": x_cursor, "length": length, "name": name})
        x_cursor += RAIL_WIDTH
    return "\n".join(dsl_lines) + "\n", instances, x_cursor


class RailDslApp:
    def __init__(self, root):
        self.root = root
        if hasattr(root, "title"):
            root.title("Rail Cut-list to DSL Tool")
        self.dsl_text = ""

        self._build_input_panel()
        self._build_canvas_panel()

    def _build_input_panel(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="ns")

        ttk.Label(frame, text="Cut list (comma-separated lengths, mm):").grid(
            row=0, column=0, sticky="w")
        self.lengths_var = tk.StringVar(value="100,100,80,80")
        ttk.Entry(frame, textvariable=self.lengths_var, width=30).grid(row=1, column=0, pady=4)

        self.generate_btn = ttk.Button(frame, text="Generate", command=self.on_generate)
        self.generate_btn.grid(row=2, column=0, pady=10, sticky="ew")

        self.copy_btn = ttk.Button(frame, text="Copy DSL", command=self.on_copy, state="disabled")
        self.copy_btn.grid(row=3, column=0, pady=2, sticky="ew")

        self.result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.result_var, wraplength=220, font=(FONT_FAMILY, 9, "bold")
                  ).grid(row=4, column=0, pady=(10, 0), sticky="w")

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

    def _parse_lengths(self):
        raw = self.lengths_var.get().replace(" ", "")
        if not raw:
            raise ValueError("Enter at least one length.")
        parts = [p for p in raw.split(",") if p]
        lengths = []
        for p in parts:
            v = float(p)
            if v <= 0:
                raise ValueError(f"Length must be positive: '{p}'")
            lengths.append(v)
        return lengths

    def on_generate(self):
        try:
            lengths = self._parse_lengths()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return

        dsl_text, instances, total_width = build_rail_dsl(lengths)
        self.dsl_text = dsl_text
        self.copy_btn.config(state="normal")
        self.result_var.set(f"Sheet size: {total_width:g} x {max(lengths):g} mm\n"
                             f"Total rails: {len(lengths)}")
        self._draw_canvas(instances, total_width, max(lengths))

    def _draw_canvas(self, instances, total_width, max_len):
        self.canvas.delete("all")
        scale = 3.0
        margin = 20

        for inst in instances:
            x0 = inst["x"] * scale + margin
            y0 = margin
            x1 = (inst["x"] + RAIL_WIDTH) * scale + margin
            y1 = inst["length"] * scale + margin
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#cfe2f3", outline="black")
            self.canvas.create_text((x0 + x1) / 2, y1 + 10, text=f"{inst['length']:g}", font=(FONT_FAMILY, 8))

        gw = total_width * scale + margin * 2
        gh = max_len * scale + margin * 2
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
    app = RailDslApp(root)
    root.geometry("900x600")
    root.mainloop()
