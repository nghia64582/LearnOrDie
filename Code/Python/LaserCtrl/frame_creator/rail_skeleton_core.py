"""
Rail skeleton solver.

Input: a list of centerline rectangles (x, y, w, h) -- the MIDLINE of a
10mm-wide rail frame (already shrunk 5mm on each side from the outer
design size, per convention).

Output: the set of final rail segments to cut, each adjusted at its ends
according to the joint-type rule confirmed with the user:

  At every node where a horizontal centerline and a vertical centerline
  meet, look at whether each axis "passes through" (qua) the node
  (i.e. the node is an interior point of a merged run on that axis) or
  "stops" there (the node is an endpoint of the run):

    (H_qua, V_qua) -> (H_end_adjustment, V_end_adjustment)
    (False, False) -> (+5, -5)   corner / L
    (True,  False) -> ( 0,  -5)  T  (vertical stub retreats half-width)
    (True,  True)  -> ( 0,  -5)  +  (both cross, both retreat half-width)
    (False, True)  -> (+5,  -5)  T-rotated (horizontal stub butts into vertical)

  The adjustment is added to that end's coordinate, extending the segment
  outward (+) or shrinking it inward (-), along its own axis, away from
  the segment body.

Free/dangling ends (no perpendicular member crossing there) are left
un-adjusted and reported separately -- bracing for those is not handled
yet (deferred, per user).
"""

RULE = {
    (False, False): (5, -5),
    (True, False): (0, -5),
    (True, True): (0, -5),
    (False, True): (5, -5),
}

NODE_LABEL = {
    (False, False): "L",
    (True, False): "T",
    (True, True): "+",
    (False, True): "T-rot",
}

NODE_COLOR = {
    "L": "#4a86e8",
    "T": "#6aa84f",
    "+": "#cc0000",
    "T-rot": "#e69138",
}


def _merge_intervals(intervals):
    """intervals: list of (a, b) with a<=b. Merge overlapping/touching."""
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [list(intervals[0])]
    for a, b in intervals[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [tuple(m) for m in merged]


def build_skeleton(rects):
    """rects: list of (x, y, w, h). Returns dict with merged horizontal /
    vertical segments, nodes, and final adjusted sub-segments."""

    h_raw = {}  # y -> list of (x0, x1)
    v_raw = {}  # x -> list of (y0, y1)

    for (x, y, w, h) in rects:
        h_raw.setdefault(y, []).append((x, x + w))
        h_raw.setdefault(y + h, []).append((x, x + w))
        v_raw.setdefault(x, []).append((y, y + h))
        v_raw.setdefault(x + w, []).append((y, y + h))

    h_segs = []  # {"y":.., "x0":.., "x1":..}
    for y, ivals in h_raw.items():
        for (x0, x1) in _merge_intervals(ivals):
            if x1 > x0:
                h_segs.append({"y": y, "x0": x0, "x1": x1})

    v_segs = []
    for x, ivals in v_raw.items():
        for (y0, y1) in _merge_intervals(ivals):
            if y1 > y0:
                v_segs.append({"x": x, "y0": y0, "y1": y1})

    # find nodes: (x0,y0) where an h_seg and v_seg overlap
    nodes = {}  # (x,y) -> {"h_qua":bool, "v_qua":bool}
    for hs in h_segs:
        for vs in v_segs:
            x0, y0 = vs["x"], hs["y"]
            if hs["x0"] <= x0 <= hs["x1"] and vs["y0"] <= y0 <= vs["y1"]:
                h_qua = hs["x0"] < x0 < hs["x1"]
                v_qua = vs["y0"] < y0 < vs["y1"]
                nodes[(x0, y0)] = {"h_qua": h_qua, "v_qua": v_qua}

    # split each h_seg by node x-coords on its y, each v_seg by node y-coords on its x
    final_segments = []  # {"orient","x0","y0","x1","y1","length"}
    free_ends = []

    for hs in h_segs:
        xs = sorted({x for (x, y) in nodes if y == hs["y"] and hs["x0"] <= x <= hs["x1"]})
        if hs["x0"] not in xs:
            xs = [hs["x0"]] + xs
        if hs["x1"] not in xs:
            xs = xs + [hs["x1"]]
        xs = sorted(set(xs))
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            # adjust xa (left end)
            node = nodes.get((xa, hs["y"]))
            if node:
                xa_adj = xa - RULE[(node["h_qua"], node["v_qua"])][0]
            else:
                xa_adj = xa
                free_ends.append((xa, hs["y"]))
            node2 = nodes.get((xb, hs["y"]))
            if node2:
                xb_adj = xb + RULE[(node2["h_qua"], node2["v_qua"])][0]
            else:
                xb_adj = xb
                free_ends.append((xb, hs["y"]))
            final_segments.append({
                "orient": "H", "y": hs["y"], "x0": xa_adj, "x1": xb_adj,
                "length": xb_adj - xa_adj,
                "node0": (xa, hs["y"]), "node1": (xb, hs["y"]),
            })

    for vs in v_segs:
        ys = sorted({y for (x, y) in nodes if x == vs["x"] and vs["y0"] <= y <= vs["y1"]})
        if vs["y0"] not in ys:
            ys = [vs["y0"]] + ys
        if vs["y1"] not in ys:
            ys = ys + [vs["y1"]]
        ys = sorted(set(ys))
        for i in range(len(ys) - 1):
            ya, yb = ys[i], ys[i + 1]
            node = nodes.get((vs["x"], ya))
            if node:
                ya_adj = ya - RULE[(node["h_qua"], node["v_qua"])][1]
            else:
                ya_adj = ya
                free_ends.append((vs["x"], ya))
            node2 = nodes.get((vs["x"], yb))
            if node2:
                yb_adj = yb + RULE[(node2["h_qua"], node2["v_qua"])][1]
            else:
                yb_adj = yb
                free_ends.append((vs["x"], yb))
            final_segments.append({
                "orient": "V", "x": vs["x"], "y0": ya_adj, "y1": yb_adj,
                "length": yb_adj - ya_adj,
                "node0": (vs["x"], ya), "node1": (vs["x"], yb),
            })

    node_list = [{"x": x, "y": y, "h_qua": v["h_qua"], "v_qua": v["v_qua"],
                  "label": NODE_LABEL[(v["h_qua"], v["v_qua"])]}
                 for (x, y), v in nodes.items()]

    return {
        "h_segs": h_segs,
        "v_segs": v_segs,
        "nodes": node_list,
        "segments": final_segments,
        "free_ends": list(set(free_ends)),
    }


def cut_list(skeleton):
    return sorted((round(s["length"], 4) for s in skeleton["segments"]), reverse=True)