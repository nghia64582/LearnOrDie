"""
Tool 5: Box Frame Tool

Input: centerline rectangles (same as the Skeleton tab), column height H,
shared strip width, and how many identical planar frames (default 2).

Output: one DSL file with nested ADD groups (rails / joints / beams),
a skeleton preview, Copy DSL, and Save DSL.

Run locally with: python box_gui.py
Requires: pip install ortools
"""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from frame_creator.beam_dsl_core import TOOTH
from frame_creator.box_core import (
    CELL_SIZE,
    JOINT_WARNING,
    build_box,
    format_length,
    format_length_list,
)
from frame_creator.rail_skeleton_core import NODE_COLOR
from frame_creator.rail_skeleton_gui import draw_skeleton

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

FONT_FAMILY = "Segoe UI"
FONT_SIZE = 10


class BoxApp:
    def __init__(self, root):
        self.root = root
        if hasattr(root, "title"):
            root.title("Box Frame Tool")
        self.dsl_text = ""
        self.msg_queue = queue.Queue()

        self._build_input_panel()
        self._build_canvas_panel()
        self.root.after(100, self._poll_queue)

    def _build_input_panel(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="ns")

        ttk.Label(frame, text="Centerline rectangles (x y w h, one per line):").grid(
            row=0, column=0, sticky="w")
        self.rect_text = tk.Text(frame, width=28, height=10)
        self.rect_text.grid(row=1, column=0, pady=4)
        self.rect_text.insert("1.0", "0 0 90 90")

        fields = ttk.Frame(frame)
        fields.grid(row=2, column=0, pady=(4, 0), sticky="w")

        ttk.Label(fields, text="Height H (mm):").grid(row=0, column=0, sticky="w")
        self.height_var = tk.StringVar(value="100")
        ttk.Entry(fields, textvariable=self.height_var, width=8).grid(
            row=0, column=1, padx=(6, 0), pady=2)

        ttk.Label(fields, text="Strip width (mm):").grid(row=1, column=0, sticky="w")
        self.width_var = tk.StringVar(value="10")
        ttk.Entry(fields, textvariable=self.width_var, width=8).grid(
            row=1, column=1, padx=(6, 0), pady=2)

        ttk.Label(fields, text="Frames:").grid(row=2, column=0, sticky="w")
        self.frames_var = tk.StringVar(value="2")
        ttk.Entry(fields, textvariable=self.frames_var, width=8).grid(
            row=2, column=1, padx=(6, 0), pady=2)

        ttk.Label(fields, text="Beam count:").grid(row=3, column=0, sticky="w")
        self.beam_count_var = tk.StringVar(value="1")
        ttk.Entry(fields, textvariable=self.beam_count_var, width=8).grid(
            row=3, column=1, padx=(6, 0), pady=2)

        self.generate_btn = ttk.Button(frame, text="Generate", command=self.on_generate)
        self.generate_btn.grid(row=4, column=0, pady=8, sticky="ew")

        self.copy_btn = ttk.Button(frame, text="Copy DSL", command=self.on_copy,
                                   state="disabled")
        self.copy_btn.grid(row=5, column=0, pady=2, sticky="ew")

        self.save_btn = ttk.Button(frame, text="Save DSL...", command=self.on_save,
                                   state="disabled")
        self.save_btn.grid(row=6, column=0, pady=2, sticky="ew")

        self.warn_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.warn_var, wraplength=220,
                  foreground="#b06000").grid(row=7, column=0, pady=(8, 0), sticky="w")

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(frame, textvariable=self.status_var, wraplength=220,
                  foreground="#555").grid(row=8, column=0, pady=(6, 0), sticky="w")

        self.result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.result_var, wraplength=230,
                  font=(FONT_FAMILY, 9, "bold")).grid(
                      row=9, column=0, pady=(6, 0), sticky="w")

        legend = ttk.Frame(frame)
        legend.grid(row=10, column=0, pady=(16, 0), sticky="w")
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

    def _read_inputs(self):
        rects = self._parse_rects()
        if not rects:
            raise ValueError("Enter at least one rectangle.")
        try:
            height = float(self.height_var.get())
            strip_width = float(self.width_var.get())
            frames = int(float(self.frames_var.get()))
            beam_count = int(float(self.beam_count_var.get()))
        except ValueError:
            raise ValueError(
                "Height, strip width, frames, and beam count must be numbers."
            )
        if height <= 0:
            raise ValueError("Height must be a positive number.")
        if strip_width <= 0:
            raise ValueError("Strip width must be a positive number.")
        if strip_width <= TOOTH:
            raise ValueError(
                f"Strip width must be greater than material thickness ({TOOTH:g} mm)."
            )
        if frames < 1:
            raise ValueError("Frames must be an integer >= 1.")
        if beam_count < 1:
            raise ValueError("Beam count must be an integer >= 1.")
        return rects, height, strip_width, frames, beam_count

    def on_generate(self):
        try:
            rects, height, strip_width, frames, beam_count = self._read_inputs()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return

        self.generate_btn.config(state="disabled")
        self.copy_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        self.result_var.set("")
        if abs(strip_width - CELL_SIZE) > 1e-9:
            self.warn_var.set(JOINT_WARNING)
        else:
            self.warn_var.set("")
        self.status_var.set("Generating (packing rails and joints)...")

        def worker():
            try:
                result = build_box(rects, height, strip_width=strip_width,
                                   frames=frames, beam_count=beam_count)
                self.msg_queue.put(("done", result))
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
                    messagebox.showerror("Generate error", payload)
                elif kind == "done":
                    self._apply_result(payload)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(100, self._poll_queue)

    def _apply_result(self, result):
        self.dsl_text = result["dsl"]
        nodes = result["nodes"]
        beams = result["beam_type_counts"]
        hole = result["hole_counts"]
        plain = result["plain_counts"]
        lengths = result["lengths"]
        frames = result["frames"]
        warn = ""
        if result["free_ends"]:
            warn = (f"\n\nWarning: {len(result['free_ends'])} free/dangling "
                    "end(s) found (unbraced, not adjusted).")
        if result.get("warning"):
            self.warn_var.set(result["warning"])
        self.status_var.set("Done.")
        self.result_var.set(
            f"Nodes (per frame): L={nodes['L']}  T={nodes['T']}  +={nodes['P']}\n"
            f"Beams (x{result['beam_count']}): "
            f"L={beams['L']}  T={beams['T']}  +={beams['P']}\n"
            f"Column length: {format_length(result['height'])} mm\n"
            f"Joints with hole: L={hole['L']}  T={hole['T']}  +={hole['P']}\n"
            f"Joints without hole: "
            f"L={plain['L']}  T={plain['T']}  +={plain['P']}\n"
            f"Rails (1 frame): {format_length_list(lengths)}\n"
            f"Rails x {frames}: {len(lengths) * frames} pieces\n"
            f"Total rail length: {format_length(result['total_rail_length'])} mm"
            f"{warn}"
        )
        self.generate_btn.config(state="normal")
        self.copy_btn.config(state="normal")
        self.save_btn.config(state="normal")
        draw_skeleton(self.canvas, result["skeleton"], font_family=FONT_FAMILY)

    def on_copy(self):
        if not self.dsl_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.dsl_text)
        self.root.update()
        self.status_var.set("DSL copied to clipboard.")

    def on_save(self):
        if not self.dsl_text:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".dsl",
            filetypes=[("DSL files", "*.dsl"), ("All files", "*.*")],
            title="Save DSL",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.dsl_text)
        except OSError as e:
            messagebox.showerror("Save error", str(e))
            return
        self.status_var.set(f"Saved {path}")


if __name__ == "__main__":
    root = tk.Tk()
    default_font = (FONT_FAMILY, FONT_SIZE)
    root.option_add("*Font", default_font)
    style = ttk.Style(root)
    style.configure(".", font=default_font)
    app = BoxApp(root)
    root.geometry("1100x720")
    root.mainloop()
