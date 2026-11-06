"""DSL strip nesting: CP-SAT packing plus rewrite of top-level ADD lines."""

import math
import os
import time

from ortools.sat.python import cp_model

from engraver_ctrl.dsl_parse import (
    apply_rotate90_to_block_lines,
    bbox_from_segments,
    local_segments_from_lines,
    parse_blocks,
    rewrite_add_line,
)

SCALE = 100  # 0.01 mm -> integer CP-SAT units


def _snap(v):
    return round(v * 2) / 2


def fmt_num(v):
    r = _snap(v)
    return str(int(r)) if float(r).is_integer() else f"{r:.1f}"


def solve_packing(instances, H, time_limit=20.0, scale=None):
    """
    instances: list of dict {id, name, w, h, rotate}
    H: chiều cao tấm cố định (mm)
    Trả về dict: placements, infeasible, status, W_used
    """
    if scale is None:
        scale = SCALE
    H_s = round(H * scale)

    feasible_items = []
    infeasible = []
    for inst in instances:
        w_s = round(inst["w"] * scale)
        h_s = round(inst["h"] * scale)
        can_normal = h_s <= H_s
        can_rot = inst["rotate"] and w_s <= H_s
        if not can_normal and not can_rot:
            infeasible.append(inst)
            continue
        feasible_items.append((inst, w_s, h_s, can_normal, can_rot))

    if not feasible_items:
        return {"placements": [], "infeasible": infeasible + [i for i in instances if i not in infeasible],
                "status": "NO_ITEMS", "W_used": 0}

    model = cp_model.CpModel()
    n = len(feasible_items)

    ub_w = sum((max(w_s, h_s) if inst["rotate"] else w_s) for inst, w_s, h_s, _, _ in feasible_items)
    ub_w = max(ub_w, 1)
    total_area = sum(w_s * h_s for _, w_s, h_s, _, _ in feasible_items)
    lb_w = max(1, math.ceil(total_area / H_s))

    x_vars, y_vars, w_vars, h_vars, rot_vars = [], [], [], [], []
    x_intervals, y_intervals = [], []

    for idx, (inst, w_s, h_s, can_normal, can_rot) in enumerate(feasible_items):
        if can_normal and can_rot and w_s != h_s:
            rot = model.NewBoolVar(f"rot_{idx}")
            w_v = model.NewIntVar(0, ub_w, f"w_{idx}")
            h_v = model.NewIntVar(0, H_s, f"h_{idx}")
            model.Add(w_v == w_s).OnlyEnforceIf(rot.Not())
            model.Add(w_v == h_s).OnlyEnforceIf(rot)
            model.Add(h_v == h_s).OnlyEnforceIf(rot.Not())
            model.Add(h_v == w_s).OnlyEnforceIf(rot)
        elif can_normal:
            rot = model.NewConstant(0)
            w_v = model.NewIntVar(w_s, w_s, f"w_{idx}")
            h_v = model.NewIntVar(h_s, h_s, f"h_{idx}")
        else:  # chỉ vừa khi xoay
            rot = model.NewConstant(1)
            w_v = model.NewIntVar(h_s, h_s, f"w_{idx}")
            h_v = model.NewIntVar(w_s, w_s, f"h_{idx}")

        x = model.NewIntVar(0, ub_w, f"x_{idx}")
        y = model.NewIntVar(0, H_s, f"y_{idx}")
        model.Add(y + h_v <= H_s)

        x_end = model.NewIntVar(0, ub_w, f"xend_{idx}")
        model.Add(x_end == x + w_v)
        y_end = model.NewIntVar(0, H_s, f"yend_{idx}")
        model.Add(y_end == y + h_v)

        x_iv = model.NewIntervalVar(x, w_v, x_end, f"xi_{idx}")
        y_iv = model.NewIntervalVar(y, h_v, y_end, f"yi_{idx}")

        x_vars.append(x); y_vars.append(y)
        w_vars.append(w_v); h_vars.append(h_v); rot_vars.append(rot)
        x_intervals.append(x_iv); y_intervals.append(y_iv)

    model.AddNoOverlap2D(x_intervals, y_intervals)

    W = model.NewIntVar(lb_w, ub_w, "W")
    for idx in range(n):
        model.Add(x_vars[idx] + w_vars[idx] <= W)
    model.Minimize(W)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = min(8, max(1, os.cpu_count() or 4))
    status = solver.Solve(model)
    status_name = solver.StatusName(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"placements": [], "infeasible": instances, "status": status_name, "W_used": 0}

    placements = []
    for idx, (inst, w_s, h_s, can_normal, can_rot) in enumerate(feasible_items):
        xv = solver.Value(x_vars[idx]) / scale
        yv = solver.Value(y_vars[idx]) / scale
        wv = solver.Value(w_vars[idx]) / scale
        hv = solver.Value(h_vars[idx]) / scale
        rotated = solver.Value(rot_vars[idx]) == 1
        placements.append({
            "id": inst["id"], "name": inst["name"],
            "x": xv, "y": yv, "w": wv, "h": hv,
            "rotated": rotated, "origW": inst["w"], "origH": inst["h"],
            "innerText": inst.get("innerText", ""),
        })

    W_used = solver.Value(W) / scale
    return {"placements": placements, "infeasible": infeasible, "status": status_name, "W_used": W_used}


