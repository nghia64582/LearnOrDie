"""G2/G3 arc interpolation for Simulate and Machine (G17 / XY, Y up).

I/J are offsets from the start point to the centre (GRBL / LinuxCNC).
R is a signed radius: positive = arc of at most 180 deg, negative = the
longer one. A full circle needs I/J (R cannot describe it).

G2 is clockwise and G3 is counter-clockwise, viewed from +Z.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

TWO_PI = 2.0 * math.pi
_TOL = 1e-9

# Chord error target (mm) when splitting an arc into straight steps.
DEFAULT_MAX_CHORD = 0.4
DEFAULT_MIN_SEGS = 8


def _hypot(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


def arc_sweep(a0: float, a1: float, clockwise: bool, full_circle: bool) -> float:
    """Positive sweep angle (radians) from a0 to a1 in the given direction."""
    if full_circle:
        return TWO_PI
    if clockwise:
        sweep = (a0 - a1) % TWO_PI
    else:
        sweep = (a1 - a0) % TWO_PI
    if sweep < _TOL:
        return TWO_PI if full_circle else 0.0
    return sweep


def interpolate_arc(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    cx: float,
    cy: float,
    clockwise: bool,
    max_chord: float = DEFAULT_MAX_CHORD,
    min_segs: int = DEFAULT_MIN_SEGS,
) -> List[Tuple[float, float]]:
    """Return intermediate points from just after the start through (x2, y2)."""
    r = _hypot(x1 - cx, y1 - cy)
    if r <= _TOL:
        if _hypot(x2 - x1, y2 - y1) > _TOL:
            return [(x2, y2)]
        return []

    a0 = math.atan2(y1 - cy, x1 - cx)
    a1 = math.atan2(y2 - cy, x2 - cx)
    full = _hypot(x2 - x1, y2 - y1) <= _TOL
    sweep = arc_sweep(a0, a1, clockwise, full)
    if sweep <= _TOL:
        return []

    if max_chord > 0 and r > 0:
        # chord = 2 r sin(dtheta/2)
        ratio = min(1.0, max_chord / (2.0 * r))
        dtheta = 2.0 * math.asin(ratio)
        n = max(int(min_segs), int(math.ceil(sweep / max(dtheta, 1e-9))))
    else:
        n = max(int(min_segs), 1)

    pts: List[Tuple[float, float]] = []
    for i in range(1, n + 1):
        t = i / n
        a = a0 - t * sweep if clockwise else a0 + t * sweep
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts[-1] = (float(x2), float(y2))
    return pts


def center_from_ij(x1: float, y1: float, i: float, j: float) -> Tuple[float, float]:
    return (x1 + i, y1 + j)


def center_from_r(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    r: float,
    clockwise: bool,
) -> Tuple[float, float]:
    """Centre of a G2/G3 R-word arc (G17)."""
    dx, dy = x2 - x1, y2 - y1
    chord = _hypot(dx, dy)
    if chord <= _TOL:
        raise ValueError("R-word arc needs distinct start and end points")
    abs_r = abs(float(r))
    half = chord / 2.0
    if abs_r + 1e-6 < half:
        raise ValueError(
            f"R-word radius {r} is shorter than half the chord {half}"
        )
    # Geometric height from midpoint to centre.
    h = math.sqrt(max(0.0, abs_r * abs_r - half * half))
    ux, uy = dx / chord, dy / chord
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    # Two candidate centres, offset along the perpendicular.
    candidates = (
        (mx - uy * h, my + ux * h),
        (mx + uy * h, my - ux * h),
    )

    def sweep_of(c):
        a0 = math.atan2(y1 - c[1], x1 - c[0])
        a1 = math.atan2(y2 - c[1], x2 - c[0])
        return arc_sweep(a0, a1, clockwise, full_circle=False)

    want_minor = r >= 0
    picked = None
    for c in candidates:
        is_minor = sweep_of(c) <= math.pi + 1e-8
        if is_minor == want_minor:
            picked = c
            break
    if picked is None:
        # Semicircle (h ~ 0): both centres collapse; either works.
        picked = candidates[0]
    return picked


def interpolate_g2g3(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    clockwise: bool,
    i: Optional[float] = None,
    j: Optional[float] = None,
    r: Optional[float] = None,
    max_chord: float = DEFAULT_MAX_CHORD,
    min_segs: int = DEFAULT_MIN_SEGS,
) -> List[Tuple[float, float]]:
    """Interpolate a G2/G3 move. I/J wins if both I/J and R are given."""
    has_ij = i is not None or j is not None
    if has_ij:
        cx, cy = center_from_ij(x1, y1, float(i or 0.0), float(j or 0.0))
    elif r is not None:
        cx, cy = center_from_r(x1, y1, x2, y2, float(r), clockwise)
    else:
        raise ValueError("G2/G3 needs I/J or R")
    return interpolate_arc(
        x1, y1, x2, y2, cx, cy, clockwise,
        max_chord=max_chord, min_segs=min_segs,
    )



def arc_length(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    clockwise: bool,
    i: Optional[float] = None,
    j: Optional[float] = None,
    r: Optional[float] = None,
) -> float:
    """Exact XY arc length (mm) of a G2/G3 move. I/J wins over R."""
    has_ij = i is not None or j is not None
    if has_ij:
        cx, cy = center_from_ij(x1, y1, float(i or 0.0), float(j or 0.0))
    elif r is not None:
        cx, cy = center_from_r(x1, y1, x2, y2, float(r), clockwise)
    else:
        return _hypot(x2 - x1, y2 - y1)
    radius = _hypot(x1 - cx, y1 - cy)
    if radius <= _TOL:
        return _hypot(x2 - x1, y2 - y1)
    a0 = math.atan2(y1 - cy, x1 - cx)
    a1 = math.atan2(y2 - cy, x2 - cx)
    full = _hypot(x2 - x1, y2 - y1) <= _TOL
    return radius * arc_sweep(a0, a1, clockwise, full)


def word_value(text: str, letter: str) -> Optional[float]:
    """Extract a G-code word (X, I, R, ...) from a parameter string."""
    import re
    match = re.search(
        rf"{letter}(-?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if match:
        return float(match.group(1))
    return None
