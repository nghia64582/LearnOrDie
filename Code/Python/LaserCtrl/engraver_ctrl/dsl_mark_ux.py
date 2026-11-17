"""Geometry helpers for the Custom-tab Mark joint drag UX.

Snapping, piece ownership, and pairing live here so they can be unit-tested
without Tk. The J line format and Apply joints expansion stay in dsl_joint.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engraver_ctrl.dsl_joint import (
    THICKNESS,
    JointMark,
    classify_mark,
    fmt_num,
    group_marks,
    mark_axes,
    next_joint_name,
    parse_joint_file,
)

# Grid step (mm) used while dragging. The post-drag dialog may use any value.
SNAP_GRID = 1.0
# Snap a pointer onto an axis-aligned outline edge within this distance (mm).
EDGE_SNAP_MM = 3.0
# Treat a point this close to a boundary as inside the piece.
CONTAIN_TOL = 1.0
MIN_LENGTH = 1.0


@dataclass
class Piece:
    add_line: int
    add_dx: float
    add_dy: float
    depth: int
    polygons: list = field(default_factory=list)  # world-space rings
    circles: list = field(default_factory=list)   # world (cx, cy, r)
    # world HV edges: ((x1, y1), (x2, y2), inward_nx, inward_ny)
    edges: list = field(default_factory=list)

    @property
    def area(self):
        total = 0.0
        for poly in self.polygons:
            total += abs(_shoelace(poly))
        for _cx, _cy, r in self.circles:
            total += 3.141592653589793 * r * r
        return total


@dataclass
class MarkDraft:
    add_line: int
    x: float
    y: float
    w: float
    h: float
    name: str
    along_x: bool
    length: float
    on_edge: bool
    world_x: float
    world_y: float
    world_w: float
    world_h: float
    copied_length: bool = False
    valid: bool = True
    message: str = ""

    @property
    def local_rect(self):
        return self.x, self.y, self.w, self.h

    @property
    def world_rect(self):
        return self.world_x, self.world_y, self.world_w, self.world_h


def snap_grid(value, step=SNAP_GRID):
    """Round *value* to the nearest multiple of *step* (away from ties)."""
    step = float(step)
    if step <= 0:
        return float(value)
    q = float(value) / step
    # Avoid banker's rounding so 0.5 mm always goes to the next millimetre.
    if q >= 0:
        return int(q + 0.5) * step
    return int(q - 0.5) * step


def pending_unpaired_mark(marks):
    """Most recently written unpaired (non-ROTATE) mark, or None."""
    groups = group_marks(marks)
    unpaired = []
    for _name, items in groups.items():
        active = [m for m in items if not m.in_rotate]
        if len(active) == 1:
            unpaired.append(active[0])
    if not unpaired:
        return None
    unpaired.sort(key=lambda m: m.line, reverse=True)
    return unpaired[0]


def suggested_joint_name(marks):
    """Pending unpaired name, otherwise the next automatic J1, J2, ... name."""
    pending = pending_unpaired_mark(marks)
    if pending is not None:
        return pending.name
    return next_joint_name(marks)


def collect_pieces(text):
    """Closed outlines per ADD, in world coordinates (ROTATE blocks skipped)."""
    pieces = {}
    stack = []  # (dx, dy, add_line or None, is_rotate)
    for lineno, raw in _iter_cmds(text):
        parts = raw.strip().split()
        cmd = parts[0]
        if cmd == "ADD":
            if len(parts) < 3:
                continue
            try:
                dx, dy = float(parts[1]), float(parts[2])
            except ValueError:
                continue
            stack.append((dx, dy, lineno, False))
            add_n = sum(1 for e in stack if e[2] is not None)
            pieces[lineno] = Piece(
                add_line=lineno,
                add_dx=sum(e[0] for e in stack),
                add_dy=sum(e[1] for e in stack),
                depth=add_n - 1,
            )
            continue
        if cmd == "ROTATE":
            stack.append((0.0, 0.0, None, True))
            continue
        if cmd == "END":
            if stack:
                stack.pop()
            continue
        if any(e[3] for e in stack):
            continue
        add_entries = [e for e in stack if e[2] is not None]
        if not add_entries:
            continue
        add_line = add_entries[-1][2]
        piece = pieces.get(add_line)
        if piece is None:
            continue
        dx, dy = piece.add_dx, piece.add_dy
        try:
            nums = list(map(float, parts[1:]))
        except ValueError:
            continue
        if cmd == "R" and len(nums) == 4:
            x, y, w, h = nums
            poly = _shift_poly(
                [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], dx, dy,
            )
            piece.polygons.append(poly)
            piece.edges.extend(_hv_edges(poly))
        elif cmd == "RC" and len(nums) == 4:
            cx, cy, w, h = nums
            x, y = cx - w / 2, cy - h / 2
            poly = _shift_poly(
                [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], dx, dy,
            )
            piece.polygons.append(poly)
            piece.edges.extend(_hv_edges(poly))
        elif cmd == "P" and len(nums) >= 6 and len(nums) % 2 == 0:
            pts = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
            poly = _shift_poly(pts, dx, dy)
            piece.polygons.append(poly)
            piece.edges.extend(_hv_edges(poly))
        elif cmd == "C" and len(nums) >= 3:
            cx, cy, r = nums[0], nums[1], nums[2]
            if r > 0:
                piece.circles.append((cx + dx, cy + dy, r))
    return [p for p in pieces.values() if p.polygons or p.circles]


def owning_piece(pieces, wx, wy, tol=CONTAIN_TOL):
    """Smallest piece containing (wx, wy). Tie-break: deeper, then later ADD."""
    hits = [p for p in pieces if point_in_piece(p, wx, wy, tol)]
    if not hits:
        return None
    hits.sort(key=lambda p: (p.area, -p.depth, -p.add_line))
    return hits[0]


def point_in_piece(piece, wx, wy, tol=CONTAIN_TOL):
    for poly in piece.polygons:
        if _point_in_poly(wx, wy, poly) or _dist_to_poly(wx, wy, poly) <= tol:
            return True
    for cx, cy, r in piece.circles:
        if (wx - cx) ** 2 + (wy - cy) ** 2 <= (r + tol) ** 2:
            return True
    return False


def draft_from_drag(
    piece, x0, y0, x1, y1, *,
    marks=None, name=None, thickness=THICKNESS,
    grid=SNAP_GRID, edge_snap=EDGE_SNAP_MM,
):
    """Build a snapped J-mark draft for a drag on *piece*.

    Thickness is always *thickness*. Length is the dragged span (1 mm grid)
    unless a pending unpaired mark exists, in which case that length is copied.
    A nearby HV outline edge wins over free placement; the rectangle sits
    flush inside the piece, touching the edge.
    """
    if piece is None:
        return None
    marks = marks or []
    pending = pending_unpaired_mark(marks)
    copied = pending is not None
    pending_length = None
    pending_along_x = None
    if pending is not None:
        pending_along_x, pending_length, _th, _x, _y = mark_axes(pending)
    if not name:
        name = pending.name if pending is not None else suggested_joint_name(marks)

    edge = _pick_edge(piece, x0, y0, x1, y1, edge_snap)
    if edge is not None:
        draft = _draft_on_edge(
            piece, edge, x0, y0, x1, y1,
            thickness=thickness, grid=grid,
            pending_length=pending_length, name=name,
        )
    else:
        draft = _draft_interior(
            piece, x0, y0, x1, y1,
            thickness=thickness, grid=grid,
            pending_length=pending_length,
            pending_along_x=pending_along_x, name=name,
        )
    draft.copied_length = copied
    if draft.length + 1e-9 < MIN_LENGTH and not copied:
        draft.valid = False
        draft.message = "Mark joint: drag was too small"
    return draft


def apply_dialog_values(draft, x, y, length, name, thickness=THICKNESS):
    """Rebuild a draft from dialog fields (no grid snap; thickness fixed)."""
    try:
        x = float(x)
        y = float(y)
        length = float(length)
    except (TypeError, ValueError):
        return None, "x, y, and length must be numbers."
    name = (name or "").strip()
    if not name:
        return None, "Name is required."
    if length <= 0:
        return None, "Length must be positive."
    if draft.copied_length:
        length = draft.length
    along_x = draft.along_x
    w, h = (length, thickness) if along_x else (thickness, length)
    add_dx = draft.world_x - draft.x
    add_dy = draft.world_y - draft.y
    updated = MarkDraft(
        add_line=draft.add_line,
        x=x, y=y, w=w, h=h, name=name,
        along_x=along_x, length=length,
        on_edge=draft.on_edge,
        world_x=x + add_dx, world_y=y + add_dy, world_w=w, world_h=h,
        copied_length=draft.copied_length, valid=True,
    )
    return updated, None


def pair_placement_error(draft, marks, outlines):
    """If this draft would complete a both-interior pair, return a message."""
    if draft is None or draft.on_edge:
        return None
    partner = None
    for m in marks:
        if m.in_rotate:
            continue
        if m.name == draft.name:
            partner = m
    if partner is None:
        return None
    # A lone existing mark with this name is the partner; if more than one
    # already exists the apply step will reject the group anyway.
    same = [m for m in marks if m.name == draft.name and not m.in_rotate]
    if len(same) != 1:
        return None
    kind, _o, _s = classify_mark(same[0], outlines)
    if kind == "interior":
        return (
            f"Joint '{draft.name}' would have both marks in the interior; "
            "one mark must lie on an edge (male tenon)."
        )
    return None



def refresh_on_edge(draft, outlines):
    """Update draft.on_edge from the current rectangle vs piece outlines."""
    mark = JointMark(
        line=0, x=draft.x, y=draft.y, w=draft.w, h=draft.h,
        name=draft.name, role=None, add_line=draft.add_line,
        add_dx=draft.world_x - draft.x, add_dy=draft.world_y - draft.y,
        in_rotate=False, raw="",
    )
    kind, _o, _s = classify_mark(mark, outlines)
    draft.on_edge = kind == "edge"
    return draft


def format_draft_label(draft):
    """Short live caption shown next to the cursor while dragging."""
    if draft is None:
        return ""
    kind = "edge" if draft.on_edge else "interior"
    return (
        f"{draft.name}  x={fmt_num(draft.x)} y={fmt_num(draft.y)}  "
        f"L={fmt_num(draft.length)}  {kind}"
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _iter_cmds(text):
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        yield lineno, raw


def _shift_poly(pts, dx, dy):
    return [(p[0] + dx, p[1] + dy) for p in pts]


def _shoelace(poly):
    n = len(poly)
    if n < 3:
        return 0.0
    acc = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        acc += x1 * y2 - x2 * y1
    return acc / 2.0


def _hv_edges(poly):
    n = len(poly)
    if n < 3:
        return []
    area = _shoelace(poly)
    # CCW (positive area): interior is to the left of each directed edge.
    sign = 1.0 if area >= 0 else -1.0
    edges = []
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            continue
        if abs(dy) < 1e-9:
            # Horizontal: left normal is (0, sign) if going +x.
            nx, ny = 0.0, sign * (1.0 if dx > 0 else -1.0)
            edges.append(((ax, ay), (bx, by), nx, ny))
        elif abs(dx) < 1e-9:
            # Vertical: left normal is (-sign, 0) if going +y.
            nx, ny = sign * (-1.0 if dy > 0 else 1.0), 0.0
            edges.append(((ax, ay), (bx, by), nx, ny))
    return edges


def _point_to_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 < 1e-18:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5, 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5, t


def _point_in_poly(px, py, poly):
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py):
            xint = (xj - xi) * (py - yi) / ((yj - yi) or 1e-18) + xi
            if px < xint:
                inside = not inside
        j = i
    return inside


def _dist_to_poly(px, py, poly):
    n = len(poly)
    if n < 2:
        return float("inf")
    best = float("inf")
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        d, _t = _point_to_segment(px, py, ax, ay, bx, by)
        if d < best:
            best = d
    return best


def _pick_edge(piece, x0, y0, x1, y1, max_dist):
    hits = []
    for a, b, nx, ny in piece.edges:
        d0, _t0 = _point_to_segment(x0, y0, a[0], a[1], b[0], b[1])
        d1, _t1 = _point_to_segment(x1, y1, a[0], a[1], b[0], b[1])
        dist = min(d0, d1)
        if dist <= max_dist + 1e-12:
            hits.append((dist, d0, a, b, nx, ny))
    if not hits:
        return None
    dx, dy = x1 - x0, y1 - y0
    drag_len = (dx * dx + dy * dy) ** 0.5
    clearly = drag_len >= MIN_LENGTH

    chosen = []
    for item in hits:
        dist, d0, a, b, nx, ny = item
        horizontal = abs(a[1] - b[1]) < 1e-9
        align = abs(dx) if horizontal else abs(dy)
        cross = abs(dy) if horizontal else abs(dx)
        # A clearly orthogonal drag is free placement, not a snap onto
        # the nearby cross edge (e.g. an interior horizontal stroke 2 mm
        # from a vertical side).
        if clearly and align + 1e-9 < cross:
            continue
        chosen.append((align, d0, dist, a, b, nx, ny))
    if not chosen:
        return None

    def score(item):
        align, d0, dist, _a, _b, _nx, _ny = item
        if clearly:
            return (-align, d0, dist)
        return (d0, dist, -align)

    chosen.sort(key=score)
    _align, _d0, _dist, a, b, nx, ny = chosen[0]
    return a, b, nx, ny


def _draft_on_edge(piece, edge, x0, y0, x1, y1, *,
                   thickness, grid, pending_length, name):
    a, b, nx, ny = edge
    horizontal = abs(a[1] - b[1]) < 1e-9
    if horizontal:
        y_edge = a[1]
        lo, hi = min(a[0], b[0]), max(a[0], b[0])
        start = snap_grid(x0, grid)
        end = snap_grid(x1, grid)
        span_lo, span_hi, length = _span_on_edge(
            start, end, lo, hi, pending_length, grid,
        )
        if ny < 0:
            world_y = y_edge - thickness
        else:
            world_y = y_edge
        world_x = span_lo
        world_w, world_h = length, thickness
        along_x = True
    else:
        x_edge = a[0]
        lo, hi = min(a[1], b[1]), max(a[1], b[1])
        start = snap_grid(y0, grid)
        end = snap_grid(y1, grid)
        span_lo, span_hi, length = _span_on_edge(
            start, end, lo, hi, pending_length, grid,
        )
        if nx < 0:
            world_x = x_edge - thickness
        else:
            world_x = x_edge
        world_y = span_lo
        world_w, world_h = thickness, length
        along_x = False
    x = world_x - piece.add_dx
    y = world_y - piece.add_dy
    return MarkDraft(
        add_line=piece.add_line,
        x=x, y=y, w=world_w, h=world_h, name=name,
        along_x=along_x, length=length, on_edge=True,
        world_x=world_x, world_y=world_y,
        world_w=world_w, world_h=world_h,
    )


def _span_on_edge(start, end, lo, hi, pending_length, grid):
    if pending_length is not None:
        length = float(pending_length)
        direction = 1.0 if end >= start else -1.0
        # No meaningful drag: extend in the + direction along the edge.
        if abs(end - start) < 1e-9:
            direction = 1.0
        if direction >= 0:
            span_lo, span_hi = start, start + length
        else:
            span_hi, span_lo = start, start - length
        if length <= hi - lo + 1e-9:
            if span_lo < lo:
                span_lo, span_hi = lo, lo + length
            elif span_hi > hi:
                span_hi, span_lo = hi, hi - length
        else:
            # Longer than the edge: pin to the start of the edge.
            if direction >= 0:
                span_lo, span_hi = lo, lo + length
            else:
                span_hi, span_lo = hi, hi - length
        return span_lo, span_hi, length
    raw = abs(end - start)
    length = max(0.0, snap_grid(raw, grid))
    if end < start:
        span_lo, span_hi = start - length, start
    else:
        span_lo, span_hi = start, start + length
    # Keep as much of the span as possible on the edge.
    if length <= hi - lo + 1e-9 and length > 0:
        if span_lo < lo:
            span_lo, span_hi = lo, lo + length
        elif span_hi > hi:
            span_hi, span_lo = hi, hi - length
    return span_lo, span_hi, length


def _draft_interior(piece, x0, y0, x1, y1, *,
                    thickness, grid, pending_length, pending_along_x, name):
    sx, sy = snap_grid(x0, grid), snap_grid(y0, grid)
    ex, ey = snap_grid(x1, grid), snap_grid(y1, grid)
    if pending_length is not None and pending_along_x is not None:
        along_x = pending_along_x
        length = float(pending_length)
    else:
        along_x = abs(ex - sx) >= abs(ey - sy)
        length = abs(ex - sx) if along_x else abs(ey - sy)
        length = max(0.0, snap_grid(length, grid))
    if along_x:
        if pending_length is not None:
            world_x = sx if ex >= sx else sx - length
        else:
            world_x = min(sx, ex)
        world_y = _prefer_inside_y(piece, world_x, sy, length, thickness)
        world_w, world_h = length, thickness
    else:
        if pending_length is not None:
            world_y = sy if ey >= sy else sy - length
        else:
            world_y = min(sy, ey)
        world_x = _prefer_inside_x(piece, sx, world_y, thickness, length)
        world_w, world_h = thickness, length
    x = world_x - piece.add_dx
    y = world_y - piece.add_dy
    return MarkDraft(
        add_line=piece.add_line,
        x=x, y=y, w=world_w, h=world_h, name=name,
        along_x=along_x, length=length, on_edge=False,
        world_x=world_x, world_y=world_y,
        world_w=world_w, world_h=world_h,
    )


def _corners_inside(piece, x, y, w, h):
    pts = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    return sum(1 for px, py in pts if point_in_piece(piece, px, py, tol=0.05))


def _prefer_inside_y(piece, world_x, sy, length, thickness):
    """Choose a grid-aligned y so the 3 mm strip stays inside the piece.

    Keep the snapped start y when it already sits fully inside.
    """
    return _prefer_inside_axis(
        piece, sy,
        lambda y: (world_x, y, length, thickness),
    )


def _prefer_inside_x(piece, sx, world_y, thickness, length):
    return _prefer_inside_axis(
        piece, sx,
        lambda x: (x, world_y, thickness, length),
    )


def _prefer_inside_axis(piece, start, rect_at):
    candidates = [start, start - THICKNESS, snap_grid(start - THICKNESS / 2)]
    scored = []
    for i, value in enumerate(candidates):
        x, y, w, h = rect_at(value)
        inside = _corners_inside(piece, x, y, w, h)
        # More corners inside wins; ties keep the original start (index 0).
        scored.append((-inside, i, value))
    scored.sort()
    return scored[0][2]


