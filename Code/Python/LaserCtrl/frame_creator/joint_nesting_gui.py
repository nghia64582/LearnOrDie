"""
Joint Nesting Tool - GUI

Combines the CP-SAT packing solver with a Tkinter front-end.

Input (via GUI):
  - number of rows (grid height, in 10mm cells)
  - counts for 6 piece variants: L (hole/no-hole), T (hole/no-hole),
    Plus (hole/no-hole)

Output:
  - a .dsl file (ADD/END blocks, same format as the existing designer tool)
  - a canvas preview of the packed layout

Run locally with: python joint_nesting_gui.py
Requires: pip install ortools
"""

import threading
import queue
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:  # allow solver helpers to load headless
    tk = ttk = filedialog = messagebox = None

# DPI awareness is handled once by the app entrypoint (laser_app / main).

# Custom font -- change these two to adjust the whole app's font in one place
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 10

from frame_creator.joint_nesting_solver import (
    SHAPE_COLOR,
    assign_variants,
    build_dsl,
    get_rotated_template,
    solve_min_columns,
    translate_points,
)


class JointNestingApp:
    def __init__(self, root):
        self.root = root
        if hasattr(root, "title"):
            root.title("Joint Nesting Tool")
        self.msg_queue = queue.Queue()
        self.placed_result = None  # list with has_hole/name after solve
        self.grid_cols = None
        self.grid_rows = None

        self._build_input_panel()
        self._build_canvas_panel()
        self.root.after(100, self._poll_queue)

    # ---- UI construction ----
    def _build_input_panel(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="ns")

        self.vars = {}

        def add_row(r, label, key, default):
            ttk.Label(frame, text=label).grid(row=r, column=0, sticky="w", pady=2)
            v = tk.StringVar(value=str(default))
            ttk.Entry(frame, textvariable=v, width=8).grid(row=r, column=1, pady=2)
            self.vars[key] = v

        add_row(0, "Rows (grid height, cells):", "rows", 10)
        add_row(1, "Cell size (mm):", "cell_size", 10)
        ttk.Separator(frame).grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        ttk.Label(frame, text="L-shape:").grid(row=3, column=0, sticky="w")
        add_row(4, "  with hole:", "L_hole", 5)
        add_row(5, "  no hole:", "L_nohole", 5)
        ttk.Label(frame, text="T-shape:").grid(row=6, column=0, sticky="w")
        add_row(7, "  with hole:", "T_hole", 5)
        add_row(8, "  no hole:", "T_nohole", 5)
        ttk.Label(frame, text="Plus-shape:").grid(row=9, column=0, sticky="w")
        add_row(10, "  with hole:", "P_hole", 5)
        add_row(11, "  no hole:", "P_nohole", 5)

        ttk.Separator(frame).grid(row=12, column=0, columnspan=2, sticky="ew", pady=6)
        ttk.Label(frame, text="Time limit / try (s):").grid(row=13, column=0, sticky="w")
        self.time_limit_var = tk.StringVar(value="15")
        ttk.Entry(frame, textvariable=self.time_limit_var, width=8).grid(row=13, column=1)

        self.generate_btn = ttk.Button(frame, text="Generate Layout", command=self.on_generate)
        self.generate_btn.grid(row=14, column=0, columnspan=2, pady=10, sticky="ew")

        self.copy_btn = ttk.Button(frame, text="Copy DSL", command=self.on_copy, state="disabled")
        self.copy_btn.grid(row=15, column=0, columnspan=2, pady=2, sticky="ew")

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(frame, textvariable=self.status_var, wraplength=200,
                  foreground="#555").grid(row=16, column=0, columnspan=2, pady=(10, 0), sticky="w")

        self.result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.result_var, wraplength=200, font=(FONT_FAMILY, 9, "bold")
                  ).grid(row=17, column=0, columnspan=2, pady=(6, 0), sticky="w")

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

    # ---- actions ----
    def _read_inputs(self):
        try:
            rows = int(self.vars["rows"].get())
            cell_size = float(self.vars["cell_size"].get())
            counts_hole = {
                "L": int(self.vars["L_hole"].get()),
                "T": int(self.vars["T_hole"].get()),
                "P": int(self.vars["P_hole"].get()),
            }
            counts_nohole = {
                "L": int(self.vars["L_nohole"].get()),
                "T": int(self.vars["T_nohole"].get()),
                "P": int(self.vars["P_nohole"].get()),
            }
            time_limit = float(self.time_limit_var.get())
        except ValueError:
            raise ValueError("All inputs must be numbers.")
        if rows <= 0:
            raise ValueError("Rows must be positive.")
        if cell_size <= 0:
            raise ValueError("Cell size must be positive.")
        counts_total = {t: counts_hole[t] + counts_nohole[t] for t in ("L", "T", "P")}
        return rows, cell_size, counts_hole, counts_nohole, counts_total, time_limit

    def on_generate(self):
        try:
            rows, cell_size, counts_hole, counts_nohole, counts_total, time_limit = self._read_inputs()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return

        if sum(counts_total.values()) == 0:
            messagebox.showerror("Invalid input", "Enter at least one piece.")
            return

        self.cell_size = cell_size
        self.generate_btn.config(state="disabled")
        self.copy_btn.config(state="disabled")
        self.result_var.set("")
        self.status_var.set("Solving...")

        def worker():
            try:
                def progress(msg):
                    self.msg_queue.put(("status", msg))

                cols, placed = solve_min_columns(
                    counts_total, rows, time_limit_per_try=time_limit,
                    progress_cb=progress)
                placed_full = assign_variants(placed, counts_hole)
                self.msg_queue.put(("done", (rows, cols, placed_full, counts_total)))
            except Exception as e:
                self.msg_queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "status":
                    self.status_var.set(payload)
                elif kind == "error":
                    self.status_var.set("Error.")
                    self.generate_btn.config(state="normal")
                    messagebox.showerror("Solver error", payload)
                elif kind == "done":
                    rows, cols, placed_full, counts_total = payload
                    self.grid_rows, self.grid_cols = rows, cols
                    self.placed_result = placed_full
                    total_cells = sum(v * n for v, n in
                                       zip((3, 4, 5), (counts_total["L"], counts_total["T"], counts_total["P"])))
                    waste = rows * cols - total_cells
                    self.status_var.set("Done.")
                    self.result_var.set(
                        f"Grid: {rows} rows x {cols} cols\n"
                        f"Total pieces: {len(placed_full)}\n"
                        f"Waste: {waste} cells ({100*waste/(rows*cols):.1f}%)")
                    self.generate_btn.config(state="normal")
                    self.copy_btn.config(state="normal")
                    self._draw_canvas()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _draw_canvas(self):
        self.canvas.delete("all")
        cell_size = getattr(self, "cell_size", 10.0)
        scale = 2.5  # px per mm (halved from the original 5)
        margin = 20
        for p in self.placed_result:
            outer, hole, w, h = get_rotated_template(p["type"], p["has_hole"], p["k"], cell_size)
            dx, dy = p["c0"] * cell_size, p["r0"] * cell_size
            outer_t = translate_points(outer, dx, dy)
            pts = [coord * scale + margin for x, y in outer_t for coord in (x, y)]
            self.canvas.create_polygon(*pts, fill=SHAPE_COLOR[p["type"]],
                                        outline="black", width=1.5)
            if hole is not None:
                hole_t = translate_points(hole, dx, dy)
                hpts = [coord * scale + margin for x, y in hole_t for coord in (x, y)]
                self.canvas.create_polygon(*hpts, fill="white", outline="black")
            cx = sum(x for x, y in outer_t) / len(outer_t) * scale + margin
            cy = sum(y for x, y in outer_t) / len(outer_t) * scale + margin
            self.canvas.create_text(cx, cy, text=p["name"], font=(FONT_FAMILY, 7))

        # grid boundary
        gw = self.grid_cols * cell_size * scale + margin * 2
        gh = self.grid_rows * cell_size * scale + margin * 2
        self.canvas.create_rectangle(margin, margin,
                                      self.grid_cols * cell_size * scale + margin,
                                      self.grid_rows * cell_size * scale + margin,
                                      outline="red", width=2)
        self.canvas.config(scrollregion=(0, 0, gw, gh))

    def on_copy(self):
        if not self.placed_result:
            return
        cell_size = getattr(self, "cell_size", 10.0)
        dsl_text = build_dsl(self.placed_result, cell_size)
        self.root.clipboard_clear()
        self.root.clipboard_append(dsl_text)
        self.root.update()  # keep clipboard content after the app loses focus
        self.status_var.set("DSL copied to clipboard.")


if __name__ == "__main__":
    root = tk.Tk()
    default_font = (FONT_FAMILY, FONT_SIZE)
    root.option_add("*Font", default_font)
    style = ttk.Style(root)
    style.configure(".", font=default_font)
    app = JointNestingApp(root)
    root.geometry("1000x700")
    root.mainloop()
