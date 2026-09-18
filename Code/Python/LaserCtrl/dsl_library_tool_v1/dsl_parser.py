from dataclasses import dataclass, field
import math


KNOWN = {"C", "R", "RC", "LH", "LV", "L", "A", "P", "M"}


@dataclass
class DSLError:
    line: int
    message: str


@dataclass
class ParseResult:
    segments: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    bounds: object = None


def shape_to_segments(cmd, nums):
    if cmd == "L":
        if len(nums) != 4:
            raise ValueError("L requires 4 numbers")
        x1, y1, x2, y2 = nums
        return [(x1, y1, x2, y2)]

    if cmd == "LH":
        if len(nums) != 3:
            raise ValueError("LH requires 3 numbers")
        x, y, length = nums
        return [(x, y, x + length, y)]

    if cmd == "LV":
        if len(nums) != 3:
            raise ValueError("LV requires 3 numbers")
        x, y, length = nums
        return [(x, y, x, y + length)]

    if cmd in ("R", "RC"):
        if len(nums) != 4:
            raise ValueError(f"{cmd} requires 4 numbers")
        if cmd == "R":
            x, y, w, h = nums
        else:
            cx, cy, w, h = nums
            x, y = cx - w / 2, cy - h / 2
        return [
            (x, y, x + w, y),
            (x + w, y, x + w, y + h),
            (x + w, y + h, x, y + h),
            (x, y + h, x, y),
        ]

    if cmd in ("C", "A"):
        if cmd == "C":
            if len(nums) != 3:
                raise ValueError("C requires 3 numbers")
            cx, cy, r = nums
            start, end = 0, 360
        else:
            if len(nums) != 5:
                raise ValueError("A requires 5 numbers")
            cx, cy, r, start, end = nums

        # Preview approximation. G-code generator can keep its exact/tab-aware arc routine.
        if r < 0:
            raise ValueError("radius must be >= 0")
        n = max(12, int(abs(end - start) / 5))
        pts = []
        for i in range(n + 1):
            a = math.radians(start + (end - start) * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return [(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
                for i in range(len(pts) - 1)]

    if cmd in ("P", "M"):
        if len(nums) < 4 or len(nums) % 2:
            raise ValueError(f"{cmd} requires an even number of coordinates")
        pts = [(nums[i], nums[i+1]) for i in range(0, len(nums), 2)]
        limit = len(pts) if cmd == "P" else len(pts) - 1
        return [
            (pts[i][0], pts[i][1], pts[(i+1) % len(pts)][0], pts[(i+1) % len(pts)][1])
            for i in range(limit)
        ]

    raise ValueError(f"Unknown command: {cmd}")


def transform_segment(seg, dx, dy, angle):
    x1, y1, x2, y2 = seg
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)

    def f(x, y):
        return x * c - y * s + dx, x * s + y * c + dy

    p1 = f(x1, y1)
    p2 = f(x2, y2)
    return (*p1, *p2)


def parse_dsl(text):
    result = ParseResult()
    stack = []
    priority_next = False

    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        cmd = parts[0]

        if cmd == "FIRST":
            priority_next = True
            continue

        if cmd == "ADD":
            if len(parts) < 3:
                result.errors.append(DSLError(line_no, "ADD requires x y [label]"))
                continue
            try:
                dx, dy = float(parts[1]), float(parts[2])
            except ValueError:
                result.errors.append(DSLError(line_no, "ADD x and y must be numbers"))
                continue
            label = " ".join(parts[3:])
            stack.append((dx, dy, 0.0, label))
            cum_x = sum(x[0] for x in stack)
            cum_y = sum(x[1] for x in stack)
            if label:
                result.labels.append((cum_x, cum_y, label))
            continue

        if cmd == "ROTATE":
            if len(parts) != 2:
                result.errors.append(DSLError(line_no, "ROTATE requires angle"))
                continue
            try:
                angle = float(parts[1])
            except ValueError:
                result.errors.append(DSLError(line_no, "ROTATE angle must be a number"))
                continue
            stack.append((0.0, 0.0, angle, None))
            continue

        if cmd == "END":
            if stack:
                stack.pop()
            else:
                result.errors.append(DSLError(line_no, "END without matching ADD/ROTATE"))
            continue

        if cmd not in KNOWN:
            result.errors.append(DSLError(line_no, f"Unknown command: {cmd}"))
            continue

        try:
            nums = list(map(float, parts[1:]))
            raw_segments = shape_to_segments(cmd, nums)
        except ValueError as e:
            result.errors.append(DSLError(line_no, str(e)))
            continue

        dx = sum(x[0] for x in stack)
        dy = sum(x[1] for x in stack)
        angle = sum(x[2] for x in stack)

        for seg in raw_segments:
            result.segments.append(transform_segment(seg, dx, dy, angle))

    if stack:
        result.errors.append(DSLError(len(text.splitlines()) or 1, "Unclosed ADD/ROTATE block"))

    result.bounds = calculate_bounds(result.segments, result.labels)
    return result


def calculate_bounds(segments, labels):
    xs, ys = [], []
    for x1, y1, x2, y2 in segments:
        xs += [x1, x2]
        ys += [y1, y2]
    for x, y, _ in labels:
        xs.append(x)
        ys.append(y)

    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)
