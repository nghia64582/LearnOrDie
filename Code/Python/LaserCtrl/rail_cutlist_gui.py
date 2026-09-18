"""
Tool 2: Rail Cut-list to DSL Tool (optimized packing)

Input: a comma-separated list of rail lengths (mm), e.g. "100,100,80,80"
(paste directly from Tool 1's cut-list output).

These rails are plain 10mm-wide strips (no zigzag / slot -- they plug
into the L/T/Plus joint connectors made by the earlier tool), so each is
just a rectangle. Instead of laying them side by side, this tool packs
them with CP-SAT: rails can be STACKED vertically within the same 10mm
lane, and/or ROTATED 90 degrees to fill leftover gaps -- minimizing the
total sheet width used.

Output: DSL (ADD/P/END blocks), canvas preview, and a Copy DSL button.

Run locally with: python rail_cutlist_gui.py
Requires: pip install ortools
"""

import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox

from rail_cutlist_core import optimize_layout, build_rail_dsl

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


class RailDslApp:
    def __init__(self, root):
        self.root = root
        if hasattr(root, "title"):
            root.title("Rail Cut-list to DSL Tool")
        self.dsl_text = ""
        self.msg_queue = queue.Queue()

        self._build_input_panel()
        self._build_canvas_panel()
        self.root.after(100, self._poll_queue)

    def _build_input_panel(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="ns")

        ttk.Label(frame, text="Cut list (comma-separated lengths, mm):").grid(
            row=0, column=0, sticky="w")
        self.lengths_var = tk.StringVar(value="100,100,80,80")
        ttk.Entry(frame, textvariable=self.lengths_var, width=30).grid(row=1, column=0, pady=4)

        self.generate_btn = ttk.Button(frame, text="Generate (optimize packing)", command=self.on_generate)
        self.generate_btn.grid(row=2, column=0, pady=10, sticky="ew")

        self.copy_btn = ttk.Button(frame, text="Copy DSL", command=self.on_copy, state="disabled")
        self.copy_btn.grid(row=3, column=0, pady=2, sticky="ew")

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(frame, textvariable=self.status_var, wraplength=220, foreground="#555"
                  ).grid(row=4, column=0, pady=(10, 0), sticky="w")

        self.result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.result_var, wraplength=220, font=(FONT_FAMILY, 9, "bold")
                  ).grid(row=5, column=0, pady=(6, 0), sticky="w")

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

        self.generate_btn.config(state="disabled")
        self.copy_btn.config(state="disabled")
        self.result_var.set("")
        self.status_var.set("Optimizing layout...")

        def worker():
            try:
                placements, total_width, height = optimize_layout(lengths, rail_width=RAIL_WIDTH)
                self.msg_queue.put(("done", (placements, total_width, height, lengths)))
            except Exception as e:
                self.msg_queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "error":
                    self.status_var.set("Error.")
                    self.generate_btn.config(state="normal")
                    messagebox.showerror("Solver error", payload)
                elif kind == "done":
                    placements, total_width, height, lengths = payload
                    self.dsl_text = build_rail_dsl(placements, RAIL_WIDTH)
                    used_area = sum(p["w"] * p["h"] for p in placements)
                    sheet_area = total_width * height
                    waste_pct = 100 * (1 - used_area / sheet_area) if sheet_area else 0
                    n_cols = round(total_width / RAIL_WIDTH)
                    self.status_var.set("Done.")
                    self.result_var.set(
                        f"Sheet size: {total_width:g} x {height:g} mm (~{n_cols} columns)\n"
                        f"Total rails: {len(lengths)}\n"
                        f"Waste: {waste_pct:.1f}%")
                    self.generate_btn.config(state="normal")
                    self.copy_btn.config(state="normal")
                    self._draw_canvas(placements, total_width, height)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _draw_canvas(self, placements, total_width, height):
        self.canvas.delete("all")
        scale = 4.0
        margin = 20

        for p in placements:
            x0 = p["x"] * scale + margin
            y0 = p["y"] * scale + margin
            x1 = (p["x"] + p["w"]) * scale + margin
            y1 = (p["y"] + p["h"]) * scale + margin
            color = "#f5c99b" if p["rotated"] else "#cfe2f3"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="black")
            self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=f"{p['length']:g}", font=(FONT_FAMILY, 8))

        gw = total_width * scale + margin * 2
        gh = height * scale + margin * 2
        self.canvas.create_rectangle(margin, margin, total_width * scale + margin, height * scale + margin,
                                      outline="red", width=2)
        self.canvas.config(scrollregion=(0, 0, gw, gh))

    def on_copy(self):
        if not self.dsl_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.dsl_text)
        self.root.update()
        self.status_var.set("DSL copied to clipboard.")


if __name__ == "__main__":
    root = tk.Tk()
    default_font = (FONT_FAMILY, FONT_SIZE)
    root.option_add("*Font", default_font)
    style = ttk.Style(root)
    style.configure(".", font=default_font)
    app = RailDslApp(root)
    root.geometry("900x600")
    root.mainloop()