def pieces_to_dsl(placements, W_used, H):
    lines = [f"# Tam: rong={fmt_num(W_used)} cao={fmt_num(H)} (mm, lam tron 0.5)"]
    for p in placements:
        inner_lines = [l.strip() for l in (p.get("innerText") or "").split("\n") if l.strip()]
        label = f"# {p['name']}" + (" (xoay 90 do)" if p["rotated"] else "")
        lines.append(label)
        if not inner_lines:
            lines.append(f"R {fmt_num(p['x'])} {fmt_num(p['y'])} {fmt_num(p['w'])} {fmt_num(p['h'])}")
            continue
        # RC neo tam: tam khung bao = goc trai-duoi + nua kich thuoc
        cx, cy = p["x"] + p["w"] / 2, p["y"] + p["h"] / 2
        lines.append(f"RC {fmt_num(cx)} {fmt_num(cy)} {fmt_num(p['w'])} {fmt_num(p['h'])}")
        for raw in inner_lines:
            if raw.startswith("#"):
                lines.append(raw)
                continue
            parts = raw.split()
            cmd = parts[0].upper()
            if cmd == "R" and len(parts) >= 5:
                # R: x,y = goc trai-duoi
                lx, ly, lw, lh = (float(v) for v in parts[1:5])
                if not p["rotated"]:
                    nx, ny, nw, nh = p["x"] + lx, p["y"] + ly, lw, lh
                else:
                    nx = p["x"] + (p["origH"] - ly - lh)
                    ny = p["y"] + lx
                    nw, nh = lh, lw
                lines.append(f"R {fmt_num(nx)} {fmt_num(ny)} {fmt_num(nw)} {fmt_num(nh)}")
            elif cmd == "RC" and len(parts) >= 5:
                # RC: x,y = tam -> phep xoay ap dung truc tiep len diem tam
                lcx, lcy, lw, lh = (float(v) for v in parts[1:5])
                if not p["rotated"]:
                    ncx, ncy, nw, nh = p["x"] + lcx, p["y"] + lcy, lw, lh
                else:
                    ncx = p["x"] + (p["origH"] - lcy)
                    ncy = p["y"] + lcx
                    nw, nh = lh, lw
                lines.append(f"RC {fmt_num(ncx)} {fmt_num(ncy)} {fmt_num(nw)} {fmt_num(nh)}")
            elif cmd == "C" and len(parts) >= 4:
                lx, ly, lr = (float(v) for v in parts[1:4])
                if not p["rotated"]:
                    nx, ny = p["x"] + lx, p["y"] + ly
                else:
                    # Xoay quanh goc trai-duoi cua manh (origW x origH),
                    # ban kinh khong doi vi phep xoay bao toan khoang cach.
                    nx = p["x"] + (p["origH"] - ly)
                    ny = p["y"] + lx
                lines.append(f"C {fmt_num(nx)} {fmt_num(ny)} {fmt_num(lr)}")
            else:
                lines.append(f'# CANH BAO: lenh "{cmd}" chua duoc tu dong xoay/dich chuyen - kiem tra tay')
                lines.append(raw)
    return "\n".join(lines)



def _aabb_overlap(a, b, eps=1e-9):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax + aw > bx + eps and bx + bw > ax + eps
            and ay + ah > by + eps and by + bh > ay + eps)


