"""Headless DSL parser matching tab_designer geometry and ADD/ROTATE stack.

Used to compute block bounding boxes and segment sets without Tk.
"""

import math
from dataclasses import dataclass, field

SHAPE_CMDS = {"C", "R", "RC", "LH", "LV", "L", "A", "P", "M", "JF", "JM"}


def apply_transform(segments, dx, dy, angle_deg):
    """Clockwise rotation about the origin, then translate by (dx, dy).

    Equivalent to: translate by ADD first, then rotate about the ADD
    point, because rotate-about-(dx,dy) after translate = rotate local
    about (0,0) then add (dx, dy).
    """
    if angle_deg == 0 and dx == 0 and dy == 0:
        return list(segments)
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    result = []
    for x1, y1, x2, y2 in segments:
        nx1 = x1 * cos_t + y1 * sin_t + dx
        ny1 = -x1 * sin_t + y1 * cos_t + dy
        nx2 = x2 * cos_t + y2 * sin_t + dx
        ny2 = -x2 * sin_t + y2 * cos_t + dy
        result.append((nx1, ny1, nx2, ny2))
    return result


def _arc_segments(cx, cy, r, s_alpha, e_alpha):
    span = e_alpha - s_alpha
    if abs(span) < 1e-9:
        return []
    circumference = 2 * math.pi * r
    arc_length = abs(span) / 360 * circumference
    segment_count = max(2, round(abs(span) / 360 * 60))
    points = []
    for i in range(segment_count + 1):
        pos = i / segment_count * arc_length
        bearing = s_alpha + (pos / arc_length) * span if arc_length else s_alpha
        math_angle = math.radians(90 - bearing)
        points.append((cx + r * math.cos(math_angle),
                       cy + r * math.sin(math_angle)))
    segs = []
    for i in range(len(points) - 1):
        p1, p2 = points[i], points[i + 1]
        segs.append((p1[0], p1[1], p2[0], p2[1]))
    return segs


def _joint_segments(cmd, nums):
    if cmd == "JF" and len(nums) != 6:
        return []
    if cmd == "JM" and len(nums) != 7:
        return []
    x, y, w, h, teeth, first_d = nums[:6]
    if w <= 0 or h <= 0 or teeth <= 0 or first_d < 0:
        return []
    along_x = w >= h
    length = w if along_x else h
    thick = h if along_x else w
    teeth_pos = []
    t = first_d
    while t + teeth <= length + 1e-9:
        teeth_pos.append((t, t + teeth))
        t += 2 * teeth

    def pt(u, v):
        return (x + u, y + v) if along_x else (x + v, y + u)

    segments = []
    if cmd == "JF":
        for a, b in teeth_pos:
            hv = thick / 2
            corners = [pt(a, -hv), pt(b, -hv), pt(b, hv), pt(a, hv)]
            for i in range(4):
                p1, p2 = corners[i], corners[(i + 1) % 4]
                segments.append((p1[0], p1[1], p2[0], p2[1]))
        return segments

    base, top = (0.0, thick) if nums[6] > 0 else (thick, 0.0)
    points = [(0.0, base)]
    for a, b in teeth_pos:
        if a > points[-1][0] + 1e-9:
            points.append((a, base))
        points.append((a, top))
        points.append((b, top))
        points.append((b, base))
    if length > points[-1][0] + 1e-9:
        points.append((length, base))
    xy = [pt(u, v) for u, v in points]
    for i in range(len(xy) - 1):
        p1, p2 = xy[i], xy[i + 1]
        if p1 != p2:
            segments.append((p1[0], p1[1], p2[0], p2[1]))
    return segments


