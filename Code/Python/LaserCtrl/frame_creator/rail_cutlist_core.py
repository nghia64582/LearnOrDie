"""
Rail cut-list 2D packing optimizer.

Each rail is a rectangle of fixed width (RAIL_WIDTH, default 10mm) and a
given length. To minimize the total sheet WIDTH used (the "number of
columns"), rails can be:
  - stacked vertically within the same column (multiple rails sharing one
    10mm-wide lane, e.g. two 50mm rails stacked = 100mm, same height as
    one 100mm rail)
  - rotated 90 degrees (laid on its side, occupying `length` mm of width
    and only `RAIL_WIDTH` mm of height) to fill leftover horizontal gaps

This is a 2D strip-packing problem with free rotation, fixed strip height
H = max(lengths) (the longest single rail sets the sheet height -- it must
fit somehow, and using it upright is always at least as good as any
alternative for the piece that defines H). Solved via CP-SAT's NoOverlap2D.
"""

from ortools.sat.python import cp_model


def _decimals(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return len(s.split(".")[1]) if "." in s else 0


def optimize_layout(lengths, rail_width=10.0, time_limit=15.0):
    """lengths: list of positive floats (mm). Returns (placements, total_width, height).
    placements: list of dicts {length, rotated, x, y, w, h} in original mm units."""
    if not lengths:
        return [], 0.0, 0.0

    max_dec = max(max((_decimals(v) for v in lengths), default=0), _decimals(rail_width))
    scale = 10 ** max_dec

    L = [round(v * scale) for v in lengths]
    RW = round(rail_width * scale)
    H = max(L)
    n = len(L)

    model = cp_model.CpModel()
    xs, ys, ws, hs, rots = [], [], [], [], []
    x_intervals, y_intervals = [], []
    W_UB = sum(L) + n * RW  # loose but safe upper bound

    for i in range(n):
        rot = model.NewBoolVar(f"rot_{i}")
        lo, hi = min(RW, L[i]), max(RW, L[i])
        w = model.NewIntVar(lo, hi, f"w_{i}")
        h = model.NewIntVar(lo, hi, f"h_{i}")
        model.Add(w == RW).OnlyEnforceIf(rot.Not())
        model.Add(w == L[i]).OnlyEnforceIf(rot)
        model.Add(h == L[i]).OnlyEnforceIf(rot.Not())
        model.Add(h == RW).OnlyEnforceIf(rot)

        x = model.NewIntVar(0, W_UB, f"x_{i}")
        y = model.NewIntVar(0, H, f"y_{i}")
        model.Add(y + h <= H)

        x_end = model.NewIntVar(0, W_UB, f"xend_{i}")
        y_end = model.NewIntVar(0, H, f"yend_{i}")
        model.Add(x_end == x + w)
        model.Add(y_end == y + h)

        x_intervals.append(model.NewIntervalVar(x, w, x_end, f"xi_{i}"))
        y_intervals.append(model.NewIntervalVar(y, h, y_end, f"yi_{i}"))
        xs.append(x); ys.append(y); ws.append(w); hs.append(h); rots.append(rot)

    model.AddNoOverlap2D(x_intervals, y_intervals)

    total_width = model.NewIntVar(0, W_UB, "total_width")
    model.AddMaxEquality(total_width, [xs[i] + ws[i] for i in range(n)])
    model.Minimize(total_width)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("No feasible layout found")

    placements = []
    for i in range(n):
        placements.append({
            "length": lengths[i],
            "rotated": bool(solver.Value(rots[i])),
            "x": solver.Value(xs[i]) / scale,
            "y": solver.Value(ys[i]) / scale,
            "w": solver.Value(ws[i]) / scale,
            "h": solver.Value(hs[i]) / scale,
        })
    return placements, solver.Value(total_width) / scale, H / scale


def build_rail_dsl(placements, rail_width=10.0):
    """Each rail's own outline is always a plain rectangle; only its
    placement (position + w/h swap for rotation) differs on the sheet."""
    lines = []
    for i, p in enumerate(placements, start=1):
        name = f"rail-{i}"
        w, h = p["w"], p["h"]
        pts = [(0, 0), (0, h), (w, h), (w, 0), (0, 0)]

        def g(v):
            return str(int(v)) if float(v).is_integer() else f"{v:g}"

        lines.append(f"ADD {g(p['x'])} {g(p['y'])} {name}")
        lines.append("P " + " ".join(g(v) for pt in pts for v in pt))
        lines.append("END")
    return "\n".join(lines) + "\n"