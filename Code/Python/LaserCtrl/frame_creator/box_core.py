"""
Box-frame assembler.

Takes centerline rectangles (same convention as the skeleton tool), a
column length H, a shared strip width, and a frame count. Builds:

  - rails: cut-list of one frame, repeated `frames` times, packed by
    rail_cutlist_core
  - joints: one hole-variant joint per node per frame, packed by
    joint_nesting (cell_size stays 10 mm; not strip-width-aware)
  - beams: one L/T/Plus stick per node (not per frame), length = H,
    from beam_dsl_core

The three groups are wrapped in top-level ADD ... END blocks and placed
side by side with a small gap so they do not overlap.
"""

from frame_creator.beam_dsl_core import (
    STRIP_WIDTH_DEFAULT,
    TOOTH,
    build_sheet,
)
from frame_creator.rail_skeleton_core import build_skeleton, cut_list

CELL_SIZE = 10.0
GROUP_GAP = 5.0
JOINT_WARNING = (
    "Joints are not width-aware yet (cell size stays 10 mm; holes are not scaled)."
)


def _g(v):
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def format_length(v):
    return str(round(v, 2)) if v != int(v) else str(int(v))


def format_length_list(lengths):
    return ",".join(format_length(v) for v in lengths)


def count_nodes(skeleton):
    """Map skeleton node labels to beam/joint types (T-rot counts as T)."""
    counts = {"L": 0, "T": 0, "P": 0}
    for n in skeleton["nodes"]:
        label = n["label"]
        if label == "L":
            counts["L"] += 1
        elif label in ("T", "T-rot"):
            counts["T"] += 1
        elif label == "+":
            counts["P"] += 1
        else:
            raise ValueError(f"Unknown node label: {label!r}")
    return counts


def _min_joint_rows(joint_counts):
    rows = 1
    if joint_counts.get("L", 0):
        rows = max(rows, 2)
    if joint_counts.get("T", 0) or joint_counts.get("P", 0):
        rows = max(rows, 3)
    return rows


def _choose_joint_rows(joint_counts, target_height_mm):
    if sum(joint_counts.values()) == 0:
        return 0
    guess = max(1, int(round(float(target_height_mm) / CELL_SIZE)))
    return max(_min_joint_rows(joint_counts), guess)