def shape_to_segments(cmd, nums):
    segments = []
    if cmd == "L":
        x1, y1, x2, y2 = nums
        segments.append((x1, y1, x2, y2))
    elif cmd == "LH":
        x, y, length = nums
        segments.append((x, y, x + length, y))
    elif cmd == "LV":
        x, y, length = nums
        segments.append((x, y, x, y + length))
    elif cmd == "R":
        x, y, w, h = nums
        segments.extend([
            (x, y, x + w, y), (x + w, y, x + w, y + h),
            (x + w, y + h, x, y + h), (x, y + h, x, y),
        ])
    elif cmd == "RC":
        cx, cy, w, h = nums
        x, y = cx - w / 2, cy - h / 2
        segments.extend([
            (x, y, x + w, y), (x + w, y, x + w, y + h),
            (x + w, y + h, x, y + h), (x, y + h, x, y),
        ])
    elif cmd == "C":
        cx, cy, r = nums
        segments.extend(_arc_segments(cx, cy, r, 0, 360))
    elif cmd == "A":
        cx, cy, r, s_alpha, e_alpha = nums
        segments.extend(_arc_segments(cx, cy, r, s_alpha, e_alpha))
    elif cmd == "P":
        points = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
        n = len(points)
        for i in range(n):
            p1, p2 = points[i], points[(i + 1) % n]
            segments.append((p1[0], p1[1], p2[0], p2[1]))
    elif cmd == "M":
        points = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i + 1]
            segments.append((p1[0], p1[1], p2[0], p2[1]))
    elif cmd in ("JF", "JM"):
        segments.extend(_joint_segments(cmd, nums))
    return segments


def parse_text(text):
    """Parse DSL into transformed world-coordinate segments.

    Returns dict with shapes: list of (cmd, segments), add_labels: list
    of (x, y, label). Invalid lines are skipped (same as tab_designer).
    """
    shapes = []
    add_labels = []
    delta_stack = []
    next_is_priority = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        cmd = parts[0]
        if cmd == "FIRST":
            next_is_priority = True
            continue
        if cmd == "ADD":
            if len(parts) < 3:
                continue
            try:
                dx, dy = float(parts[1]), float(parts[2])
            except ValueError:
                continue
            label = " ".join(parts[3:])
            delta_stack.append((dx, dy, 0.0, label))
            add_labels.append((
                sum(d[0] for d in delta_stack),
                sum(d[1] for d in delta_stack),
                label,
            ))
            continue
        if cmd == "ROTATE":
            if len(parts) < 2:
                continue
            try:
                angle = float(parts[1])
            except ValueError:
                continue
            delta_stack.append((0.0, 0.0, angle, None))
            continue
        if cmd == "END":
            if delta_stack:
                delta_stack.pop()
            continue
        if cmd not in SHAPE_CMDS:
            continue
        num_parts = parts[1:]
        jm_dir = None
        if cmd == "JM":
            if len(num_parts) != 7:
                continue
            jm_dir = {"out": 1.0, "+": 1.0, "in": -1.0, "-": -1.0}.get(
                num_parts[-1].lower())
            if jm_dir is None:
                continue
            num_parts = num_parts[:-1]
        try:
            nums = list(map(float, num_parts))
        except ValueError:
            continue
        if cmd == "JF" and len(nums) != 6:
            continue
        if jm_dir is not None:
            nums.append(jm_dir)
        raw_segments = shape_to_segments(cmd, nums)
        dx = sum(d[0] for d in delta_stack)
        dy = sum(d[1] for d in delta_stack)
        ang = sum(d[2] for d in delta_stack)
        segments = apply_transform(raw_segments, dx, dy, ang)
        shapes.append((cmd, segments))
        next_is_priority = False
    return {"shapes": shapes, "add_labels": add_labels}


def segments_bbox(segments):
    xs, ys = [], []
    for x1, y1, x2, y2 in segments:
        xs.extend((x1, x2))
        ys.extend((y1, y2))
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def all_segments(parse_result):
    segs = []
    for _cmd, shape_segs in parse_result["shapes"]:
        segs.extend(shape_segs)
    return segs


@dataclass
class Block:
    start: int          # 0-based inclusive
    end: int            # 0-based inclusive (END line)
    add_x: float
    add_y: float
    label: str
    add_raw: str


@dataclass
class BlocksResult:
    blocks: list = field(default_factory=list)
    stray: list = field(default_factory=list)  # (lineno_1based, line)


