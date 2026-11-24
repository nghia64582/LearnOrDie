from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from engraver_ctrl.cut_handler import pack_pieces

_TOL = 1e-9
CUT_EXTRA_MARGIN = 1.0  # mm overcut on each side of a stick


@dataclass
class Part:
    """One piece to cut from a stick.

    - length: finished piece length along the stick (mm)
    - is_cut_down: cut a 180° arch at the bottom (low-Y) end
    - is_cut_up: cut a 180° arch at the top (high-Y) end
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

    - cuts: (start_x, y, length_of_cut) horizontal G-code cuts
    - holes: (center_x, center_y)
    - arches: (center_x, center_y, is_up)
        is_up True  => lower arch, opening upward (G3)
        is_up False => upper arch, opening downward (G2)
    """
    stick_width: float
    cuts: List[Tuple[float, float, float]]
    holes: List[Tuple[float, float]]
    radius: float
    arches: List[Tuple[float, float, bool]]
    stock_length: float = 0.0
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
        s += f"Sticks: {len(self.sticks)}\n"
        s += "Cuts:\n"
        for (sx, y, length) in self.cuts:
            s += f"  StartX: {sx:.3f}, Y: {y:.3f}, Length: {length:.3f}\n"
        s += "Holes:\n"
        for (cx, cy) in self.holes:
            s += f"  CenterX: {cx:.3f}, CenterY: {cy:.3f}\n"
        s += f"Radius: {self.radius:.3f}\n"
        s += "Arches:\n"
        for (cx, cy, is_up) in self.arches:
            dir_str = "Up" if is_up else "Down"
            s += f"  CenterX: {cx:.3f}, CenterY: {cy:.3f}, Direction: {dir_str}\n"
        if self.unplaced:
            s += f"Unplaced: {self.unplaced}\n"
        return s


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
    stock_length: float,
) -> Tuple[List[int], float]:
    """Order pieces on one stick and choose where leftover waste goes.

    Simple policy (usable length = L, leftover is a single block):
    - If any piece wants a rounded top and none wants a rounded bottom,
      put waste at the bottom so the last piece ends at Y=L.
    - Otherwise put waste at the top (first piece starts at Y=0).
    - Prefer a round-bottom piece at the factory bottom when waste is
      at the top; prefer a round-top piece at the factory top when the
      used span reaches Y=L.
    A piece that wants both rounded ends only sits at both factory tips
    when it occupies the whole stick.

    Returns (ordered_indices, y_start_of_first_piece).
    """
    items = list(indices)
    if not items:
        return [], 0.0
    used = sum(float(parts[i].length) for i in items)
    leftover = max(0.0, float(stock_length) - used)
    has_down = any(parts[i].is_cut_down for i in items)
    has_up = any(parts[i].is_cut_up for i in items)
    waste_at_bottom = leftover > _TOL and has_up and not has_down
    y0 = leftover if waste_at_bottom else 0.0

    def take(pred) -> Optional[int]:
        for pos, idx in enumerate(items):
            if pred(parts[idx]):
                return items.pop(pos)
        return None

    ordered: List[int] = []
    if y0 <= _TOL:
        first = take(lambda p: p.is_cut_down and not p.is_cut_up)
        if first is None:
            first = take(lambda p: p.is_cut_down)
        if first is not None:
            ordered.append(first)

    last = None
    end_reaches_stock = abs((y0 + used) - float(stock_length)) <= _TOL
    if end_reaches_stock:
        last = take(lambda p: p.is_cut_up and not p.is_cut_down)
        if last is None:
            last = take(lambda p: p.is_cut_up)

    # Keep remaining pieces in pack order (stable, already by FFD/BFD).
    ordered.extend(items)
    if last is not None:
        ordered.append(last)
    return ordered, y0


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
    """
    if stock_length <= _TOL:
        raise ValueError("Stock length must be positive")
    if width <= _TOL:
        raise ValueError("Width must be positive")
    if gap < 0:
        raise ValueError("Gap must be >= 0")
    if hole_radius < 0:
        raise ValueError("Hole radius must be >= 0")

    lengths = [p.length for p in parts]
    bins, unplaced = pack_pieces(stock_length, lengths, method=method)

    cuts: List[Tuple[float, float, float]] = []
    holes_out: List[Tuple[float, float]] = []
    arches_out: List[Tuple[float, float, bool]] = []
    sticks: List[StickLayout] = []

    cut_length_overall = width + 2.0 * CUT_EXTRA_MARGIN

    for bin_index, bin_items in enumerate(bins):
        x_left = bin_index * (width + gap)
        start_x = x_left - CUT_EXTRA_MARGIN
        x_center = x_left + (width / 2.0)

        ordered, y0 = arrange_bin(bin_items, parts, stock_length)
        layout = StickLayout(
            index=bin_index,
            x_left=x_left,
            width=width,
            length=stock_length,
        )

        # Cuts at every piece boundary, plus y=0 / final end when requested.
        cut_ys = []
        if include_end_cut:
            cut_ys.append(0.0)

        y_cursor = y0
        if y0 > _TOL:
            # Waste at the bottom: cut where the first piece starts
            # (separates leftover from the first piece).
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

            if part.is_cut_down:
                arches_out.append((x_center, y_start + (width / 2.0), True))
            if part.is_cut_up:
                arches_out.append((x_center, y_end - (width / 2.0), False))

            y_cursor = y_end

        if y_cursor < stock_length - _TOL:
            layout.waste.append((y_cursor, stock_length))
        if y0 > _TOL:
            layout.waste.append((0.0, y0))
        layout.waste.sort()

        if include_end_cut and abs(y_cursor - stock_length) > _TOL:
            # Last piece ended before L; y=L is not already queued unless
            # some piece ended exactly at L. Keep previous behaviour: no
            # extra tip cut at L when leftover sits at the top.
            pass

        # Dedup cut Ys while preserving order.
        seen = set()
        for y in cut_ys:
            key = round(y, 6)
            if key in seen:
                continue
            if y < -_TOL or y > stock_length + _TOL:
                continue
            if (y < stock_length - _TOL) or include_end_cut:
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
        gap=gap,
        sticks=sticks,
        unplaced=list(unplaced),
        parts=list(parts),
    )
