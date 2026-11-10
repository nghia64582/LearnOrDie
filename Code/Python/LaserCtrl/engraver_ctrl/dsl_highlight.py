"""Preview-only JM/JF highlight footprints.

This module never participates in G-code generation. It only computes
filled polygons for canvas previews (male JM / female JF mortise-tenon
blocks), including ADD offsets and ROTATE, matching dsl_parse geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

from engraver_ctrl.dsl_parse import apply_transform

# Keep in sync with _joint_segments in dsl_parse / tab_designer.


@dataclass(frozen=True)
class JointHighlight:
    kind: str  # "JM" or "JF"
    polygon: tuple[tuple[float, float], ...]  # world-space vertices


def _transform_points(points, dx, dy, angle_deg):
    if not points:
        return points
    # Reuse apply_transform by treating each point as a degenerate segment.
    segs = [(x, y, x, y) for x, y in points]
    out = apply_transform(segs, dx, dy, angle_deg)
    return tuple((x1, y1) for x1, y1, _x2, _y2 in out)


def _joint_polygons_local(cmd, nums):
    """Return local-space footprint polygons for one JM/JF command.

    JF: one axis-aligned rectangle per mortise hole (exact tooth footprint).
    JM: the closed comb of the tenon profile (polyline closed along the base).
    """
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

    if cmd == "JF":
        polys = []
        hv = thick / 2
        for a, b in teeth_pos:
            corners = (pt(a, -hv), pt(b, -hv), pt(b, hv), pt(a, hv))
            polys.append(corners)
        return polys

    if not teeth_pos:
        return []
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
    if len(points) < 3:
        return []
    return [tuple(pt(u, v) for u, v in points)]


def joint_highlights(text):
    """Parse DSL and return world-space JM/JF highlight polygons.

    ADD / ROTATE stacking matches parse_text / tab_designer.preview.
    Invalid lines are skipped. Does not emit or alter G-code.
    """
    highlights = []
    delta_stack = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        cmd = parts[0]
        if cmd == "FIRST":
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
        if cmd not in ("JF", "JM"):
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
        dx = sum(d[0] for d in delta_stack)
        dy = sum(d[1] for d in delta_stack)
        ang = sum(d[2] for d in delta_stack)
        for poly in _joint_polygons_local(cmd, nums):
            highlights.append(JointHighlight(
                kind=cmd,
                polygon=_transform_points(poly, dx, dy, ang),
            ))
    return highlights


def polygons_from_joint_segments(cmd, segments):
    """Rebuild footprint polygons from already-transformed cut segments.

    Used by canvases that already hold preview segments, so fills stay
    aligned with the drawn G-code paths (including after ADD transforms).
    """
    if not segments:
        return []
    if cmd == "JF":
        polys = []
        for i in range(0, len(segments), 4):
            chunk = segments[i:i + 4]
            if len(chunk) < 4:
                break
            pts = tuple((s[0], s[1]) for s in chunk)
            if len(pts) >= 3:
                polys.append(pts)
        return polys
    if cmd == "JM":
        pts = [(segments[0][0], segments[0][1])]
        for s in segments:
            pts.append((s[2], s[3]))
        if len(pts) < 3:
            return []
        return [tuple(pts)]
    return []


def draw_joint_highlights(canvas, highlights, to_canvas, tags=()):
    """Fill highlight polygons on a Tk canvas. Call before drawing paths."""
    from common.ui import JF_HIGHLIGHT, JM_HIGHLIGHT

    colors = {"JM": JM_HIGHLIGHT, "JF": JF_HIGHLIGHT}
    item_ids = []
    for hl in highlights:
        color = colors.get(hl.kind)
        if not color or len(hl.polygon) < 3:
            continue
        coords = []
        for x, y in hl.polygon:
            px, py = to_canvas(x, y)
            coords.extend((px, py))
        if len(coords) < 6:
            continue
        item_ids.append(canvas.create_polygon(
            *coords, fill=color, outline="", tags=tags + ("jmjf_hl",),
        ))
    return item_ids
