"""Card-based view of Custom-tab DSL: parse, assemble, and placement.

A card is one top-level ADD ... END block. Nested ADD/ROTATE stay as
text inside the parent card; cards are never nested. Commands (and
adjacent comments) that sit outside any top-level ADD are wrapped into
their own card when converting raw DSL to cards.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from engraver_ctrl.dsl_parse import (
    _fmt_coord,
    all_segments,
    parse_text,
    segments_bbox,
)


LOOSE_NAME = "loose"


@dataclass
class Card:
    name: str
    dx: float
    dy: float
    inner: str = ""


@dataclass
class ParseCardsResult:
    cards: list = field(default_factory=list)


def fmt_delta(v):
    return _fmt_coord(v)


def normalize_inner(text):
    """Canonical inner-DSL body: newlines only, no trailing newline."""
    if not text:
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def unique_name(base, existing):
    """Return base, or base_2, base_3, ... not in existing."""
    used = set(existing)
    name = base or LOOSE_NAME
    if name not in used:
        return name
    n = 2
    while f"{name}_{n}" in used:
        n += 1
    return f"{name}_{n}"


def next_piece_name(existing):
    """Next unused p1, p2, ... name."""
    used = set(existing)
    n = 1
    while f"p{n}" in used:
        n += 1
    return f"p{n}"


def duplicate_name(source, existing):
    return unique_name(source or LOOSE_NAME, existing)


def _parse_add(parts):
    if len(parts) < 3:
        return None
    try:
        dx, dy = float(parts[1]), float(parts[2])
    except ValueError:
        return None
    name = " ".join(parts[3:])
    return dx, dy, name


def _flush_loose(run, cards):
    """Wrap a contiguous run of top-level loose lines into one card."""
    # Drop leading/trailing blank lines; keep comments next to commands.
    while run and not run[0].strip():
        run.pop(0)
    while run and not run[-1].strip():
        run.pop()
    if not run:
        return
    # A run that is only comments/blanks is not a command; drop it.
    has_command = False
    for raw in run:
        s = raw.strip()
        if s and not s.startswith("#"):
            has_command = True
            break
    if not has_command:
        return
    names = [c.name for c in cards]
    name = unique_name(LOOSE_NAME, names)
    cards.append(Card(name=name, dx=0.0, dy=0.0,
                      inner=normalize_inner("\n".join(run))))


def parse_cards(text):
    """Split raw DSL into a document-ordered list of cards.

    Each top-level ADD ... END (END also closes ROTATE frames inside the
    block, same stack as the Custom parser) becomes a card. Each
    contiguous run of loose lines becomes a wrapped card named loose,
    loose_2, ... Nested ADD is kept as inner text.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    cards = []
    loose = []
    stack = []  # "ADD" or "ROTATE", only after a top-level ADD is open
    start = None
    add_dx = add_dy = 0.0
    add_name = ""

    def close_block(end_idx):
        nonlocal start, add_dx, add_dy, add_name
        inner_lines = lines[start + 1:end_idx]
        cards.append(Card(
            name=add_name,
            dx=add_dx,
            dy=add_dy,
            inner=normalize_inner("\n".join(inner_lines)),
        ))
        start = None

    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if not stack:
            if not stripped:
                if loose:
                    loose.append(raw)
                continue
            parts = stripped.split()
            cmd = parts[0]
            if cmd == "ADD":
                parsed = _parse_add(parts)
                if parsed is None:
                    loose.append(raw)
                    continue
                _flush_loose(loose, cards)
                loose = []
                add_dx, add_dy, add_name = parsed
                if not add_name:
                    add_name = next_piece_name(c.name for c in cards)
                start = i
                stack.append("ADD")
                continue
            loose.append(raw)
            continue

        # Inside a top-level ADD (stack may also hold ROTATE / nested ADD).
        # Comments/blanks stay in the inner slice but do not affect depth.
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        cmd = parts[0]
        if cmd == "ADD":
            parsed = _parse_add(parts)
            # Nested or invalid: still a stack frame only if it looks like ADD.
            # Invalid ADD tokens stay as text; do not change depth.
            if parsed is not None:
                stack.append("ADD")
        elif cmd == "ROTATE":
            # ROTATE is a stack frame only when it is a real command
            # (has an angle); otherwise it is just inner text.
            if len(parts) >= 2:
                try:
                    float(parts[1])
                    stack.append("ROTATE")
                except ValueError:
                    pass
        elif cmd == "END":
            if stack:
                stack.pop()
            if not stack:
                close_block(i)
                continue
        # inner lines are captured when the block closes (slice of lines)

    if stack and start is not None:
        close_block(len(lines))
    _flush_loose(loose, cards)
    return cards


