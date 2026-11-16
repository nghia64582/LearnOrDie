"""Card-based view of Custom-tab DSL: parse, assemble, and placement.

A card is one top-level ADD ... END block. Nested ADD/ROTATE stay as
text inside the parent card; cards are never nested. Commands (and
adjacent comments) that sit outside any top-level ADD are wrapped into
their own card when converting raw DSL to cards.

Card size and border
--------------------
Each card may carry optional ``w`` / ``h`` (local size from the card
origin) and a ``border`` flag. When ``border`` is on, assemble writes
these two lines at the start of the ADD body::

    # card w=<w> h=<h> border=1
    R 0 0 <w> <h>

The comment is the round-trip marker: parse strips it and the following
``R 0 0 w h``, sets ``border=True`` and the size, and leaves the rest of
the body as ``inner`` so the rectangle is not duplicated. A trailing
``# card-border`` (or the same ``# card ... border=1`` form) on the
``R`` line is also accepted.

A bare ``R 0 0 W H`` with no marker is ordinary geometry, not a border.
That keeps existing piece outlines intact and makes unmarked raw DSL
round-trip byte-for-byte (aside from normal ADD wrapping of loose
commands).

When border is off, a ``# card w=.. h=.. border=0`` comment is emitted
only if the user has set a size that differs from the inferred bbox;
no extra ``R`` is written. On parse of unmarked cards, ``w`` / ``h``
are prefilled from the inner geometry's max extents relative to the
card origin (local ``maxx``, ``maxy``) when those can be computed.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from engraver_ctrl.dsl_parse import (
    _fmt_coord,
    all_segments,
    parse_text,
    segments_bbox,
)


LOOSE_NAME = "loose"

# Leading metadata comment written when border is on, or when w/h is a
# custom size that would otherwise be lost on a raw-DSL round-trip.
# Short form "# card-border" is also accepted (size then comes from the
# following R 0 0 w h).
_META_RE = re.compile(
    r"^#\s*card(?:-border)?"
    r"(?:\s+w\s*=\s*(\S+))?"
    r"(?:\s+h\s*=\s*(\S+))?"
    r"(?:\s+border\s*=\s*([01]))?"
    r"\s*$",
    re.IGNORECASE,
)


@dataclass
class Card:
    name: str
    dx: float
    dy: float
    inner: str = ""
    w: float | None = None
    h: float | None = None
    border: bool = False


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
    name = base or LOOSE_NAME
    used = set(existing)
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


def copy_card(card):
    """Shallow copy of a Card, including size and border."""
    return Card(
        name=card.name,
        dx=float(card.dx),
        dy=float(card.dy),
        inner=card.inner,
        w=card.w,
        h=card.h,
        border=bool(card.border),
    )


def _parse_add(parts):
    if len(parts) < 3:
        return None
    try:
        dx, dy = float(parts[1]), float(parts[2])
    except ValueError:
        return None
    name = " ".join(parts[3:])
    return dx, dy, name


def infer_size(inner):
    """(w, h) from inner geometry: max extents relative to the card origin.

    That is local (maxx, maxy) of the axis-aligned bbox, so a following
    ``R 0 0 w h`` covers first-quadrant content from the origin. Empty
    or non-geometric inner returns (None, None). A non-positive far edge
    is stored as 0 when the other edge is usable, or as unset if both
    are non-positive.
    """
    segs = all_segments(parse_text(inner or ""))
    box = segments_bbox(segs)
    if box is None:
        return None, None
    _minx, _miny, maxx, maxy = box
    w = maxx if maxx > 0 else 0.0
    h = maxy if maxy > 0 else 0.0
    if w <= 0 and h <= 0:
        return None, None
    return w, h


def apply_inferred_size(card, overwrite=False):
    """Prefill card.w / card.h from inner geometry when missing (or always)."""
    iw, ih = infer_size(card.inner)
    if overwrite or card.w is None:
        card.w = iw
    if overwrite or card.h is None:
        card.h = ih
    return card


def _size_is_custom(card):
    """True when w/h are set and do not match the inferred inner extents."""
    if card.w is None or card.h is None:
        return False
    iw, ih = infer_size(card.inner)
    if iw is None or ih is None:
        return True
    return fmt_delta(card.w) != fmt_delta(iw) or fmt_delta(card.h) != fmt_delta(ih)


def _parse_meta_comment(stripped):
    """Parse a standalone ``# card ...`` / ``# card-border`` comment.

    Returns (w, h, border) or None if the line is not a card meta comment.
    ``w`` / ``h`` may be None when the short ``# card-border`` form is used.
    """
    m = _META_RE.match(stripped)
    if not m:
        return None
    w_s, h_s, b_s = m.group(1), m.group(2), m.group(3)
    try:
        w = float(w_s) if w_s is not None else None
        h = float(h_s) if h_s is not None else None
    except ValueError:
        return None
    compact = re.sub(r"\s+", "", stripped).lower()
    short = compact == "#card-border" or compact.startswith("#card-border")
    if b_s is not None:
        border = b_s == "1"
    else:
        border = bool(short)
    return w, h, border


def _parse_r_origin(stripped):
    """If ``R 0 0 W H`` (optional trailing comment), return (W, H, comment)."""
    if "#" in stripped:
        code, comment = stripped.split("#", 1)
        comment = comment.strip()
    else:
        code, comment = stripped, ""
    parts = code.split()
    if len(parts) != 5 or parts[0] != "R":
        return None
    try:
        x, y, w, h = (float(parts[1]), float(parts[2]),
                      float(parts[3]), float(parts[4]))
    except ValueError:
        return None
    if abs(x) > 1e-9 or abs(y) > 1e-9:
        return None
    return w, h, comment


def extract_card_meta(inner):
    """Split a raw ADD body into (inner, w, h, border).

    See the module docstring for the marker convention. Unmarked bodies
    keep every line (including a leading ``R 0 0 W H``) and get w/h
    inferred from geometry when possible.
    """
    raw = normalize_inner(inner)
    if not raw:
        return "", None, None, False

    lines = raw.split("\n")
    found_meta = False
    meta_idx = None
    r_idx = None
    w = h = None
    border = False

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        parsed = _parse_meta_comment(s)
        if parsed is not None:
            found_meta = True
            meta_idx = i
            w, h, border = parsed
            i += 1
            break
        if s.startswith("#"):
            i += 1
            continue
        break

    if not found_meta:
        for j, line in enumerate(lines):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parsed_r = _parse_r_origin(s)
            if parsed_r is not None:
                rw, rh, comment = parsed_r
                if comment:
                    parsed_c = _parse_meta_comment("# " + comment)
                    if parsed_c is not None and parsed_c[2]:
                        found_meta = True
                        border = True
                        w = parsed_c[0] if parsed_c[0] is not None else rw
                        h = parsed_c[1] if parsed_c[1] is not None else rh
                        r_idx = j
            break

    if found_meta and border and r_idx is None:
        for j in range(len(lines)):
            if j == meta_idx:
                continue
            s = lines[j].strip()
            if not s or s.startswith("#"):
                continue
            parsed_r = _parse_r_origin(s)
            if parsed_r is not None:
                rw, rh, _comment = parsed_r
                w, h = rw, rh
                r_idx = j
            break

    if found_meta:
        drop = set()
        if meta_idx is not None:
            drop.add(meta_idx)
        if border and r_idx is not None:
            drop.add(r_idx)
        raw = normalize_inner("\n".join(
            ln for k, ln in enumerate(lines) if k not in drop
        ))

    if w is None or h is None:
        iw, ih = infer_size(raw)
        if w is None:
            w = iw
        if h is None:
            h = ih

    return raw, w, h, bool(border) if found_meta else False


def card_prefix_lines(card):
    """Metadata comment and/or border R lines to write before card.inner."""
    lines = []
    emit_meta = bool(card.border) or _size_is_custom(card)
    w = 0.0 if card.w is None else card.w
    h = 0.0 if card.h is None else card.h
    if emit_meta:
        flag = 1 if card.border else 0
        lines.append(f"# card w={fmt_delta(w)} h={fmt_delta(h)} border={flag}")
    if card.border:
        lines.append(f"R 0 0 {fmt_delta(w)} {fmt_delta(h)}")
    return lines


def card_body_text(card):
    """Full text inside ADD ... END, including border prefix when present."""
    chunks = list(card_prefix_lines(card))
    inner = normalize_inner(card.inner)
    if inner:
        chunks.append(inner)
    return "\n".join(chunks)


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
    inner, w, h, border = extract_card_meta(normalize_inner("\n".join(run)))
    cards.append(Card(name=name, dx=0.0, dy=0.0, inner=inner,
                      w=w, h=h, border=border))


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
        inner, w, h, border = extract_card_meta(
            normalize_inner("\n".join(inner_lines))
        )
        cards.append(Card(
            name=add_name,
            dx=add_dx,
            dy=add_dy,
            inner=inner,
            w=w,
            h=h,
            border=border,
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
        body = card_body_text(card)
        if body:
            parts.append(f"{header}\n{body}\nEND")
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
        body = card_body_text(card)
        inner_count = len(body.split("\n")) if body else 0
        # header + body + END
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


def card_far_extents(card):
    """Local (maxx, maxy) used for placement: inner bbox unioned with w/h."""
    _minx, _miny, maxx, maxy = local_aabb(card.inner)
    if card.w is not None:
        maxx = max(maxx, float(card.w))
    if card.h is not None:
        maxy = max(maxy, float(card.h))
    return maxx, maxy


def world_envelope(cards):
    """(xmax, ymax) = max over cards of (dx + local_max_x, dy + local_max_y).

    With no cards, both are 0. Uses w/h when set, otherwise inner bbox.
    """
    if not cards:
        return 0.0, 0.0
    xmax = None
    ymax = None
    for card in cards:
        maxx, maxy = card_far_extents(card)
        wx = card.dx + maxx
        wy = card.dy + maxy
        xmax = wx if xmax is None else max(xmax, wx)
        ymax = wy if ymax is None else max(ymax, wy)
    return xmax, ymax


def place_new_card(cards, inner="", use_center=None, w=None, h=None, card=None):
    """Pick (dx, dy) for a new card among (xmax, 0) and (0, ymax).

    First card is (0, 0). No extra gap. For an empty card, compare
    distance of the new origin to O(0,0). When size is known (duplicate,
    use_center=True, or w/h set), compare distance of the placed bbox
    center. Ties prefer (xmax, 0). Existing cards contribute their w/h
    to the envelope when those are set.
    """
    if card is not None:
        inner = card.inner
        if w is None:
            w = card.w
        if h is None:
            h = card.h
    if not cards:
        return 0.0, 0.0
    xmax, ymax = world_envelope(cards)
    cand_x = (xmax, 0.0)
    cand_y = (0.0, ymax)
    body = normalize_inner(inner)
    has_size = (w is not None and h is not None) or bool(body)
    if use_center is None:
        use_center = has_size
    if not use_center:
        dx = math.hypot(*cand_x)
        dy = math.hypot(*cand_y)
        return cand_x if dx <= dy else cand_y
    minx, miny, maxx, maxy = local_aabb(body)
    if w is not None:
        maxx = max(maxx, float(w))
        minx = min(minx, 0.0)
    if h is not None:
        maxy = max(maxy, float(h))
        miny = min(miny, 0.0)
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
    apply_inferred_size(card)
    card.dx, card.dy = place_new_card(cards, card=card, use_center=False)
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
        w=src.w,
        h=src.h,
        border=bool(src.border),
    )
    card.dx, card.dy = place_new_card(cards, card=card, use_center=True)
    result = list(cards)
    result.insert(index + 1, card)
    return result, card


def cards_from_raw_and_assemble(text):
    """Convenience: parse then assemble (raw → cards → raw)."""
    cards = parse_cards(text)
    return cards, assemble_cards(cards)