def heuristic_pack(instances, H):
    """Bottom-left strip packer used when CP-SAT finds no solution in time."""
    ready = []
    infeasible = []
    for inst in instances:
        w, h = float(inst["w"]), float(inst["h"])
        orients = [(w, h, False)]
        if inst.get("rotate") and abs(w - h) > 1e-12:
            orients.append((h, w, True))
        orients = [o for o in orients if o[1] <= H + 1e-9]
        if not orients:
            infeasible.append(inst)
            continue
        ready.append((inst, orients))
    ready.sort(key=lambda item: -max(max(o[0], o[1]) for o in item[1]))

    placed = []
    placements = []
    for inst, orients in ready:
        best = None
        cands = [(0.0, 0.0)]
        for px, py, pw, ph in placed:
            cands.append((px + pw, py))
            cands.append((px, py + ph))
        seen = set()
        uniq = []
        for x, y in cands:
            key = (round(x, 6), round(y, 6))
            if key not in seen and x >= -1e-9 and y >= -1e-9:
                seen.add(key)
                uniq.append((x, y))
        for x, y in uniq:
            for w, h, rot in orients:
                if y + h > H + 1e-9:
                    continue
                box = (x, y, w, h)
                if any(_aabb_overlap(box, p) for p in placed):
                    continue
                score = (x + w, x, y)
                if best is None or score < best[0]:
                    best = (score, x, y, w, h, rot)
        if best is None:
            x = max((p[0] + p[2] for p in placed), default=0.0)
            w, h, rot = min(orients, key=lambda o: (o[0], -o[1]))
            if h > H + 1e-9:
                infeasible.append(inst)
                continue
            best = ((x + w, x, 0.0), x, 0.0, w, h, rot)
        _, x, y, w, h, rot = best
        placed.append((x, y, w, h))
        placements.append({
            "id": inst["id"], "name": inst["name"],
            "x": x, "y": y, "w": w, "h": h,
            "rotated": rot, "origW": inst["w"], "origH": inst["h"],
            "innerText": inst.get("innerText", ""),
        })
    W_used = max((p[0] + p[2] for p in placed), default=0.0)
    return {
        "placements": placements,
        "infeasible": infeasible,
        "status": "HEURISTIC",
        "W_used": W_used,
    }


def nest_dsl(dsl, height=None, allow_rotate=True, time_limit=15.0):
    """Rearrange top-level ADD blocks to minimize sheet width for a given H."""
    t0 = time.perf_counter()
    lines = dsl.splitlines()
    parsed = parse_blocks(dsl)
    if parsed.stray:
        nums = ", ".join(str(n) for n, _ in parsed.stray)
        detail = "\n".join(f"  line {n}: {txt.rstrip()}" for n, txt in parsed.stray)
        raise ValueError(
            f"Shape commands outside a top-level ADD (lines {nums}):\n{detail}"
        )
    if not parsed.blocks:
        raise ValueError("No top-level ADD ... END blocks found.")

    prepared = []
    for i, block in enumerate(parsed.blocks):
        chunk = lines[block.start:block.end + 1]
        segs0 = local_segments_from_lines(chunk)
        box0 = bbox_from_segments(segs0)
        if not box0 or box0["w"] <= 1e-12 or box0["h"] <= 1e-12:
            name = block.label or f"#{i + 1}"
            raise ValueError(
                f"Block '{name}' (lines {block.start + 1}-{block.end + 1}) "
                "has no drawable shapes."
            )
        rot_chunk = apply_rotate90_to_block_lines(lines, block)
        box90 = bbox_from_segments(local_segments_from_lines(rot_chunk))
        prepared.append({"block": block, "box": box0, "box90": box90})

    if height is None:
        if allow_rotate:
            height = max(min(p["box"]["w"], p["box"]["h"]) for p in prepared)
        else:
            height = max(p["box"]["h"] for p in prepared)
    height = float(height)
    if height <= 0:
        raise ValueError("Sheet height H must be greater than 0.")

    instances = []
    for i, p in enumerate(prepared):
        instances.append({
            "id": i,
            "name": p["block"].label or f"block-{i + 1}",
            "w": p["box"]["w"],
            "h": p["box"]["h"],
            "rotate": bool(allow_rotate),
        })

    pack = solve_packing(instances, height, time_limit=time_limit, scale=100)
    used_heuristic = False
    if not pack["placements"]:
        pack = heuristic_pack(instances, height)
        used_heuristic = True

    by_id = {pl["id"]: pl for pl in pack["placements"]}
    out_lines = list(lines)
    for i in range(len(prepared) - 1, -1, -1):
        pl = by_id.get(i)
        if pl is None:
            continue
        block = prepared[i]["block"]
        chunk = lines[block.start:block.end + 1]
        if pl["rotated"]:
            chunk = apply_rotate90_to_block_lines(lines, block)
        segs = local_segments_from_lines(chunk)
        box = bbox_from_segments(segs)
        new_x = pl["x"] - box["minx"]
        new_y = pl["y"] - box["miny"]
        chunk[0] = rewrite_add_line(chunk[0], new_x, new_y)
        out_lines[block.start:block.end + 1] = chunk

    new_dsl = "\n".join(out_lines)
    if dsl.endswith("\n") and not new_dsl.endswith("\n"):
        new_dsl += "\n"

    elapsed = time.perf_counter() - t0
    return {
        "dsl": new_dsl,
        "H": height,
        "W": pack["W_used"],
        "status": pack["status"],
        "heuristic": used_heuristic,
        "placements": pack["placements"],
        "infeasible": pack["infeasible"],
        "n_blocks": len(prepared),
        "elapsed": elapsed,
    }


