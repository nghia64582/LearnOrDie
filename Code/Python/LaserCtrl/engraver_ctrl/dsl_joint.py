"""Auto-joint marks (J) and expansion to JM/JF.

J is a preview-only marker, never cut geometry. Apply joints rewrites the
DSL: comment each J, insert matching JM/JF, and on a male R replace the
shared outline edge so the comb is not double-cut.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

# Sheet thickness (mm). Adjustable later; used to validate the mark short side.
THICKNESS = 3.0
# Default tooth length (mm). first_d is chosen so the tooth/gap pattern
# (same length teeth and gaps, as in JM/JF) is centred on the joint.
DEFAULT_TEETH_LENGTH = 10.0
THICKNESS_TOL = 0.05
EDGE_TOL = 0.05
LENGTH_TOL = 0.05

PAIR_COLORS = (
    "#0f766e", "#b45309", "#7c3aed", "#be185d",
    "#1d4ed8", "#15803d", "#c2410c", "#a16207",
)


@dataclass
class JointMark:
    line: int              # 1-based
    x: float
    y: float
    w: float
    h: float
    name: str
    role: str | None       # "M", "F", or None
    add_line: int | None   # 1-based innermost ADD, or None if stray
    add_dx: float          # cumulative ADD translation (ROTATE ignored)
    add_dy: float
    in_rotate: bool
    raw: str
    indent: str = ""


@dataclass
class Outline:
    line: int              # 1-based
    cmd: str
    nums: list
    add_line: int
    raw: str
    indent: str = ""


@dataclass
class JointWarning:
    level: str             # "error" or "warning"
    message: str
    line: int | None = None


@dataclass
class ApplyResult:
    text: str
    warnings: list = field(default_factory=list)
    applied: int = 0
    skipped: int = 0


def fmt_num(v):
    r = round(float(v), 2)
    if abs(r) < 1e-12:
        r = 0.0
    if float(r).is_integer():
        return str(int(r))
    return f"{r:.2f}".rstrip("0").rstrip(".")


def comment_line(raw):
    indent = raw[:len(raw) - len(raw.lstrip())] if raw.strip() else ""
    body = raw.strip()
    if not body or body.startswith("#"):
        return raw
    return f"{indent}# {body}"


def tooth_spans(length, teeth, first_d):
    """(start, end) intervals of teeth / JF holes along the joint line."""
    spans = []
    t = float(first_d)
    teeth = float(teeth)
    length = float(length)
    while t + teeth <= length + 1e-9:
        spans.append((t, t + teeth))
        t += 2 * teeth
    return spans


def choose_teeth(length, teeth_length=DEFAULT_TEETH_LENGTH):
    """Return (teeth_length, first_d) centred on the joint line.

    Uses the existing JM/JF convention: teeth of equal length, gaps of the
    same length, a leftover last tooth is not emitted (so first_d is set
    so the used span (2n-1)*teeth sits in the middle).
    """
    length = float(length)
    teeth = float(teeth_length)
    if length <= 0:
        return None
    if teeth > length + 1e-9:
        return (length, 0.0)
    n = max(1, int((length / teeth + 1) // 2))
    while n > 1 and (2 * n - 1) * teeth > length + 1e-9:
        n -= 1
    used = (2 * n - 1) * teeth
    first_d = max(0.0, (length - used) / 2)
    return (teeth, first_d)


def mark_axes(mark):
    """Return (along_x, length, thick, x, y) for a J / R-like strip."""
    along_x = mark.w >= mark.h
    length = mark.w if along_x else mark.h
    thick = mark.h if along_x else mark.w
    return along_x, length, thick, mark.x, mark.y


def world_mark_corners(mark):
    """World-space corners of the mark rectangle (ADD translation only)."""
    x0, y0 = mark.x + mark.add_dx, mark.y + mark.add_dy
    x1, y1 = x0 + mark.w, y0 + mark.h
    return (x0, y0), (x1, y0), (x1, y1), (x0, y1)


def world_mark_center(mark):
    return (mark.x + mark.w / 2 + mark.add_dx,
            mark.y + mark.h / 2 + mark.add_dy)


def pair_color(name, index=None):
    if index is None:
        index = sum(ord(c) for c in name)
    return PAIR_COLORS[index % len(PAIR_COLORS)]


def parse_j_tokens(parts):
    """Parse `J x y w h NAME [M|F]`. Returns dict or None."""
    if len(parts) < 6:
        return None
    try:
        x, y, w, h = map(float, parts[1:5])
    except ValueError:
        return None
    if w <= 0 or h <= 0:
        return None
    name = parts[5]
    role = None
    if len(parts) >= 7:
        token = parts[6].upper()
        if token in ("M", "F"):
            role = token
        else:
            return None
    if len(parts) > 7:
        return None
    return {"x": x, "y": y, "w": w, "h": h, "name": name, "role": role}


def parse_joint_file(text):
    """Scan DSL for J marks and closed outlines (R/RC/P) per ADD.

    ROTATE is recorded on the stack so a J inside it can be flagged; mark
    world positions only apply ADD translation (no rotation), as required.
    """
    marks = []
    outlines = []
    warnings = []
    add_stack = []  # (dx, dy, line or None, is_rotate)
    lines = text.splitlines()
    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        cmd = parts[0]
        indent = raw[:len(raw) - len(raw.lstrip())]
        if cmd == "ADD":
            if len(parts) < 3:
                continue
            try:
                dx, dy = float(parts[1]), float(parts[2])
            except ValueError:
                continue
            add_stack.append((dx, dy, lineno, False))
            continue
        if cmd == "ROTATE":
            add_stack.append((0.0, 0.0, None, True))
            continue
        if cmd == "END":
            if add_stack:
                add_stack.pop()
            continue
        in_rotate = any(e[3] for e in add_stack)
        add_entries = [e for e in add_stack if e[2] is not None]
        add_line = add_entries[-1][2] if add_entries else None
        add_dx = sum(e[0] for e in add_stack)
        add_dy = sum(e[1] for e in add_stack)
        if cmd == "J":
            parsed = parse_j_tokens(parts)
            if parsed is None:
                warnings.append(JointWarning(
                    "warning", f"Ignored malformed J on line {lineno}", lineno))
                continue
            if add_line is None:
                warnings.append(JointWarning(
                    "warning",
                    f"J '{parsed['name']}' on line {lineno} is outside any ADD "
                    "and will be skipped",
                    lineno,
                ))
            if in_rotate:
                warnings.append(JointWarning(
                    "warning",
                    f"J '{parsed['name']}' on line {lineno} is inside a ROTATE "
                    "block (not supported yet) and will be skipped",
                    lineno,
                ))
            marks.append(JointMark(
                line=lineno, add_line=add_line, add_dx=add_dx, add_dy=add_dy,
                in_rotate=in_rotate, raw=raw, indent=indent, **parsed,
            ))
            continue
        if cmd in ("R", "RC", "P") and add_line is not None and not in_rotate:
            try:
                nums = list(map(float, parts[1:]))
            except ValueError:
                continue
            if cmd in ("R", "RC") and len(nums) != 4:
                continue
            if cmd == "P" and (len(nums) < 4 or len(nums) % 2):
                continue
            outlines.append(Outline(
                line=lineno, cmd=cmd, nums=nums, add_line=add_line,
                raw=raw, indent=indent,
            ))
    return marks, outlines, warnings


def _outline_segments(outline):
    nums = outline.nums
    if outline.cmd == "R":
        x, y, w, h = nums
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    elif outline.cmd == "RC":
        cx, cy, w, h = nums
        x, y = cx - w / 2, cy - h / 2
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    elif outline.cmd == "P":
        pts = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    else:
        return []
    n = len(pts)
    return [(pts[i], pts[(i + 1) % n]) for i in range(n)]


def _point_to_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 < 1e-18:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5, 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5, t


def _segment_on_segment(p1, p2, e1, e2, tol=EDGE_TOL):
    d1, t1 = _point_to_segment(p1[0], p1[1], e1[0], e1[1], e2[0], e2[1])
    d2, t2 = _point_to_segment(p2[0], p2[1], e1[0], e1[1], e2[0], e2[1])
    return d1 <= tol and d2 <= tol and max(t1, t2) - min(t1, t2) > 1e-9


def mark_long_sides(mark):
    along_x, _length, _thick, x, y = mark_axes(mark)
    if along_x:
        a = (x, y), (x + mark.w, y)
        b = (x, y + mark.h), (x + mark.w, y + mark.h)
    else:
        a = (x, y), (x, y + mark.h)
        b = (x + mark.w, y), (x + mark.w, y + mark.h)
    return a, b


def classify_mark(mark, outlines, tol=EDGE_TOL):
    """'edge' if a long side lies on a same-ADD outline edge, else 'interior'.

    Returns (kind, outline_or_None, outer_side).
    outer_side is 0 if the v=0 long side is on the boundary, 1 if v=thick,
    or None if interior / unknown.
    """
    if mark.add_line is None:
        return "unknown", None, None
    sides = mark_long_sides(mark)
    candidates = [o for o in outlines if o.add_line == mark.add_line]
    hits = []
    for side_idx, side in enumerate(sides):
        for outline in candidates:
            for edge in _outline_segments(outline):
                if _segment_on_segment(side[0], side[1], edge[0], edge[1], tol):
                    hits.append((side_idx, outline, edge))
                    break
    if not hits:
        return "interior", None, None
    # Prefer a hit on a unique side. If both long sides somehow hit, first one.
    side_idx, outline, _edge = hits[0]
    return "edge", outline, side_idx


def group_marks(marks):
    groups = defaultdict(list)
    for m in marks:
        groups[m.name].append(m)
    return groups


def collect_preview_warnings(marks, outlines, warnings=None, thickness=THICKNESS):
    """Warnings for unpaired / >2 / rotate / thickness, plus role errors."""
    out = list(warnings or [])
    groups = group_marks(marks)
    for name, items in groups.items():
        active = [m for m in items if not m.in_rotate and m.add_line is not None]
        skipped_rot = [m for m in items if m.in_rotate]
        # rotate warnings already added at parse; still note pairing impact
        if len(items) == 1 and not skipped_rot:
            m = items[0]
            if m.add_line is not None:
                out.append(JointWarning(
                    "warning",
                    f"Joint '{name}' has only one mark (line {m.line}); "
                    "needs a matching J with the same name",
                    m.line,
                ))
        if len(items) > 2:
            lines = ", ".join(str(m.line) for m in items)
            out.append(JointWarning(
                "warning",
                f"Joint '{name}' has {len(items)} marks (lines {lines}); "
                "exactly two are required, this pair will not be applied",
                items[0].line,
            ))
        if len(active) == 2:
            for m in active:
                _along, _length, thick, _x, _y = mark_axes(m)
                if abs(thick - thickness) > THICKNESS_TOL:
                    out.append(JointWarning(
                        "warning",
                        f"J '{name}' on line {m.line} short side is "
                        f"{fmt_num(thick)} mm, expected sheet thickness "
                        f"{fmt_num(thickness)} mm",
                        m.line,
                    ))
            kinds = [classify_mark(m, outlines)[0] for m in active]
            if kinds[0] == "interior" and kinds[1] == "interior":
                out.append(JointWarning(
                    "error",
                    f"Joint '{name}' has both marks in the interior of their "
                    f"pieces (lines {active[0].line} and {active[1].line}); "
                    "one mark must be on an edge (male tenon)",
                    active[0].line,
                ))
    return out


def _roles_for_pair(m1, m2, outlines):
    """Return (role1, role2) as 'M'/'F', or (None, None) with a reason."""
    k1, _o1, _s1 = classify_mark(m1, outlines)
    k2, _o2, _s2 = classify_mark(m2, outlines)
    if k1 == "interior" and k2 == "interior":
        return None, None, (
            f"Joint '{m1.name}' has both marks in the interior "
            f"(lines {m1.line} and {m2.line})"
        )
    # Overrides: if one or both specify M/F, use them when consistent.
    r1, r2 = m1.role, m2.role
    if r1 and r2:
        if r1 == r2:
            return None, None, (
                f"Joint '{m1.name}' has conflicting roles "
                f"(both {r1} on lines {m1.line} and {m2.line})"
            )
        return r1, r2, None
    if r1 and not r2:
        return r1, ("F" if r1 == "M" else "M"), None
    if r2 and not r1:
        return ("F" if r2 == "M" else "M"), r2, None
    # Automatic: edge+interior -> edge JM, interior JF.
    if k1 == "edge" and k2 == "interior":
        return "M", "F", None
    if k1 == "interior" and k2 == "edge":
        return "F", "M", None
    # Both edge (or unknown treated like edge default): first JM, second JF.
    return "M", "F", None


def _jf_params(mark, teeth, first_d):
    """Centerline-mapped JF command (local coords)."""
    along_x, length, thick, x, y = mark_axes(mark)
    if along_x:
        cx, cy, w, h = x, y + thick / 2, length, thick
    else:
        cx, cy, w, h = x + thick / 2, y, thick, length
    return (
        f"JF {fmt_num(cx)} {fmt_num(cy)} {fmt_num(w)} {fmt_num(h)} "
        f"{fmt_num(teeth)} {fmt_num(first_d)}"
    )


def _jm_params(mark, teeth, first_d, outlines):
    """JM command: teeth reach the original piece edge; spine is inward.

    `in` = teeth toward v=0 (the strip origin). `out` = teeth toward v=thick.
    If the free edge is the v=0 long side, use `in` so the tooth tips sit on
    that edge and the shoulders sit at v=thick (one thickness inward).
    """
    _kind, _outline, outer = classify_mark(mark, outlines)
    # outer 0: free edge is v=0 -> in.  outer 1: free edge is v=thick -> out.
    # Unknown / interior (forced M): default in (teeth toward v=0).
    direction = "out" if outer == 1 else "in"
    along_x, length, thick, x, y = mark_axes(mark)
    if along_x:
        w, h = length, thick
    else:
        w, h = thick, length
    return (
        f"JM {fmt_num(x)} {fmt_num(y)} {fmt_num(w)} {fmt_num(h)} "
        f"{fmt_num(teeth)} {fmt_num(first_d)} {direction}"
    ), direction


def _replace_r_edges(outline, mark, outlines):
    """Replace a male R: keep non-joint edges, drop the outer joint span.

    Adjacent sides that used to meet the original edge are shortened so they
    meet the comb spine (one thickness inward). Stubs of a partial-edge mark
    stay on the original edge and are connected to the spine at the mark
    ends. Returns None if the outline is not an R we can split.
    """
    if outline is None or outline.cmd != "R":
        return None
    kind, hit, outer = classify_mark(mark, [outline] if outline else outlines)
    if kind != "edge" or hit is None or outer is None:
        return None
    x, y, w, h = outline.nums
    edges = [
        ((x, y), (x + w, y)),
        ((x + w, y), (x + w, y + h)),
        ((x + w, y + h), (x, y + h)),
        ((x, y + h), (x, y)),
    ]
    long_sides = mark_long_sides(mark)
    op0, op1 = long_sides[outer]
    sp0, sp1 = long_sides[1 - outer]

    def _key(pt):
        return (round(pt[0], 4), round(pt[1], 4))

    def _near(p, q, tol=EDGE_TOL):
        return abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol

    def _map_corner(pt):
        # Move a vertex that sat on the free edge to the matching spine
        # corner, so side edges start at thickness inward, not at y=0 / etc.
        if _near(pt, op0):
            return sp0
        if _near(pt, op1):
            return sp1
        return pt

    def _emit(a, b, dest):
        if _key(a) != _key(b):
            dest.append(
                f"L {fmt_num(a[0])} {fmt_num(a[1])} {fmt_num(b[0])} {fmt_num(b[1])}"
            )

    lines = []
    for a, b in edges:
        if _segment_on_segment(op0, op1, a, b):
            ax, ay = a
            dx, dy = b[0] - ax, b[1] - ay
            length2 = dx * dx + dy * dy or 1.0
            t0 = ((op0[0] - ax) * dx + (op0[1] - ay) * dy) / length2
            t1 = ((op1[0] - ax) * dx + (op1[1] - ay) * dy) / length2
            start_outer, start_spine = op0, sp0
            end_outer, end_spine = op1, sp1
            if t1 < t0:
                t0, t1 = t1, t0
                start_outer, start_spine = op1, sp1
                end_outer, end_spine = op0, sp0
            t0c = max(0.0, min(1.0, t0))
            t1c = max(0.0, min(1.0, t1))
            if t0c > 1e-9:
                _emit(a, start_outer, lines)
                _emit(start_outer, start_spine, lines)
            if t1c < 1 - 1e-9:
                _emit(end_spine, end_outer, lines)
                _emit(end_outer, b, lines)
        else:
            _emit(_map_corner(a), _map_corner(b), lines)
    return lines


def apply_joints(text, thickness=THICKNESS, teeth_length=DEFAULT_TEETH_LENGTH):
    """Expand J marks into JM/JF. Comments original J (and replaced R) lines."""
    marks, outlines, warnings = parse_joint_file(text)
    warnings = collect_preview_warnings(marks, outlines, warnings, thickness)
    lines = text.splitlines()
    # Keep a trailing newline if the original had one (splitlines drops it).
    had_trailing = text.endswith("\n")
    replacements = {}  # 0-based -> list[str]
    applied = 0
    skipped = 0
    groups = group_marks(marks)

    for name, items in groups.items():
        usable = [m for m in items if not m.in_rotate and m.add_line is not None]
        if len(items) > 2 or len(usable) != 2:
            # warnings already recorded
            skipped += 1
            continue
        m1, m2 = usable[0], usable[1]
        a1, len1, th1, _, _ = mark_axes(m1)
        a2, len2, th2, _, _ = mark_axes(m2)
        if abs(len1 - len2) > LENGTH_TOL:
            warnings.append(JointWarning(
                "error",
                f"Joint '{name}' region lengths differ "
                f"({fmt_num(len1)} vs {fmt_num(len2)} mm) on lines "
                f"{m1.line} and {m2.line}; not applied",
                m1.line,
            ))
            skipped += 1
            continue
        if abs(th1 - th2) > THICKNESS_TOL:
            warnings.append(JointWarning(
                "error",
                f"Joint '{name}' thicknesses differ "
                f"({fmt_num(th1)} vs {fmt_num(th2)} mm) on lines "
                f"{m1.line} and {m2.line}; not applied",
                m1.line,
            ))
            skipped += 1
            continue
        roles = _roles_for_pair(m1, m2, outlines)
        r1, r2, err = roles
        if err:
            if not any(err in (w.message or "") or err in w.message.replace("; not applied", "")
                       for w in warnings):
                warnings.append(JointWarning("error", err + "; not applied", m1.line))
            skipped += 1
            continue
        chosen = choose_teeth(min(len1, len2), teeth_length)
        if not chosen:
            warnings.append(JointWarning(
                "error", f"Joint '{name}' has non-positive length; not applied",
                m1.line,
            ))
            skipped += 1
            continue
        teeth, first_d = chosen
        plan = []
        for mark, role in ((m1, r1), (m2, r2)):
            if role == "F":
                cmd = _jf_params(mark, teeth, first_d)
                plan.append((mark, role, cmd, None, None))
            else:
                cmd, _direction = _jm_params(mark, teeth, first_d, outlines)
                kind, outline, _outer = classify_mark(mark, outlines)
                edge_lines = None
                if kind == "edge" and outline is not None and outline.cmd == "R":
                    edge_lines = _replace_r_edges(outline, mark, outlines)
                elif kind == "edge" and outline is not None:
                    warnings.append(JointWarning(
                        "warning",
                        f"Joint '{name}' male outline on line {outline.line} "
                        f"is {outline.cmd}, not R; the edge was not replaced "
                        "(possible double cut)",
                        outline.line,
                    ))
                elif kind != "edge":
                    warnings.append(JointWarning(
                        "warning",
                        f"Joint '{name}' male mark on line {mark.line} has no "
                        "R edge to replace (possible double cut)",
                        mark.line,
                    ))
                plan.append((mark, role, cmd, outline, edge_lines))
        for mark, role, cmd, outline, edge_lines in plan:
            j_idx = mark.line - 1
            replacements[j_idx] = [
                comment_line(mark.raw),
                f"{mark.indent}{cmd}",
            ]
            if role == "M" and edge_lines is not None and outline is not None:
                o_idx = outline.line - 1
                indent = outline.indent
                replacements[o_idx] = (
                    [comment_line(outline.raw)]
                    + [f"{indent}{ln}" for ln in edge_lines]
                )
        applied += 1

    if not replacements:
        return ApplyResult(text=text, warnings=warnings,
                           applied=applied, skipped=skipped)
    new_lines = []
    for i, line in enumerate(lines):
        if i in replacements:
            new_lines.extend(replacements[i])
        else:
            new_lines.append(line)
    new_text = "\n".join(new_lines)
    if had_trailing:
        new_text += "\n"
    return ApplyResult(text=new_text, warnings=warnings,
                       applied=applied, skipped=skipped)


def next_joint_name(marks):
    """Reuse a currently unpaired name, else A, B, ... Z, A2, ..."""
    groups = group_marks(marks)
    unpaired = [name for name, items in groups.items()
                if len([m for m in items if not m.in_rotate]) == 1]
    if unpaired:
        # Prefer the most recently written unpaired name (highest line).
        unpaired.sort(key=lambda n: max(m.line for m in groups[n]), reverse=True)
        return unpaired[0]
    n = 0
    while True:
        name = chr(ord("A") + (n % 26)) + ("" if n < 26 else str(n // 26 + 1))
        if name not in groups:
            return name
        n += 1


def insert_j_line(text, add_line, x, y, w, h, name, role=None):
    """Insert `J x y w h NAME [M|F]` just before the END that closes add_line."""
    lines = text.splitlines()
    had_trailing = text.endswith("\n")
    depth = 0
    start_depth = None
    end_idx = None
    indent = ""
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cmd = stripped.split()[0]
        if cmd == "ADD":
            if start_depth is None and (i + 1) == add_line:
                start_depth = depth
                indent = raw[:len(raw) - len(raw.lstrip())]
            depth += 1
        elif cmd == "ROTATE":
            depth += 1
        elif cmd == "END":
            depth -= 1
            if start_depth is not None and depth == start_depth:
                end_idx = i
                break
    if end_idx is None:
        return text
    role_tok = f" {role}" if role in ("M", "F") else ""
    # One indent step deeper than the ADD line, if any.
    j_indent = indent + "    " if indent else "    "
    # If existing body lines have an indent, prefer that.
    for j in range(add_line, end_idx):
        s = lines[j]
        if s.strip() and not s.strip().startswith("#"):
            j_indent = s[:len(s) - len(s.lstrip())]
            break
    new_line = (
        f"{j_indent}J {fmt_num(x)} {fmt_num(y)} {fmt_num(w)} {fmt_num(h)} "
        f"{name}{role_tok}"
    )
    lines.insert(end_idx, new_line)
    new_text = "\n".join(lines)
    if had_trailing or text.endswith("\n"):
        new_text += "\n"
    return new_text


def add_local_coords(mark_world_rect, add_dx, add_dy):
    """Convert a world-axis-aligned rect to local ADD coords (no rotation)."""
    x0, y0, x1, y1 = mark_world_rect
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return (x0 - add_dx, y0 - add_dy, x1 - x0, y1 - y0)