def _boxes_overlap(a, b, eps=1e-9):
    """Axis-aligned boxes as (x, y, w, h). Touching edges is OK."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax + aw > bx + eps and bx + bw > ax + eps
            and ay + ah > by + eps and by + bh > ay + eps)


def _layout_groups(pieces, gap=GROUP_GAP):
    """pieces: list of (name, width, height, dsl). Skip empty dsl/size.
    Place left to right along y=0. Returns list of dicts."""
    x = 0.0
    groups = []
    for name, width, height, dsl in pieces:
        if not dsl or width <= 0:
            continue
        groups.append({
            "name": name,
            "x": x,
            "y": 0.0,
            "w": width,
            "h": height,
            "dsl": dsl,
        })
        x += width + gap
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            box_a = (a["x"], a["y"], a["w"], a["h"])
            box_b = (b["x"], b["y"], b["w"], b["h"])
            if _boxes_overlap(box_a, box_b):
                raise RuntimeError(
                    f"Group overlap: {a['name']} {box_a} vs {b['name']} {box_b}"
                )
    return groups


def _wrap_group(group):
    inner = group["dsl"].strip("\n")
    parts = [f"ADD {_g(group['x'])} {_g(group['y'])} {group['name']}"]
    if inner:
        parts.append(inner)
    parts.append("END")
    return "\n".join(parts)


def _header_lines(rects, height, strip_width, frames, nodes, joint_counts,
                  lengths, total_rail_length, groups):
    rect_txt = "; ".join(f"{format_length(x)} {format_length(y)} "
                         f"{format_length(w)} {format_length(h)}"
                         for x, y, w, h in rects)
    group_txt = ", ".join(
        f"{g['name']} {_g(g['w'])}x{_g(g['h'])} at ({_g(g['x'])},{_g(g['y'])})"
        for g in groups
    )
    lines = [
        "# Box frame DSL",
        f"# Centerline rects: {rect_txt}",
        f"# Height H: {format_length(height)} mm (column length)",
        f"# Strip width: {format_length(strip_width)} mm",
        f"# Frames: {int(frames)}",
        f"# Nodes (per frame): L={nodes['L']} T={nodes['T']} +={nodes['P']}",
        f"# Joints (all with hole): L={joint_counts['L']} "
        f"T={joint_counts['T']} +={joint_counts['P']}",
        f"# Columns (beams): L={nodes['L']} T={nodes['T']} +={nodes['P']} "
        f"length={format_length(height)}",
        f"# Rails (1 frame): {format_length_list(lengths)}",
        f"# Rails (x{int(frames)}): {len(lengths) * int(frames)} pieces, "
        f"total length {format_length(total_rail_length)} mm",
        f"# Groups: {group_txt}",
    ]
    if abs(float(strip_width) - CELL_SIZE) > 1e-9:
        lines.append(f"# Note: {JOINT_WARNING}")
    return lines


def build_box(rects, height, strip_width=STRIP_WIDTH_DEFAULT, frames=2,
              time_limit=15.0):
    """Build the packed box-frame DSL and a result dict for the GUI.

    rects: list of (x, y, w, h) centerline rectangles (mm).
    height: column / beam length H (mm).
    strip_width: shared rail / beam flange width (mm).
    frames: number of identical planar frames (1 = bottom only, 2 = bottom+top).
    """
    if not rects:
        raise ValueError("Enter at least one rectangle.")
    height = float(height)
    if height <= 0:
        raise ValueError("Height must be a positive number.")
    strip_width = float(strip_width)
    if strip_width <= 0:
        raise ValueError("Strip width must be a positive number.")
    if strip_width <= TOOTH:
        raise ValueError(
            f"Strip width must be greater than material thickness ({TOOTH:g} mm)."
        )
    frames = int(frames)
    if frames < 1:
        raise ValueError("Frames must be an integer >= 1.")

    from frame_creator.rail_cutlist_core import build_rail_dsl, optimize_layout
    from frame_creator.joint_nesting_gui import (
        assign_variants,
        build_dsl,
        solve_min_columns,
    )

    skeleton = build_skeleton(rects, rail_width=strip_width)
    lengths = list(cut_list(skeleton))
    nodes = count_nodes(skeleton)
    joint_counts = {k: v * frames for k, v in nodes.items()}
    rail_lengths = list(lengths) * frames
    total_rail_length = sum(lengths) * frames

    rail_dsl, rail_w, rail_h = "", 0.0, 0.0
    rail_placements = []
    if rail_lengths:
        rail_placements, rail_w, rail_h = optimize_layout(
            rail_lengths, rail_width=strip_width, time_limit=time_limit
        )
        rail_dsl = build_rail_dsl(rail_placements, rail_width=strip_width)

    joint_dsl, joint_w, joint_h = "", 0.0, 0.0
    joint_rows = joint_cols = 0
    placed_joints = []
    if sum(joint_counts.values()) > 0:
        target_h = max(height, rail_h if rail_h else 0.0, CELL_SIZE)
        joint_rows = _choose_joint_rows(joint_counts, target_h)
        last_err = None
        placed = None
        for extra in range(0, 16, 2):
            try:
                joint_cols, placed = solve_min_columns(
                    joint_counts, joint_rows + extra,
                    time_limit_per_try=time_limit,
                )
                joint_rows = joint_rows + extra
                break
            except RuntimeError as e:
                last_err = e
        if placed is None:
            raise RuntimeError(f"Could not pack joints: {last_err}")
        placed_joints = assign_variants(placed, hole_counts=joint_counts)
        if any(not p["has_hole"] for p in placed_joints):
            raise RuntimeError("Expected every joint to have a hole.")
        joint_dsl = build_dsl(placed_joints, cell_size=CELL_SIZE)
        joint_w = joint_cols * CELL_SIZE
        joint_h = joint_rows * CELL_SIZE

    beam_dsl, beam_w, beam_h = "", 0.0, 0.0
    beam_instances = []
    if sum(nodes.values()) > 0:
        beam_dsl, beam_instances, beam_w = build_sheet(
            nodes["L"], nodes["T"], nodes["P"], height,
            strip_width=strip_width,
        )
        beam_h = height

    groups = _layout_groups([
        ("rails", rail_w, rail_h, rail_dsl),
        ("joints", joint_w, joint_h, joint_dsl),
        ("beams", beam_w, beam_h, beam_dsl),
    ])

    header = _header_lines(
        rects, height, strip_width, frames, nodes, joint_counts,
        lengths, total_rail_length, groups,
    )
    body = "\n".join(_wrap_group(g) for g in groups)
    dsl = "\n".join(header) + "\n" + body + ("\n" if body else "")

    return {
        "dsl": dsl,
        "skeleton": skeleton,
        "nodes": nodes,
        "joint_counts": joint_counts,
        "beam_counts": dict(nodes),
        "lengths": lengths,
        "rail_lengths": rail_lengths,
        "total_rail_length": total_rail_length,
        "frames": frames,
        "height": height,
        "strip_width": strip_width,
        "rects": rects,
        "groups": groups,
        "rail_placements": rail_placements,
        "placed_joints": placed_joints,
        "beam_instances": beam_instances,
        "joint_rows": joint_rows,
        "joint_cols": joint_cols,
        "warning": JOINT_WARNING if abs(strip_width - CELL_SIZE) > 1e-9 else "",
        "free_ends": list(skeleton.get("free_ends") or []),
    }