def parse_blocks(dsl):
    """Split DSL into top-level ADD ... END blocks.

    Nested ADD/END pairs stay inside their parent block. Shape commands
    (and only those) that appear outside any top-level ADD are reported
    in ``stray`` with 1-based line numbers.
    """
    lines = dsl.splitlines()
    blocks = []
    stray = []
    depth = 0
    start = None
    add_x = add_y = 0.0
    label = ""
    add_raw = ""
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        cmd = parts[0]
        if cmd == "ADD":
            if depth == 0:
                if len(parts) < 3:
                    stray.append((i + 1, raw))
                    continue
                try:
                    add_x, add_y = float(parts[1]), float(parts[2])
                except ValueError:
                    stray.append((i + 1, raw))
                    continue
                label = " ".join(parts[3:])
                add_raw = raw
                start = i
            depth += 1
            continue
        if cmd == "END":
            if depth == 0:
                stray.append((i + 1, raw))
                continue
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append(Block(
                    start=start, end=i, add_x=add_x, add_y=add_y,
                    label=label, add_raw=add_raw,
                ))
                start = None
            continue
        if depth == 0 and cmd in SHAPE_CMDS:
            stray.append((i + 1, raw))
    if depth > 0 and start is not None:
        # Unclosed ADD: treat remainder as a block ending at last line
        blocks.append(Block(
            start=start, end=len(lines) - 1, add_x=add_x, add_y=add_y,
            label=label, add_raw=add_raw,
        ))
    return BlocksResult(blocks=blocks, stray=stray)


def block_source(lines, block):
    return "\n".join(lines[block.start:block.end + 1])


def rewrite_add_line(raw, x, y):
    """Replace x, y on an ADD line, keeping the original label text."""
    stripped = raw.strip()
    parts = stripped.split()
    label = " ".join(parts[3:]) if len(parts) > 3 else ""
    prefix = raw[:len(raw) - len(raw.lstrip())] if raw.strip() else ""
    xy = f"ADD {_fmt_coord(x)} {_fmt_coord(y)}"
    return prefix + (f"{xy} {label}" if label else xy)


def _fmt_coord(v):
    r = round(float(v), 2)
    if abs(r) < 1e-12:
        r = 0.0
    if float(r).is_integer():
        return str(int(r))
    s = f"{r:.2f}".rstrip("0").rstrip(".")
    return s


def following_rotate_index(lines, block):
    """Index of a ROTATE that directly follows the block's ADD (skipping
    blanks and comments), or None."""
    for i in range(block.start + 1, block.end):
        s = lines[i].strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if parts[0] == "ROTATE" and len(parts) >= 2:
            return i
        return None
    return None


def apply_rotate90_to_block_lines(lines, block):
    """Return a new list of the block's lines with ROTATE 90 applied.

    If a ROTATE command already directly follows the ADD, add 90 to it;
    otherwise insert 'ROTATE 90' immediately after the ADD line.
    """
    chunk = list(lines[block.start:block.end + 1])
    # indices relative to chunk: ADD is 0
    rel_rot = None
    for j in range(1, len(chunk)):
        s = chunk[j].strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if parts[0] == "ROTATE" and len(parts) >= 2:
            rel_rot = j
        break
    if rel_rot is not None:
        raw = chunk[rel_rot]
        parts = raw.strip().split()
        try:
            ang = float(parts[1]) + 90.0
        except (ValueError, IndexError):
            ang = 90.0
        prefix = raw[:len(raw) - len(raw.lstrip())]
        extra = " ".join(parts[2:])
        body = f"ROTATE {_fmt_coord(ang)}"
        chunk[rel_rot] = prefix + (f"{body} {extra}" if extra else body)
    else:
        chunk.insert(1, "ROTATE 90")
    return chunk


def local_segments_from_lines(block_lines):
    """Parse a block with its top-level ADD rewritten to (0, 0)."""
    if not block_lines:
        return []
    first = block_lines[0]
    stripped = first.strip()
    parts = stripped.split()
    if parts and parts[0] == "ADD" and len(parts) >= 3:
        label = " ".join(parts[3:])
        prefix = first[:len(first) - len(first.lstrip())]
        new_first = prefix + (f"ADD 0 0 {label}" if label else "ADD 0 0")
        text = "\n".join([new_first] + block_lines[1:])
    else:
        text = "\n".join(block_lines)
    return all_segments(parse_text(text))


def bbox_from_segments(segments):
    box = segments_bbox(segments)
    if box is None:
        return None
    minx, miny, maxx, maxy = box
    return {
        "minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy,
        "w": maxx - minx, "h": maxy - miny,
    }
