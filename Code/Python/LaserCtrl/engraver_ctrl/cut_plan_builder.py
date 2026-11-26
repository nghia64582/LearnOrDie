from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from engraver_ctrl.cut_handler import pack_pieces

_TOL = 1e-9
CUT_EXTRA_MARGIN = 1.0  # mm overcut on each side of a stick


@dataclass
class Part:
    """One piece to cut from a stick.

    - length: finished piece length along the stick (mm)
    - is_cut_down: convex rounded cap at the bottom (low-Y) end
    - is_cut_up: convex rounded cap at the top (high-Y) end
    - hole_centers: hole positions (mm) measured from the bottom of the piece
    """
    length: float
    is_cut_down: bool
    is_cut_up: bool
    hole_centers: List[float]


@dataclass
class Placement:
    """A part laid out on one stick."""
    part_index: int
    stick_index: int
    y_start: float
    y_end: float
    length: float
    is_cut_down: bool
    is_cut_up: bool
    hole_centers: List[float]


@dataclass
class StickLayout:
    """One physical stick on the bed."""
    index: int
    x_left: float
    width: float
    length: float
    placements: List[Placement] = field(default_factory=list)
    waste: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class CutPlan:
    """Cutting plan plus layout used by the preview canvas.

    Coordinate frame (r = width/2, L = stock_length):
    the physical stick occupies y in [-r, L-r]. The bottom factory
    semicircle has its centre on y=0 and fills [-r, 0]; the top
    factory semicircle has its centre at L-2r and fills [L-2r, L-r].
    A straight cut at y=0 (1 mm overcut each side) always severs
    the bottom cap, so packing uses the remaining span [0, L-r]
    (usable_length = L-r).

    - cuts: (start_x, y, length_of_cut) horizontal G-code cuts
    - holes: (center_x, center_y)
    - arches: (center_x, center_y, bulge_up)
        A convex stadium cap of radius width/2.
        bulge_up False => rounded bottom: centre at y0 + W/2, arc
            spans y0 .. y0+W/2 and bulges down (apex on the y0 cut).
        bulge_up True  => rounded top: centre at y1 - W/2, arc
            spans y1-W/2 .. y1 and bulges up (apex on the y1 cut).
    """
    stick_width: float
    cuts: List[Tuple[float, float, float]]
    holes: List[Tuple[float, float]]
    radius: float
    arches: List[Tuple[float, float, bool]]
    stock_length: float = 0.0
    usable_length: float = 0.0
    gap: float = 0.0
    sticks: List[StickLayout] = field(default_factory=list)
    unplaced: List[int] = field(default_factory=list)
    parts: List[Part] = field(default_factory=list)

    def used_length(self) -> float:
        return sum(p.length for s in self.sticks for p in s.placements)

    def waste_length(self) -> float:
        return sum(b - a for s in self.sticks for a, b in s.waste)

    def waste_percent(self) -> float:
        total = self.stock_length * len(self.sticks)
        if total <= _TOL:
            return 0.0
        return 100.0 * self.waste_length() / total

    def __str__(self):
        s = "CutPlan:\n"
        s += f"Stick Width: {self.stick_width:.3f}\n"
        s += f"Stock Length: {self.stock_length:.3f}\n"
        s += f"Usable Length: {self.usable_length:.3f}\n"
        s += f"Sticks: {len(self.sticks)}\n"
        s += "Cuts:\n"
        for (sx, y, length) in self.cuts:
            s += f"  StartX: {sx:.3f}, Y: {y:.3f}, Length: {length:.3f}\n"
        s += "Holes:\n"
        for (cx, cy) in self.holes:
            s += f"  CenterX: {cx:.3f}, CenterY: {cy:.3f}\n"
        s += f"Radius: {self.radius:.3f}\n"
        s += "Arches:\n"
        for (cx, cy, bulge_up) in self.arches:
            dir_str = "bulge +Y" if bulge_up else "bulge -Y"
            s += f"  CenterX: {cx:.3f}, CenterY: {cy:.3f}, {dir_str}\n"
        if self.unplaced:
            s += f"Unplaced: {self.unplaced}\n"
        return s


