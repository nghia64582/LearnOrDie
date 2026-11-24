"""Generate card-formatted box DSL (R outlines via card borders, J marks only).

All six faces keep the *outer* dimensions of the box:

  top / bottom     L x W
  front / behind   L x H
  left / right     W x H

Each face uses a local 2D frame with x to the right and y up. Edges are
named up (y = height), down (y = 0), left (x = 0), right (x = width).

J marks sit flush inside the face on the shared edge, thickness t, and
span the full edge length. Output is only R (the card border) and J;
the user runs Apply joints in Custom to expand J into JM/JF.

JM/JF role overrides are assigned so opposite walls alternate and the
lid/base are mortises on every edge. That keeps the tenon/mortise
pattern complementary at each box corner (see PAIRINGS).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engraver_ctrl.dsl_cards import Card, assemble_cards
from engraver_ctrl.dsl_joint import (
    DEFAULT_TEETH_DIVISIONS,
    THICKNESS,
    fmt_num,
    normalize_teeth_divisions,
)


FACE_NAMES = ("top", "bottom", "left", "right", "behind", "front")

# Local (width, height) = (x size, y size) for each face.
_FACE_SIZE = {
    "top": "LW",
    "bottom": "LW",
    "front": "LH",
    "behind": "LH",
    "left": "WH",
    "right": "WH",
}

# Wall row (y = 0) then lid row (y = wall height), packed left to right
# with no gap. Missing faces are skipped so the remaining pieces close up.
WALL_ORDER = ("left", "front", "right", "behind")
LID_ORDER = ("bottom", "top")

# (face_a, edge_a, face_b, edge_b, pair_name, role_a, role_b)
# Roles: top/bottom always F (mortise); front/behind always M (tenon);
# left/right are M on the lid edges (up/down) and F on the vertical edges.
PAIRINGS = (
    ("top", "down", "front", "up", "TOP_FRONT", "F", "M"),
    ("top", "up", "behind", "up", "TOP_BEHIND", "F", "M"),
    ("top", "left", "left", "up", "TOP_LEFT", "F", "M"),
    ("top", "right", "right", "up", "TOP_RIGHT", "F", "M"),
    ("bottom", "up", "front", "down", "BOTTOM_FRONT", "F", "M"),
    ("bottom", "down", "behind", "down", "BOTTOM_BEHIND", "F", "M"),
    ("bottom", "left", "left", "down", "BOTTOM_LEFT", "F", "M"),
    ("bottom", "right", "right", "down", "BOTTOM_RIGHT", "F", "M"),
    ("front", "right", "right", "left", "FRONT_RIGHT", "M", "F"),
    ("right", "right", "behind", "left", "RIGHT_BEHIND", "F", "M"),
    ("behind", "right", "left", "left", "BEHIND_LEFT", "M", "F"),
    ("left", "right", "front", "left", "LEFT_FRONT", "F", "M"),
)


@dataclass
class JointSpec:
    """One J mark on a face."""

    pair_name: str
    edge: str
    x: float
    y: float
    w: float
    h: float
    role: str  # "M" or "F"


@dataclass
class FaceSpec:
    name: str
    width: float
    height: float
    dx: float
    dy: float
    joints: list = field(default_factory=list)


@dataclass
class PairSpec:
    name: str
    face_a: str
    edge_a: str
    face_b: str
    edge_b: str
    role_a: str
    role_b: str
    length: float


@dataclass
class BoxResult:
    dsl: str
    faces: list = field(default_factory=list)
    pairs: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    length: float = 0.0
    width: float = 0.0
    height: float = 0.0
    thickness: float = THICKNESS


def face_size(name, length, width, height):
    """Return (local_width, local_height) for a named face."""
    kind = _FACE_SIZE.get(name)
    if kind is None:
        raise ValueError(f"Unknown face: {name!r}")
    if kind == "LW":
        return float(length), float(width)
    if kind == "LH":
        return float(length), float(height)
    return float(width), float(height)


def edge_length(face_w, face_h, edge):
    if edge in ("up", "down"):
        return float(face_w)
    if edge in ("left", "right"):
        return float(face_h)
    raise ValueError(f"Unknown edge: {edge!r}")


def edge_joint_rect(face_w, face_h, edge, thickness):
    """Axis-aligned J rectangle flush inside the face on ``edge``.

    Returns (x, y, w, h) in the face's local frame.
    """
    t = float(thickness)
    fw, fh = float(face_w), float(face_h)
    if edge == "down":
        return (0.0, 0.0, fw, t)
    if edge == "up":
        return (0.0, fh - t, fw, t)
    if edge == "left":
        return (0.0, 0.0, t, fh)
    if edge == "right":
        return (fw - t, 0.0, t, fh)
    raise ValueError(f"Unknown edge: {edge!r}")


def pair_edge_length(pair_name, length, width, height):
    """Shared edge length of a named pairing, independent of thickness."""
    for face_a, edge_a, _face_b, _edge_b, name, _ra, _rb in PAIRINGS:
        if name == pair_name:
            fw, fh = face_size(face_a, length, width, height)
            return edge_length(fw, fh, edge_a)
    raise ValueError(f"Unknown pair: {pair_name!r}")


def normalize_faces(faces):
    """Return a unique tuple of valid face names, defaulting to all six."""
    if faces is None:
        return FACE_NAMES
    seen = []
    unknown = []
    for name in faces:
        key = str(name).strip().lower()
        if key not in _FACE_SIZE:
            unknown.append(name)
            continue
        if key not in seen:
            seen.append(key)
    if unknown:
        raise ValueError("Unknown face(s): " + ", ".join(map(str, unknown)))
    return tuple(seen)


def _as_positive(name, value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a positive number") from None
    if number <= 0:
        raise ValueError(f"{name} must be a positive number")
    return number


def layout_faces(selected, sizes):
    """Place selected faces with no overlap and no inter-piece gap.

    Walls (left, front, right, behind) sit on the y=0 shelf, packed
    left to right. Lids (bottom, top) sit on a second shelf at y equal
    to the wall-row height (or 0 if no wall is present).
    """
    positions = {}
    x = 0.0
    wall_h = 0.0
    for name in WALL_ORDER:
        if name not in selected:
            continue
        w, h = sizes[name]
        positions[name] = (x, 0.0)
        x += w
        wall_h = max(wall_h, h)
    x = 0.0
    y = wall_h
    for name in LID_ORDER:
        if name not in selected:
            continue
        w, h = sizes[name]
        positions[name] = (x, y)
        x += w
    return positions


def _boxes_overlap(a, b, eps=1e-9):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax + aw > bx + eps and bx + bw > ax + eps
            and ay + ah > by + eps and by + bh > ay + eps)


def _validate_layout(positions, sizes):
    names = list(positions)
    for i, a in enumerate(names):
        ax, ay = positions[a]
        aw, ah = sizes[a]
        for b in names[i + 1:]:
            bx, by = positions[b]
            bw, bh = sizes[b]
            if _boxes_overlap((ax, ay, aw, ah), (bx, by, bw, bh)):
                raise RuntimeError(
                    f"Face overlap: {a} ({ax}, {ay}, {aw}, {ah}) vs "
                    f"{b} ({bx}, {by}, {bw}, {bh})"
                )


def _joint_line(joint):
    return (
        f"J {fmt_num(joint.x)} {fmt_num(joint.y)} "
        f"{fmt_num(joint.w)} {fmt_num(joint.h)} "
        f"{joint.pair_name} {joint.role}"
    )


def _header_lines(length, width, height, thickness, selected, warnings):
    faces = ", ".join(name for name in FACE_NAMES if name in selected)
    lines = [
        f"# Box L={fmt_num(length)} W={fmt_num(width)} "
        f"H={fmt_num(height)} t={fmt_num(thickness)}",
        f"# Faces: {faces or '(none)'}",
        "# Output is R (card border) and J marks only; "
        "run Apply joints in Custom to get JM/JF.",
    ]
    for warning in warnings:
        lines.append(f"# Warning: {warning}")
    return lines


def build_box(length, width, height, thickness=THICKNESS, faces=None,
              k=DEFAULT_TEETH_DIVISIONS):
    """Build card-formatted DSL for the selected box faces.

    Returns a :class:`BoxResult`. Raises ValueError on invalid inputs.
    """
    length = _as_positive("Length L", length)
    width = _as_positive("Width W", width)
    height = _as_positive("Height H", height)
    thickness = _as_positive("Thickness t", thickness)
    selected = normalize_faces(faces)
    if not selected:
        raise ValueError("Select at least one face.")
    for label, value in (("L", length), ("W", width), ("H", height)):
        if value <= thickness:
            raise ValueError(
                f"{label} must be greater than thickness t "
                f"({fmt_num(thickness)} mm)"
            )

    sizes = {name: face_size(name, length, width, height) for name in selected}
    positions = layout_faces(selected, sizes)
    _validate_layout(positions, sizes)

    joints_by_face = {name: [] for name in selected}
    pairs = []
    for face_a, edge_a, face_b, edge_b, name, role_a, role_b in PAIRINGS:
        if face_a not in selected or face_b not in selected:
            continue
        aw, ah = sizes[face_a]
        bw, bh = sizes[face_b]
        len_a = edge_length(aw, ah, edge_a)
        len_b = edge_length(bw, bh, edge_b)
        if abs(len_a - len_b) > 1e-9:
            raise RuntimeError(
                f"Edge length mismatch for {name}: "
                f"{face_a}.{edge_a}={fmt_num(len_a)} vs "
                f"{face_b}.{edge_b}={fmt_num(len_b)}"
            )
        ax, ay, awj, ahj = edge_joint_rect(aw, ah, edge_a, thickness)
        bx, by, bwj, bhj = edge_joint_rect(bw, bh, edge_b, thickness)
        joints_by_face[face_a].append(JointSpec(
            pair_name=name, edge=edge_a, x=ax, y=ay, w=awj, h=ahj, role=role_a,
        ))
        joints_by_face[face_b].append(JointSpec(
            pair_name=name, edge=edge_b, x=bx, y=by, w=bwj, h=bhj, role=role_b,
        ))
        pairs.append(PairSpec(
            name=name, face_a=face_a, edge_a=edge_a,
            face_b=face_b, edge_b=edge_b,
            role_a=role_a, role_b=role_b, length=len_a,
        ))

    warnings = []
    k_val, k_err = normalize_teeth_divisions(k)
    if k_err:
        warnings.append(k_err)
    else:
        for pair in pairs:
            if pair.length / k_val < thickness - 1e-9:
                warnings.append(
                    f"{pair.name}: edge {fmt_num(pair.length)} mm / k={k_val} "
                    f"= {fmt_num(pair.length / k_val)} mm is thinner than t="
                    f"{fmt_num(thickness)} mm, so a JF hole may reach the "
                    "t x t corner zone"
                )

    # Stable face order in the DSL: lids then walls, matching FACE_NAMES
    # is less compact-looking; use bottom, top, left, front, right, behind
    # so the first pieces in the file start at the origin when present.
    emit_order = ("bottom", "top", "left", "front", "right", "behind")
    face_specs = []
    cards = []
    for name in emit_order:
        if name not in selected:
            continue
        fw, fh = sizes[name]
        dx, dy = positions[name]
        joints = joints_by_face[name]
        inner = "\n".join(_joint_line(j) for j in joints)
        face_specs.append(FaceSpec(
            name=name, width=fw, height=fh, dx=dx, dy=dy, joints=joints,
        ))
        cards.append(Card(
            name=name, dx=dx, dy=dy, inner=inner,
            w=fw, h=fh, border=True,
        ))

    body = assemble_cards(cards)
    header = "\n".join(_header_lines(
        length, width, height, thickness, set(selected), warnings,
    ))
    dsl = header + "\n" + body
    if not dsl.endswith("\n"):
        dsl += "\n"

    return BoxResult(
        dsl=dsl,
        faces=face_specs,
        pairs=pairs,
        warnings=warnings,
        length=length,
        width=width,
        height=height,
        thickness=thickness,
    )