def assemble_cards(cards):
    """Serialize cards as top-level ADD ... END blocks, document order."""
    parts = []
    for card in cards:
        name = (card.name or "").strip()
        header = f"ADD {fmt_delta(card.dx)} {fmt_delta(card.dy)}"
        if name:
            header = f"{header} {name}"
        inner = normalize_inner(card.inner)
        if inner:
            parts.append(f"{header}\n{inner}\nEND")
        else:
            parts.append(f"{header}\nEND")
    if not parts:
        return ""
    return "\n".join(parts) + "\n"


def assemble_line_ranges(cards):
    """1-based inclusive (start, end) line range of each card in assemble_cards."""
    ranges = []
    line = 1
    for card in cards:
        inner = normalize_inner(card.inner)
        inner_count = len(inner.split("\n")) if inner else 0
        # header + inner + END
        start = line
        end = line + inner_count + 1
        ranges.append((start, end))
        line = end + 1
    return ranges


def card_index_for_line(cards, line):
    """Index of the card whose assembled range contains 1-based line, or None."""
    for i, (start, end) in enumerate(assemble_line_ranges(cards)):
        if start <= line <= end:
            return i
    return None


def local_aabb(inner):
    """Axis-aligned local bbox of inner DSL: (minx, miny, maxx, maxy).

    Empty or non-geometric inner returns a zero box at the origin.
    """
    segs = all_segments(parse_text(inner or ""))
    box = segments_bbox(segs)
    if box is None:
        return (0.0, 0.0, 0.0, 0.0)
    return box


def world_envelope(cards):
    """(xmax, ymax) = max over cards of (dx + local_max_x, dy + local_max_y).

    With no cards, both are 0.
    """
    if not cards:
        return 0.0, 0.0
    xmax = None
    ymax = None
    for card in cards:
        _minx, _miny, maxx, maxy = local_aabb(card.inner)
        wx = card.dx + maxx
        wy = card.dy + maxy
        xmax = wx if xmax is None else max(xmax, wx)
        ymax = wy if ymax is None else max(ymax, wy)
    return xmax, ymax


def place_new_card(cards, inner="", use_center=None):
    """Pick (dx, dy) for a new card among (xmax, 0) and (0, ymax).

    First card is (0, 0). No extra gap. For an empty card, compare
    distance of the new origin to O(0,0). When size is known (duplicate,
    or use_center=True), compare distance of the placed bbox center.
    Ties prefer (xmax, 0).
    """
    if not cards:
        return 0.0, 0.0
    xmax, ymax = world_envelope(cards)
    cand_x = (xmax, 0.0)
    cand_y = (0.0, ymax)
    body = normalize_inner(inner)
    if use_center is None:
        use_center = bool(body)
    if not use_center:
        dx = math.hypot(*cand_x)
        dy = math.hypot(*cand_y)
        return cand_x if dx <= dy else cand_y
    minx, miny, maxx, maxy = local_aabb(body)
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0

    def dist(origin):
        ox, oy = origin
        return math.hypot(ox + cx, oy + cy)

    return cand_x if dist(cand_x) <= dist(cand_y) else cand_y


def add_card(cards, name=None, inner=""):
    """Append an empty (or given) card and return the new list + the card."""
    names = [c.name for c in cards]
    card = Card(
        name=name or next_piece_name(names),
        dx=0.0,
        dy=0.0,
        inner=normalize_inner(inner),
    )
    card.dx, card.dy = place_new_card(cards, inner=card.inner, use_center=False)
    result = list(cards) + [card]
    return result, card


def duplicate_card(cards, index):
    """Copy cards[index] with a new unique name and placement; insert after it."""
    src = cards[index]
    names = [c.name for c in cards]
    card = Card(
        name=duplicate_name(src.name, names),
        dx=0.0,
        dy=0.0,
        inner=normalize_inner(src.inner),
    )
    card.dx, card.dy = place_new_card(cards, inner=card.inner, use_center=True)
    result = list(cards)
    result.insert(index + 1, card)
    return result, card


def cards_from_raw_and_assemble(text):
    """Convenience: parse then assemble (raw → cards → raw)."""
    cards = parse_cards(text)
    return cards, assemble_cards(cards)