def usable_length(stock_length: float, width: float) -> float:
    """Packing capacity after the y=0 cut removes the bottom cap.

    The physical stick occupies y in [-r, L-r] with r = width/2.
    The bottom factory semicircle (centre y=0, y in [-r, 0]) is
    always cut off, so pieces are packed in [0, L-r] and the
    capacity is L-r. The top factory semicircle (centre L-2r)
    remains in that usable span and can be reused by a piece that
    ends at y = L-r.
    """
    return float(stock_length) - float(width) / 2.0


def stick_y_bounds(stock_length: float, width: float) -> Tuple[float, float]:
    """Return (y_min, y_max) of the physical stick: (-r, L-r)."""
    r = float(width) / 2.0
    return -r, float(stock_length) - r


def merge_intervals(
    spans: Sequence[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """Merge overlapping or touching [a, b] intervals."""
    ordered = sorted(
        (float(a), float(b)) for a, b in spans if b > a + _TOL
    )
    if not ordered:
        return []
    out = [ordered[0]]
    for a, b in ordered[1:]:
        pa, pb = out[-1]
        if a <= pb + _TOL:
            out[-1] = (pa, max(pb, b))
        else:
            out.append((a, b))
    return out


def parse_parts_text(txt: str) -> List[Part]:
    """Parse the Small parts text format.

    One piece per line:
        length, round_bottom, round_top[, hole1, hole2, ...]
    round_bottom / round_top must be 0 or 1. Hole positions are mm
    from the bottom of the piece. Blank lines and # comments are ignored.
    """
    parts: List[Part] = []
    for lineno, raw in enumerate(txt.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = [t.strip() for t in line.split(",")]
        if len(tokens) < 3:
            raise ValueError(
                f"Line {lineno}: expected 'length, round_bottom, round_top[, holes...]', "
                f"got {raw!r}"
            )
        try:
            length = float(tokens[0])
        except ValueError as e:
            raise ValueError(f"Line {lineno}: invalid length {tokens[0]!r}") from e
        if length <= _TOL:
            raise ValueError(f"Line {lineno}: length must be positive")

        def _flag(value: str, name: str) -> bool:
            if value not in ("0", "1"):
                raise ValueError(
                    f"Line {lineno}: {name} must be 0 or 1, got {value!r}"
                )
            return value == "1"

        is_cut_down = _flag(tokens[1], "round_bottom")
        is_cut_up = _flag(tokens[2], "round_top")
        hole_centers: List[float] = []
        for h in tokens[3:]:
            if h == "":
                continue
            try:
                hole_centers.append(float(h))
            except ValueError as e:
                raise ValueError(f"Line {lineno}: invalid hole {h!r}") from e
        parts.append(Part(
            length=length,
            is_cut_down=is_cut_down,
            is_cut_up=is_cut_up,
            hole_centers=hole_centers,
        ))
    return parts


def format_parts_text(parts: Sequence[Part]) -> str:
    """Serialize parts back to the text format (one piece per line)."""
    lines = []
    for p in parts:
        flags = f"{p.length:g}, {int(bool(p.is_cut_down))}, {int(bool(p.is_cut_up))}"
        if p.hole_centers:
            holes = ", ".join(f"{h:g}" for h in p.hole_centers)
            flags = f"{flags}, {holes}"
        lines.append(flags)
    return "\n".join(lines)


def parse_hole_field(text: str) -> List[float]:
    """Parse a card hole field: commas and/or whitespace separated numbers."""
    raw = text.replace(",", " ").split()
    holes: List[float] = []
    for tok in raw:
        holes.append(float(tok))
    return holes


def format_hole_field(holes: Sequence[float]) -> str:
    return ", ".join(f"{h:g}" for h in holes)


def arrange_bin(
    indices: Sequence[int],
    parts: Sequence[Part],
    usable: float,
) -> Tuple[List[int], float]:
    """Order pieces on one stick and choose where leftover waste goes.

    Usable span is [0, usable] with usable = L-r. Leftover is a
    single block in that span. The factory bottom cap below y=0
    is always waste and is not part of this arrangement.

    - If any piece wants a rounded top and leftover > 0, put waste
      at the bottom of the usable span so the last piece ends at
      y = L-r and can reuse the factory top semicircle.
    - Otherwise put waste at the top (first piece starts at Y=0).
    - Prefer a round-top piece at the factory top when the used
      span reaches y = L-r.

    Returns (ordered_indices, y_start_of_first_piece).
    """
    items = list(indices)
    if not items:
        return [], 0.0
    used = sum(float(parts[i].length) for i in items)
    leftover = max(0.0, float(usable) - used)
    has_up = any(parts[i].is_cut_up for i in items)
    waste_at_bottom = leftover > _TOL and has_up
    y0 = leftover if waste_at_bottom else 0.0

    def take(pred) -> Optional[int]:
        for pos, idx in enumerate(items):
            if pred(parts[idx]):
                return items.pop(pos)
        return None

    ordered: List[int] = []
    last = None
    end_reaches_stock = abs((y0 + used) - float(usable)) <= _TOL
    if end_reaches_stock:
        last = take(lambda p: p.is_cut_up and not p.is_cut_down)
        if last is None:
            last = take(lambda p: p.is_cut_up)

    # Keep remaining pieces in pack order (stable, already by FFD/BFD).
    ordered.extend(items)
    if last is not None:
        ordered.append(last)
    return ordered, y0


def rounded_end_arches(
    x_center: float,
    y_start: float,
    y_end: float,
    width: float,
    is_cut_down: bool,
    is_cut_up: bool,
) -> List[Tuple[float, float, bool]]:
    """Return (center_x, center_y, bulge_up) caps for one piece.

    The cap is convex (stadium-like): the semicircle's apex sits on the
    nearest end (y_start or y_end) and bulges toward that end, not into
    a concave notch in the piece.
    """
    r = width / 2.0
    out: List[Tuple[float, float, bool]] = []
    if is_cut_down:
        # Centre in the piece, apex at y_start, bulge toward -Y.
        out.append((x_center, y_start + r, False))
    if is_cut_up:
        out.append((x_center, y_end - r, True))
    return out


def arch_apex_y(center_y: float, bulge_up: bool, width: float) -> float:
    r = width / 2.0
    return center_y + r if bulge_up else center_y - r


def arch_polyline(
    cx: float,
    cy: float,
    radius: float,
    bulge_up: bool,
    n: int = 18,
) -> List[Tuple[float, float]]:
    """Points from the left diameter end to the right, along the cap.

    Matches G-code: start (cx - r, cy) -> end (cx + r, cy).
    bulge_up True  travels through (cx, cy + r) (G2, CW, Y up).
    bulge_up False travels through (cx, cy - r) (G3, CCW, Y up).
    """
    a0 = math.pi
    a1 = 0.0 if bulge_up else (2.0 * math.pi)
    pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    return pts


def piece_polygon(
    x_left: float,
    width: float,
    y_start: float,
    y_end: float,
    round_bottom: bool,
    round_top: bool,
    n: int = 16,
) -> List[Tuple[float, float]]:
    """Outline of a finished piece, with convex caps when flagged.

    Walks left side (top to bottom), bottom end, right side (bottom to
    top), then the top end, so the fill matches the cut shape.
    """
    r = width / 2.0
    cx = x_left + r
    left, right = x_left, x_left + width
    y_start = float(y_start)
    y_end = float(y_end)
    if y_end <= y_start + 1e-12:
        return []

    def cap(cy: float, bulge_up: bool, reverse: bool = False):
        pts = arch_polyline(cx, cy, r, bulge_up, n=n)
        return list(reversed(pts)) if reverse else pts

    pts: List[Tuple[float, float]] = []
    # Left side, top toward bottom.
    left_top = y_end - r if round_top else y_end
    left_bot = y_start + r if round_bottom else y_start
    pts.append((left, left_top))
    if left_bot < left_top:
        pts.append((left, left_bot))
    # Bottom end: straight, or convex cap bulging down (left to right).
    if round_bottom:
        pts.extend(cap(y_start + r, bulge_up=False)[1:])
    else:
        pts.append((right, y_start))
    # Right side, bottom toward top.
    right_top = y_end - r if round_top else y_end
    if right_top > (y_start + r if round_bottom else y_start):
        pts.append((right, right_top))
    # Top end: straight, or convex cap bulging up, right to left.
    if round_top:
        # arch_polyline is left->right through +Y; reverse for right->left.
        top = cap(y_end - r, bulge_up=True, reverse=True)
        pts.extend(top[1:])
    else:
        pts.append((left, y_end))
    return pts


def stadium_slice_polygon(
    x_left: float,
    width: float,
    stock_length: float,
    y0: float,
    y1: float,
    n: int = 20,
) -> List[Tuple[float, float]]:
    """World-coordinate polygon for a y-slice of a stadium stick.

    The physical stick occupies y in [-r, L-r]: bottom cap centre at
    y=0 (from -r to 0), top cap centre at L-2r (from L-2r to L-r).
    """
    r = width / 2.0
    cx = x_left + r
    y_lo, y_hi = stick_y_bounds(stock_length, width)
    y0 = max(y_lo, min(y_hi, y0))
    y1 = max(y_lo, min(y_hi, y1))
    if y1 <= y0 + 1e-12:
        return []

    def half_w(y: float) -> float:
        if y < 0.0:
            d = r * r - y * y
            return math.sqrt(max(0.0, d))
        top_cy = stock_length - 2.0 * r
        if y > top_cy:
            d = r * r - (y - top_cy) ** 2
            return math.sqrt(max(0.0, d))
        return r

    def add_range(ys, a, b, steps):
        if b <= a + 1e-12:
            ys.append(a)
            return
        for i in range(steps + 1):
            ys.append(a + (b - a) * i / steps)

    ys: List[float] = []
    # Sample rounded caps densely so the ends look like semicircles,
    # not triangles, even when a piece is much longer than W.
    cap1_a, cap1_b = y_lo, min(0.0, y_hi)
    cap2_a, cap2_b = max(y_lo, stock_length - 2.0 * r), y_hi
    mid_a, mid_b = cap1_b, cap2_a

    def overlap_add(a, b, steps):
        lo, hi = max(y0, a), min(y1, b)
        if hi > lo:
            add_range(ys, lo, hi, steps)

    overlap_add(cap1_a, cap1_b, 16)
    if mid_b > mid_a:
        span = min(y1, mid_b) - max(y0, mid_a)
        overlap_add(mid_a, mid_b, max(2, int(span / 4) + 1))
    overlap_add(cap2_a, cap2_b, 16)
    ys.extend([y0, y1])
    ys = sorted(set(round(y, 8) for y in ys))
    right = [(cx + half_w(y), y) for y in ys]
    left = [(cx - half_w(y), y) for y in reversed(ys)]
    return right + left


def build_cut_plan(
    stock_length: float,
    parts: List[Part],
    width: float,
    gap: float,
    hole_radius: float,
    include_end_cut: bool = True,
    method: str = "auto",
) -> CutPlan:
    """Build a CutPlan: pack by identity, arrange, then emit cuts.

    Jig layout (unchanged): stick i has its left edge at
    x = i * (width + gap); length runs along +Y; each cut is a
    horizontal line of length (width + 2) starting 1 mm to the left
    of the stick (1 mm overcut each side).

    The physical stick occupies y in [-r, L-r]. A straight cut at
    y=0 always severs the bottom factory cap; packing capacity is
    the remaining length L-r. Pieces are placed in [0, L-r].
    """
    if stock_length <= _TOL:
        raise ValueError("Stock length must be positive")
    if width <= _TOL:
        raise ValueError("Width must be positive")
    if gap < 0:
        raise ValueError("Gap must be >= 0")
    if hole_radius < 0:
        raise ValueError("Hole radius must be >= 0")

    usable = usable_length(stock_length, width)
    if usable <= _TOL:
        raise ValueError(
            "Stock length must be greater than the end radius (width/2)"
        )

    lengths = [p.length for p in parts]
    bins, unplaced = pack_pieces(usable, lengths, method=method)

    cuts: List[Tuple[float, float, float]] = []
    holes_out: List[Tuple[float, float]] = []
    arches_out: List[Tuple[float, float, bool]] = []
    sticks: List[StickLayout] = []

    cut_length_overall = width + 2.0 * CUT_EXTRA_MARGIN
    r = width / 2.0
    y_lo, y_hi = stick_y_bounds(stock_length, width)

    for bin_index, bin_items in enumerate(bins):
        x_left = bin_index * (width + gap)
        start_x = x_left - CUT_EXTRA_MARGIN
        x_center = x_left + (width / 2.0)

        ordered, y0 = arrange_bin(bin_items, parts, usable)
        layout = StickLayout(
            index=bin_index,
            x_left=x_left,
            width=width,
            length=stock_length,
        )

        # Always cut at y=0 to sever the factory bottom cap.
        cut_ys = [0.0]

        y_cursor = y0
        if y0 > _TOL:
            # Waste at the bottom of the usable span: cut where the
            # first piece starts (separates leftover from the piece).
            cut_ys.append(y0)

        for part_index in ordered:
            part = parts[part_index]
            y_start = y_cursor
            y_end = y_cursor + part.length
            layout.placements.append(Placement(
                part_index=part_index,
                stick_index=bin_index,
                y_start=y_start,
                y_end=y_end,
                length=part.length,
                is_cut_down=part.is_cut_down,
                is_cut_up=part.is_cut_up,
                hole_centers=list(part.hole_centers),
            ))
            cut_ys.append(y_end)

            for hole_rel in part.hole_centers:
                holes_out.append((x_center, y_start + hole_rel))

            for arch in rounded_end_arches(
                x_center, y_start, y_end, width,
                part.is_cut_down, part.is_cut_up,
            ):
                arches_out.append(arch)

            y_cursor = y_end

        # Bottom factory cap is always waste; leftover in [0, L-r]
        # is additional offcut (merged when it touches y=0).
        layout.waste.append((y_lo, 0.0))
        if y0 > _TOL:
            layout.waste.append((0.0, y0))
        if y_cursor < usable - _TOL:
            layout.waste.append((y_cursor, y_hi))
        layout.waste = merge_intervals(layout.waste)

        # A convex cap's apex sits on the end Y. A straight cut there
        # would nick or flatten the tip, so the arc replaces that cut
        # when the end is interior. The mandatory y=0 cut is always
        # kept (it severs the factory bottom cap). The factory top
        # tip (y = L-r) keeps the optional end cut: it only touches
        # the existing rounded tip. No extra tip cut at L-r when
        # leftover sits at the top of the usable span.
        rounded_apex = set()
        for pl in layout.placements:
            if pl.is_cut_down:
                rounded_apex.add(round(pl.y_start, 6))
            if pl.is_cut_up:
                rounded_apex.add(round(pl.y_end, 6))

        def _keep_despite_apex(y: float) -> bool:
            if abs(y) <= _TOL:
                return True
            return abs(y - usable) <= _TOL

        seen = set()
        for y in cut_ys:
            key = round(y, 6)
            if key in seen:
                continue
            if y < -_TOL or y > usable + _TOL:
                continue
            if key in rounded_apex and not _keep_despite_apex(y):
                continue
            if (y < usable - _TOL) or include_end_cut:
                seen.add(key)
                cuts.append((start_x, float(y), cut_length_overall))

        sticks.append(layout)

    return CutPlan(
        stick_width=width,
        cuts=cuts,
        holes=holes_out,
        radius=hole_radius,
        arches=arches_out,
        stock_length=stock_length,
        usable_length=usable,
        gap=gap,
        sticks=sticks,
        unplaced=list(unplaced),
        parts=list(parts),
    )
