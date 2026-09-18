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

import math
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ortools.sat.python import cp_model

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

# ============================================================================
# 1. Shape definitions -- CELL geometry (used by the packing solver)
# ============================================================================

SHAPES_BASE_CELLS = {
    "L": [(0, 0), (0, 1), (1, 0)],                    # L-tromino (3 cells)
    "T": [(0, 1), (1, 0), (1, 1), (1, 2)],            # T-tetromino (4 cells)
    "P": [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)],    # Plus-pentomino (5 cells)
}

SHAPE_DISPLAY_NAME = {"L": "L-shape", "T": "T-shape", "P": "Plus-shape"}
SHAPE_COLOR = {"L": "#a8d0f0", "T": "#b8e6b0", "P": "#f5c99b"}


def normalize_cells(cells):
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return tuple(sorted((r - min_r, c - min_c) for r, c in cells))


def rotate90_cells(cells):
    max_r = max(r for r, c in cells)
    return [(c, max_r - r) for r, c in cells]


def get_rotations_cells(base_cells):
    """Return list of (k, normalized_cells) for unique rotations, k=0..3
    is the number of 90-deg clockwise rotations that produced this
    orientation (first occurrence kept on duplicates, e.g. Plus)."""
    rotations = []
    seen = set()
    cur = list(base_cells)
    for k in range(4):
        norm = normalize_cells(cur)
        if norm not in seen:
            seen.add(norm)
            rotations.append((k, norm))
        cur = rotate90_cells(cur)
    return rotations


def bbox_cells(cells):
    h = max(r for r, c in cells) + 1
    w = max(c for r, c in cells) + 1
    return h, w


# ============================================================================
# 2. Shape templates -- REAL geometry in mm (outer boundary + optional hole)
#    Taken verbatim from the DSL examples. Used only for DSL/visual output.
# ============================================================================

def parse_points(m_line):
    toks = m_line.split()[1:]
    nums = [float(t) for t in toks]
    return list(zip(nums[0::2], nums[1::2]))


TEMPLATES = {
    "L": {
        "outer": parse_points("M 0 0 20 0 20 10 10 10 10 20 0 20 0 0"),
        "hole":  parse_points("M 3 3 13 3 13 6 6 6 6 13 3 13 3 3"),
    },
    "T": {
        "outer": parse_points("M 10 0 20 0 20 10 30 10 30 20 0 20 0 10 10 10 10 0"),
        "hole":  parse_points("M 10 16.5 10 13.5 13.5 13.5 13.5 6.5 16.5 6.5 16.5 13.5 20 13.5 20 16.5 10 16.5"),
    },
    "P": {
        "outer": parse_points("M 10 0 20 0 20 10 30 10 30 20 20 20 20 30 10 30 10 20 0 20 0 10 10 10 10 0"),
        "hole":  parse_points("M 10 13.5 13.5 13.5 13.5 10 16.5 10 16.5 13.5 20 13.5 20 16.5 16.5 16.5 16.5 20 13.5 20 13.5 16.5 10 16.5 10 13.5"),
    },
}


def rotate_points_90(points, h):
    """One 90-deg clockwise rotation of real-valued points, given the
    current bounding-box height h (mm). Matches the cell rotation exactly:
    (x, y) -> (h - y, x)."""
    return [(h - y, x) for (x, y) in points]


def get_rotated_template(shape_type, has_hole, k, cell_size=10.0):
    """Return (outer_points, hole_points_or_None, width, height) for the
    given shape/variant rotated by k * 90 degrees clockwise, scaled so that
    1 grid cell = cell_size mm (templates are authored for a 10mm cell)."""
    outer = list(TEMPLATES[shape_type]["outer"])
    hole = list(TEMPLATES[shape_type]["hole"]) if has_hole else None

    w = max(x for x, y in outer)
    h = max(y for x, y in outer)

    for _ in range(k):
        outer = rotate_points_90(outer, h)
        if hole is not None:
            hole = rotate_points_90(hole, h)
        w, h = h, w  # dimensions swap after a 90-deg turn

    factor = cell_size / 10.0
    if factor != 1.0:
        outer = [(x * factor, y * factor) for x, y in outer]
        if hole is not None:
            hole = [(x * factor, y * factor) for x, y in hole]
        w, h = w * factor, h * factor

    return outer, hole, w, h


def translate_points(points, dx, dy):
    return [(x + dx, y + dy) for x, y in points]


# ============================================================================
# 3. CP-SAT packing solver
# ============================================================================

def build_placements(shape_rotations, rows, cols):
    placements = {}
    for t, rots in shape_rotations.items():
        for ridx, (k, cells) in enumerate(rots):
            h, w = bbox_cells(cells)
            valid = []
            if h <= rows and w <= cols:
                for r0 in range(rows - h + 1):
                    for c0 in range(cols - w + 1):
                        abs_cells = [(r0 + r, c0 + c) for r, c in cells]
                        valid.append((r0, c0, abs_cells))
            placements[(t, ridx)] = (k, valid)
    return placements


def try_pack(counts, rows, cols, time_limit=20.0):
    """Returns (feasible, placed_list) where placed_list is a list of
    dicts: {"type": "L"/"T"/"P", "k": rotation, "r0": row, "c0": col}."""
    shape_rotations = {t: get_rotations_cells(cells) for t, cells in SHAPES_BASE_CELLS.items()}
    placements = build_placements(shape_rotations, rows, cols)

    model = cp_model.CpModel()
    x = {}
    cell_covers = {(r, c): [] for r in range(rows) for c in range(cols)}

    for (t, ridx), (k, plist) in placements.items():
        for pidx, (r0, c0, abs_cells) in enumerate(plist):
            var = model.NewBoolVar(f"x_{t}_{ridx}_{pidx}")
            x[(t, ridx, pidx)] = (var, k, r0, c0, abs_cells)
            for cell in abs_cells:
                cell_covers[cell].append(var)

    for t, need in counts.items():
        vars_for_type = [v for (tt, ridx, pidx), (v, k, r0, c0, cells) in x.items() if tt == t]
        if not vars_for_type and need > 0:
            return False, None
        model.Add(sum(vars_for_type) == need)

    for cell, vars_here in cell_covers.items():
        if vars_here:
            model.Add(sum(vars_here) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return False, None

    placed = []
    for (t, ridx, pidx), (v, k, r0, c0, abs_cells) in x.items():
        if solver.Value(v):
            placed.append({"type": t, "k": k, "r0": r0, "c0": c0})
    return True, placed


def solve_min_columns(counts, rows, time_limit_per_try=20.0, max_extra_cols=20,
                       progress_cb=None):
    total_cells = 3 * counts["L"] + 4 * counts["T"] + 5 * counts["P"]
    if total_cells == 0:
        return 0, []

    col_lb = max(math.ceil(total_cells / rows), 1)
    max_cols = col_lb + max_extra_cols

    for cols in range(col_lb, max_cols + 1):
        if progress_cb:
            progress_cb(f"Trying cols={cols} ...")
        feasible, placed = try_pack(counts, rows, cols, time_limit=time_limit_per_try)
        if progress_cb:
            progress_cb(f"cols={cols}: {'FEASIBLE' if feasible else 'infeasible'}")
        if feasible:
            return cols, placed

    raise RuntimeError(f"No feasible packing found up to {max_cols} columns")


# ============================================================================
# 4. DSL generation
# ============================================================================

def format_points_line(points):
    flat = []
    for x, y in points:
        # print integers without trailing .0, keep decimals otherwise
        for v in (x, y):
            if float(v).is_integer():
                flat.append(str(int(v)))
            else:
                flat.append(f"{v:g}")
    return "M " + " ".join(flat)


def build_dsl(placed_with_variant, cell_size=10.0):
    """placed_with_variant: list of dicts with type, k, r0, c0, has_hole, name

    NOTE: the M-line coordinates stay in the shape's own LOCAL frame (just
    the rotated template, untranslated) -- the ADD line's (x, y) is the
    only placement offset. The downstream designer tool applies ADD's
    offset to the M points itself, so translating both here would double
    up the offset.
    """
    lines = []
    for p in placed_with_variant:
        outer, hole, w, h = get_rotated_template(p["type"], p["has_hole"], p["k"], cell_size)
        dx, dy = p["c0"] * cell_size, p["r0"] * cell_size
        outer_closed = outer + [outer[0]]
        lines.append(f'ADD {dx:g} {dy:g} {p["name"]}')
        lines.append(format_points_line(outer_closed))
        if hole is not None:
            hole_closed = hole + [hole[0]]
            lines.append(format_points_line(hole_closed))
        lines.append("END")
    return "\n".join(lines) + "\n"


def assign_variants(placed, hole_counts):
    """
    placed: list of {"type","k","r0","c0"} from solver.
    hole_counts: dict type -> number that should have a hole (rest = no hole)
    Returns new list with "has_hole" and unique "name" added.
    Placement order (reading order top-to-bottom, left-to-right) determines
    which instances get the hole variant -- purely a deterministic, stable
    assignment since hole vs no-hole doesn't affect packing.
    """
    by_type = {}
    for p in placed:
        by_type.setdefault(p["type"], []).append(p)
    for t, items in by_type.items():
        items.sort(key=lambda p: (p["r0"], p["c0"]))

    result = []
    counters = {"L": 0, "T": 0, "P": 0}
    for t, items in by_type.items():
        n_hole = hole_counts.get(t, 0)
        for i, p in enumerate(items):
            counters[t] += 1
            has_hole = i < n_hole
            variant = "hole" if has_hole else "nohole"
            name = f"{t.lower()}-{variant}-{counters[t]}"
            result.append({**p, "has_hole": has_hole, "name": name})
    return result


# ============================================================================
# 5. Tkinter GUI
# ============================================================================

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
