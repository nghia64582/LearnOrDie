"""Planar popsicle-stick truss designer (core, no Tk).

Model
-----
* A rectangular frame W x H is split into an n x m grid of panels.
  Nodes sit on the grid; bars join neighbouring nodes (chords,
  verticals, interior horizontals, diagonals) according to the truss
  type: Pratt, Howe, Warren (alternating diagonals + verticals),
  X (both diagonals per panel, crossing on different layers) and K.
* Collinear bars that meet end to end form a *chain* (a straight line
  of nodes). A chain is cut into *pieces*: each piece covers one or
  more consecutive bars, so it carries a hole at every node it
  crosses. Long chains are spliced at nodes; the two pieces overlap
  there (staggered layers) and share the node's pin.
* Lap joints: sticks lie flat and overlap at the node. Piece length =
  node span + 2e with e = cap_radius(W) = W/2 + 1, so the rounded cap
  is concentric with the pin hole. Usable stick length is L - W, so
  the longest node span on one stick is L - W - 2e (92 mm on 114x10).
* Layers: two pieces whose bodies overlap (they share a node, cross,
  or pass closer than the stick width) must lie in different layers.
  Layers are assigned by graph colouring. A node whose stack skips a
  layer needs a spacer disc (cut as a tiny piece).
* Joints: each node is glue or pin (3 mm bamboo skewer). The load
  level sets the default (Light: glue, Medium: corners + splices
  pinned, Heavy: all pinned); the user can toggle single nodes.

Optimisation enumerates type x panels x rows, keeps rigid layouts
(rigidity matrix rank = 2N - 3) whose bars all fit one stick and whose
layer count is within the limit, splits each chain with a small DP, and
scores layouts with sticks first (via the Small parts packer), then
nodes, pieces, pins, extra layers and spacers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from engraver_ctrl.cut_handler import pack_pieces
from engraver_ctrl.cut_plan_builder import Part, cap_radius, usable_length

TRUSS_TYPES = ("Pratt", "Howe", "Warren", "X", "K")
LOAD_LEVELS = ("Light", "Medium", "Heavy")
KIND_NAMES = {
    "T": "Top chord",
    "B": "Bottom chord",
    "H": "Inner chord",
    "V": "Vertical",
    "D": "Diagonal",
    "S": "Spacer",
}
_TOL = 1e-6

# Score weights: sticks dominate, then joints.
W_STICK = 100.0
W_NODE = 10.0
W_PIECE = 3.0
W_PIN = 2.0
W_LAYER = 15.0
W_SPACER = 1.0


@dataclass
class TrussParams:
    width: float = 300.0          # frame W (mm), along X
    height: float = 60.0          # frame H (mm), along Y
    stock_length: float = 114.0   # stick length incl. factory caps
    stick_width: float = 10.0
    thickness: float = 2.0        # stick thickness, for stack height
    hole_radius: float = 1.5
    truss_type: str = "Auto"      # "Auto" or one of TRUSS_TYPES
    panels: Optional[int] = None  # n along X; None = auto
    rows: Optional[int] = None    # m along Y; None = auto
    max_layers: int = 3
    load: str = "Medium"
    holes_every_node: bool = True
    lap_splice: bool = True       # allow mid-panel lap splices (2 pins)
    min_angle: float = 20.0       # diagonal angle limits (deg)
    max_angle: float = 70.0
    max_panels: int = 16
    max_rows: int = 4

    @property
    def end_offset(self) -> float:
        """e: hole centre to piece end = cap radius (W/2 + 1)."""
        return cap_radius(self.stick_width)

    @property
    def usable(self) -> float:
        return usable_length(self.stock_length, self.stick_width)

    @property
    def max_span(self) -> float:
        """Longest node-to-node span one stick can carry."""
        return self.usable - 2.0 * self.end_offset

    @property
    def lap_gap(self) -> float:
        """Distance between the two pins of a lap splice."""
        return 2.0 * self.end_offset

    @property
    def min_span(self) -> float:
        """Shortest node spacing: two caps must not overlap the next hole."""
        return 2.0 * self.end_offset


@dataclass
class Piece:
    kind: str                     # T, B, H, V, D or S
    nodes: List[int]              # node ids along the piece (start -> end)
    p0: Tuple[float, float]       # first node position
    p1: Tuple[float, float]       # last node position
    span: float                   # node-to-node length
    length: float                 # cut length = span + 2e
    node_offsets: List[float]     # hole position of each node from piece start
    label: str = ""
    layer: int = 0
    holes: List[float] = field(default_factory=list)
    spacer_node: int = -1         # for spacers: the node it sits on

    def signature(self) -> Tuple:
        return (round(self.length, 2), tuple(round(h, 2) for h in self.holes))


@dataclass
class TrussDesign:
    params: TrussParams
    truss_type: str
    panels: int
    rows: int
    nodes: List[Tuple[float, float]]
    bars: List[Tuple[int, int]]
    pieces: List[Piece]                       # structural pieces
    layers: int = 0
    pins: List[bool] = field(default_factory=list)
    pin_override: Dict[int, bool] = field(default_factory=dict)
    spacers: List[Piece] = field(default_factory=list)
    node_pieces: Dict[int, List[int]] = field(default_factory=dict)
    sticks: int = 0
    waste: float = 0.0
    score: float = 0.0
    exact: bool = False
    relaxed_layers: int = 0   # >0: layer limit had to be raised to this
    aux: List[bool] = field(default_factory=list)  # lap-splice pin points

    # ---- derived info -------------------------------------------------
    @property
    def all_pieces(self) -> List[Piece]:
        return list(self.pieces) + list(self.spacers)

    @property
    def thickness(self) -> float:
        return self.layers * self.params.thickness

    @property
    def pin_count(self) -> int:
        return sum(1 for p in self.pins if p)

    def node_stack(self, node: int) -> int:
        """Number of pieces stacked at a node."""
        return len(self.node_pieces.get(node, []))

    def node_layers(self, node: int) -> List[int]:
        return sorted(self.pieces[i].layer for i in self.node_pieces.get(node, []))

    def skewer_length(self, node: int) -> float:
        """Stack height at a pinned node (spacers included) + 2 mm."""
        lay = self.node_layers(node)
        if not lay:
            return 0.0
        return (lay[-1] - lay[0] + 1) * self.params.thickness + 2.0

    def stack_histogram(self) -> Dict[int, int]:
        hist: Dict[int, int] = {}
        for n in range(len(self.nodes)):
            k = self.node_stack(n)
            hist[k] = hist.get(k, 0) + 1
        return dict(sorted(hist.items()))

    @property
    def joint_count(self) -> int:
        return len(self.nodes)

    @property
    def lap_splices(self) -> int:
        return sum(1 for a in self.aux if a) // 2

    def spacer_count(self) -> int:
        return len(self.spacers)

    def summary(self) -> str:
        return (
            f"{self.truss_type} {self.panels}x{self.rows}: "
            f"{self.sticks} sticks, {len(self.all_pieces)} pieces, "
            f"{len(self.nodes)} nodes, {self.pin_count} pins, "
            f"{self.layers} layers"
        )


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------

def _diag_dir(truss_type: str, i: int, j: int, n: int, m: int) -> str:
    """Diagonal direction in cell (i, j): '\\' or '/'.

    '\\' joins top-left to bottom-right, '/' bottom-left to top-right.
    """
    left = (i + 0.5) <= n / 2.0
    if truss_type == "Pratt":
        return "\\" if left else "/"
    if truss_type == "Howe":
        return "/" if left else "\\"
    if truss_type == "Warren":
        return "/" if (i + j) % 2 == 0 else "\\"
    if truss_type == "K":
        upper = (j % 2) == 1
        if left:
            return "/" if upper else "\\"
        return "\\" if upper else "/"
    raise ValueError(f"No single diagonal for {truss_type}")


def build_topology(
    truss_type: str, n: int, m: int, width: float, height: float,
) -> Tuple[List[Tuple[float, float]], List[Tuple[int, int]]]:
    """Nodes and bars for a truss type with n panels x m rows.

    Pratt / Howe / X / K use an (n+1) x (m+1) node grid with verticals
    on every column. Warren is the classic form without inner
    verticals: on each horizontal line the inner nodes alternate
    between whole and half panel positions, so every inner node joins
    one chord and two diagonals; only the two ends get verticals.
    """
    if truss_type not in TRUSS_TYPES:
        raise ValueError(f"Unknown truss type {truss_type!r}")
    if n < 1 or m < 1:
        raise ValueError("Panels and rows must be >= 1")
    if truss_type == "K" and m % 2:
        raise ValueError("K truss needs an even number of rows")
    if truss_type == "Warren":
        return _warren_topology(n, m, width, height)
    sx = width / n
    sy = height / m

    def nid(i: int, j: int) -> int:
        return j * (n + 1) + i

    nodes = [(i * sx, j * sy) for j in range(m + 1) for i in range(n + 1)]
    bars: List[Tuple[int, int]] = []
    # Horizontal lines (K skips the mid line of each row pair).
    for j in range(m + 1):
        if truss_type == "K" and j % 2 == 1:
            continue
        for i in range(n):
            bars.append((nid(i, j), nid(i + 1, j)))
    # Verticals on every column.
    for i in range(n + 1):
        for j in range(m):
            bars.append((nid(i, j), nid(i, j + 1)))
    # Diagonals.
    for j in range(m):
        for i in range(n):
            if truss_type == "X":
                bars.append((nid(i, j), nid(i + 1, j + 1)))
                bars.append((nid(i, j + 1), nid(i + 1, j)))
                continue
            d = _diag_dir(truss_type, i, j, n, m)
            if d == "/":
                bars.append((nid(i, j), nid(i + 1, j + 1)))
            else:
                bars.append((nid(i, j + 1), nid(i + 1, j)))
    return _merge_straight_nodes(nodes, bars)


def _merge_straight_nodes(nodes, bars):
    """Drop nodes that only join two collinear bars (e.g. the centre
    mid-height node of a K truss): the two bars become one."""
    nodes = list(nodes)
    bars = [tuple(b) for b in bars]
    changed = True
    while changed:
        changed = False
        deg: Dict[int, List[int]] = {}
        for k, (a, b) in enumerate(bars):
            deg.setdefault(a, []).append(k)
            deg.setdefault(b, []).append(k)
        for v, ks in deg.items():
            if len(ks) != 2:
                continue
            (a1, b1), (a2, b2) = bars[ks[0]], bars[ks[1]]
            o1 = b1 if a1 == v else a1
            o2 = b2 if a2 == v else a2
            u1 = _unit(nodes, v, o1)
            u2 = _unit(nodes, v, o2)
            if abs(u1[0] + u2[0]) < 1e-9 and abs(u1[1] + u2[1]) < 1e-9:
                bars = [b for k, b in enumerate(bars) if k not in ks] + [(o1, o2)]
                changed = True
                break
    used = sorted({v for b in bars for v in b})
    remap = {v: i for i, v in enumerate(used)}
    return [nodes[v] for v in used], [(remap[a], remap[b]) for a, b in bars]


def _warren_topology(n: int, m: int, width: float, height: float):
    sx = width / n
    sy = height / m
    nodes: List[Tuple[float, float]] = []
    lines: List[List[int]] = []
    for j in range(m + 1):
        if j % 2 == 0:
            xs = [i * sx for i in range(n + 1)]
        else:
            xs = [0.0] + [(i + 0.5) * sx for i in range(n)] + [width]
        ids = []
        for x in xs:
            ids.append(len(nodes))
            nodes.append((x, j * sy))
        lines.append(ids)
    bars: List[Tuple[int, int]] = []
    for ids in lines:
        for a, b in zip(ids, ids[1:]):
            bars.append((a, b))
    for j in range(m):
        lo, hi = lines[j], lines[j + 1]
        bars.append((lo[0], hi[0]))
        bars.append((lo[-1], hi[-1]))
        # Zigzag through the inner points of both lines, by x.
        seq = sorted(
            [(nodes[v][0], v) for v in lo[1:-1]] + [(nodes[v][0], v) for v in hi[1:-1]]
        )
        if j % 2 == 0:
            start, end = lo[0], lo[-1]
        else:
            start, end = hi[0], hi[-1]
        chain = [start] + [v for _, v in seq] + [end]
        for a, b in zip(chain, chain[1:]):
            bars.append((a, b))
    return nodes, bars


def rigidity_rank(nodes: Sequence[Tuple[float, float]],
                  bars: Sequence[Tuple[int, int]]) -> int:
    """Rank of the 2D rigidity matrix (bars x 2N)."""
    cols = 2 * len(nodes)
    rows = []
    for a, b in bars:
        ax, ay = nodes[a]
        bx, by = nodes[b]
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy)
        if ln < _TOL:
            continue
        ux, uy = dx / ln, dy / ln
        row = {2 * a: -ux, 2 * a + 1: -uy, 2 * b: ux, 2 * b + 1: uy}
        rows.append(row)
    try:
        import numpy as np  # fast path
        mat = np.zeros((len(rows), cols))
        for r, row in enumerate(rows):
            for c, v in row.items():
                mat[r, c] = v
        if not rows:
            return 0
        return int(np.linalg.matrix_rank(mat, tol=1e-9))
    except ImportError:
        return _sparse_rank(rows)


def _sparse_rank(rows: List[Dict[int, float]]) -> int:
    """Gaussian elimination on sparse dict rows (fallback without numpy)."""
    pivots: Dict[int, Dict[int, float]] = {}
    rank = 0
    for row in rows:
        r = {k: v for k, v in row.items() if abs(v) > 1e-12}
        while r:
            col = min(r)
            if col in pivots:
                prow = pivots[col]
                f = r[col] / prow[col]
                for k, v in prow.items():
                    nv = r.get(k, 0.0) - f * v
                    if abs(nv) > 1e-9:
                        r[k] = nv
                    else:
                        r.pop(k, None)
            else:
                pivots[col] = r
                rank += 1
                break
    return rank


def is_rigid(nodes, bars) -> bool:
    n = len(nodes)
    if n < 2:
        return True
    return rigidity_rank(nodes, bars) == 2 * n - 3


# ---------------------------------------------------------------------------
# Chains and splitting
# ---------------------------------------------------------------------------

def _unit(nodes, a, b) -> Tuple[float, float]:
    ax, ay = nodes[a]
    bx, by = nodes[b]
    ln = math.hypot(bx - ax, by - ay)
    return ((bx - ax) / ln, (by - ay) / ln)


def find_chains(nodes, bars) -> List[List[int]]:
    """Group collinear bars meeting end to end into ordered node chains."""
    adj: Dict[int, List[int]] = {}
    for k, (a, b) in enumerate(bars):
        adj.setdefault(a, []).append(k)
        adj.setdefault(b, []).append(k)
    used = [False] * len(bars)

    def continuation(node: int, came_bar: int, direction) -> Optional[Tuple[int, int]]:
        for k in adj.get(node, []):
            if k == came_bar or used[k]:
                continue
            a, b = bars[k]
            other = b if a == node else a
            u = _unit(nodes, node, other)
            if abs(u[0] - direction[0]) < 1e-6 and abs(u[1] - direction[1]) < 1e-6:
                return k, other
        return None

    chains: List[List[int]] = []
    for k0, (a0, b0) in enumerate(bars):
        if used[k0]:
            continue
        # Orient each chain left->right, or bottom->top for verticals.
        (ax, ay), (bx, by) = nodes[a0], nodes[b0]
        if (bx, by) < (ax, ay) and abs(bx - ax) > _TOL or (
            abs(bx - ax) <= _TOL and by < ay
        ):
            a0, b0 = b0, a0
        used[k0] = True
        chain = [a0, b0]
        fwd = _unit(nodes, a0, b0)
        k, node = k0, b0
        while True:
            nxt = continuation(node, k, fwd)
            if nxt is None:
                break
            k, node = nxt
            used[k] = True
            chain.append(node)
        back = (-fwd[0], -fwd[1])
        k, node = k0, a0
        while True:
            nxt = continuation(node, k, back)
            if nxt is None:
                break
            k, node = nxt
            used[k] = True
            chain.insert(0, node)
        chains.append(chain)
    return chains


def stick_fraction(length: float, usable: float) -> float:
    """Fraction of a stick a piece costs when packed alone by length."""
    per = math.floor((usable + _TOL) / length) if length > _TOL else 0
    return 1.0 / per if per >= 1 else float("inf")


@dataclass
class ChainCut:
    """One piece of a chain: hole positions along the chain line."""
    holes: List[float]                 # every hole (nodes + lap pins), in order
    node_idx: List[Optional[int]]      # chain node index per hole, None = lap pin
    lap_start: Optional[int] = None    # panel of the lap splice at the start
    lap_end: Optional[int] = None      # panel of the lap splice at the end


def lap_centres(positions: Sequence[float], panel: int,
                params: TrussParams) -> List[float]:
    """Allowed lap-splice centres in a panel.

    The panel must leave both pins >= 2e from its nodes; the middle is
    always offered. Off-centre positions keep the overlapping piece's
    cap at least one stick width clear of the node (2e + W from it),
    so webs at that node do not need an extra layer.
    """
    e = params.end_offset
    g = params.lap_gap
    a, b = positions[panel], positions[panel + 1]
    if (b - a) < g + 4.0 * e - _TOL:
        return []
    mid = 0.5 * (a + b)
    clear = 2.0 * e + params.stick_width
    lo = a + clear + g / 2.0
    hi = b - clear - g / 2.0
    cands = [mid]
    if hi >= lo - _TOL:
        cands = [lo, mid, hi]
    out = []
    for c in cands:
        if not out or abs(c - out[-1]) > 0.5:
            out.append(c)
    return out


def lap_pins(centre: float, params: TrussParams) -> Tuple[float, float]:
    g = params.lap_gap
    return centre - g / 2.0, centre + g / 2.0


def lap_fits(positions: Sequence[float], panel: int, params: TrussParams) -> bool:
    return bool(lap_centres(positions, panel, params))


def split_chain(
    positions: Sequence[float],
    params: TrussParams,
    splice_layers: Optional[Sequence[int]] = None,
) -> Optional[List[ChainCut]]:
    """Split a chain (node distances from its start) into pieces.

    Pieces meet either at a node (node splice: both pieces share the
    node pin, adding one layer to that node's stack) or, when
    params.lap_splice is on, by a lap splice in the middle of a panel:
    the two pieces overlap there and are joined by two extra pins
    lap_gap apart, away from any web. Every piece must fit one stick
    (holes span <= max_span). Cost: estimated stick use first, then
    splice cost; node splices that would exceed max_layers are
    heavily penalised. Returns None if no split fits.
    """
    k = len(positions)
    e = params.end_offset
    usable = params.usable
    max_span = params.max_span
    INF = float("inf")
    # Boundaries in chain order: ("n", i, 0) node i, ("l", i, c) lap
    # centred at c in panel i.
    bounds: List[Tuple[str, int, float]] = []
    for i in range(k):
        bounds.append(("n", i, positions[i]))
        if i + 1 < k and params.lap_splice:
            for c in lap_centres(positions, i, params):
                bounds.append(("l", i, c))

    def start_holes(b):
        kind, i, c = b
        if kind == "n":
            return [positions[i]], [i], i  # holes, node idx, next node
        p1, p2 = lap_pins(c, params)
        return [p1, p2], [None, None], i + 1

    def end_holes(b):
        kind, j, c = b
        if kind == "n":
            return j, [], []                 # last node incl., extra holes
        p1, p2 = lap_pins(c, params)
        return j, [p1, p2], [None, None]

    nb = len(bounds)
    best = [INF] * nb
    prev = [-1] * nb
    best[0] = 0.0
    for b2 in range(1, nb):
        for b1 in range(b2 - 1, -1, -1):
            if best[b1] == INF:
                continue
            sh, sidx, first_node = start_holes(bounds[b1])
            last_node, eh, eidx = end_holes(bounds[b2])
            if bounds[b2][2] <= bounds[b1][2] + _TOL:
                continue
            if bounds[b1][0] == "l" and bounds[b2][0] == "l" and last_node < first_node:
                continue
            node_range = list(range(first_node, last_node + 1))
            if bounds[b1][0] == "n":
                node_range = list(range(bounds[b1][1] + 1, last_node + 1))
            holes = sh + [positions[t] for t in node_range] + eh
            if len(holes) < 2:
                continue
            span = holes[-1] - holes[0]
            if span > max_span + _TOL:
                continue
            cost = best[b1] + stick_fraction(span + 2 * e, usable) + 0.02
            if b1 > 0:
                kind, i, _c = bounds[b1]
                if kind == "n":
                    stack = splice_layers[i] if splice_layers else 2
                    cost += 5.0 if stack > params.max_layers else 0.05 * stack
                else:
                    cost += 0.15
            if cost < best[b2] - 1e-12:
                best[b2] = cost
                prev[b2] = b1
    last = nb - 1
    if bounds[last][:2] != ("n", k - 1) or best[last] == INF:
        return None
    out: List[ChainCut] = []
    b2 = last
    while b2 > 0:
        b1 = prev[b2]
        sh, sidx, first_node = start_holes(bounds[b1])
        last_node, eh, eidx = end_holes(bounds[b2])
        if bounds[b1][0] == "n":
            node_range = list(range(bounds[b1][1] + 1, last_node + 1))
        else:
            node_range = list(range(first_node, last_node + 1))
        out.append(ChainCut(
            holes=sh + [positions[t] for t in node_range] + eh,
            node_idx=sidx + node_range + eidx,
            lap_start=bounds[b1][1] if bounds[b1][0] == "l" else None,
            lap_end=bounds[b2][1] if bounds[b2][0] == "l" else None,
        ))
        b2 = b1
    out.reverse()
    return out


def _chain_kind(nodes, chain, height) -> str:
    (x0, y0), (x1, y1) = nodes[chain[0]], nodes[chain[-1]]
    if abs(y1 - y0) < _TOL:
        if abs(y0) < _TOL:
            return "B"
        if abs(y0 - height) < _TOL:
            return "T"
        return "H"
    if abs(x1 - x0) < _TOL:
        return "V"
    return "D"


# ---------------------------------------------------------------------------
# Layers
# ---------------------------------------------------------------------------

def _seg_dist(p, q, r, s) -> float:
    """Minimum distance between segments pq and rs."""
    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1]

    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1])

    def point_seg(pt, a, b):
        ab = sub(b, a)
        ln2 = dot(ab, ab)
        if ln2 < 1e-18:
            return math.hypot(*sub(pt, a))
        t = max(0.0, min(1.0, dot(sub(pt, a), ab) / ln2))
        proj = (a[0] + t * ab[0], a[1] + t * ab[1])
        return math.hypot(*sub(pt, proj))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1, d2 = cross(r, s, p), cross(r, s, q)
    d3, d4 = cross(p, q, r), cross(p, q, s)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and \
            abs(d1) > 1e-12 and abs(d2) > 1e-12 and abs(d3) > 1e-12 and abs(d4) > 1e-12:
        return 0.0
    return min(point_seg(p, r, s), point_seg(q, r, s),
               point_seg(r, p, q), point_seg(s, p, q))


def _extended(piece: Piece, e: float):
    (x0, y0), (x1, y1) = piece.p0, piece.p1
    ln = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
    return (x0 - ux * e, y0 - uy * e), (x1 + ux * e, y1 + uy * e)


def conflict_graph(pieces: Sequence[Piece], params: TrussParams) -> List[set]:
    """Pieces whose bodies overlap (share a node, cross, or pass close)."""
    e = params.end_offset
    w = params.stick_width
    segs = [_extended(p, e) for p in pieces]
    adj = [set() for _ in pieces]
    for a in range(len(pieces)):
        for b in range(a + 1, len(pieces)):
            share = set(pieces[a].nodes) & set(pieces[b].nodes)
            if share or _seg_dist(*segs[a], *segs[b]) < w - 1e-6:
                adj[a].add(b)
                adj[b].add(a)
    return adj


def color_graph(adj: List[set], max_colors: int = 8,
                step_limit: int = 3000, lower: int = 1) -> List[int]:
    """Smallest colouring found: exact backtracking (DSatur order) per k
    starting at `lower`, falling back to greedy DSatur when the step
    budget runs out."""
    n = len(adj)
    if n == 0:
        return []
    greedy = _dsatur(adj)
    k_greedy = max(greedy) + 1
    lo = max(1, lower, 1 + int(any(adj)))
    for k in range(lo, min(k_greedy, max_colors + 1)):
        res = _backtrack(adj, k, step_limit)
        if res is not None:
            return res
    return greedy


def count_spacers(node_pieces: Dict[int, List[int]], colors: Sequence[int]) -> int:
    total = 0
    for idxs in node_pieces.values():
        if len(idxs) < 2:
            continue
        lay = {colors[i] for i in idxs}
        total += (max(lay) - min(lay) + 1) - len(lay)
    return total


def improve_layers(adj: List[set], node_pieces: Dict[int, List[int]],
                   colors: List[int]) -> List[int]:
    """Reorder layers and nudge pieces to cut spacer discs."""
    import itertools
    k = max(colors) + 1 if colors else 0
    best = list(colors)
    best_cost = count_spacers(node_pieces, best)
    if 1 < k <= 6 and best_cost:
        for perm in itertools.permutations(range(k)):
            cand = [perm[c] for c in colors]
            cost = count_spacers(node_pieces, cand)
            if cost < best_cost:
                best, best_cost = cand, cost
                if cost == 0:
                    break
    for _ in range(6):
        if best_cost == 0:
            break
        improved = False
        for v in range(len(best)):
            used = {best[u] for u in adj[v]}
            for c in range(k):
                if c == best[v] or c in used:
                    continue
                old = best[v]
                best[v] = c
                cost = count_spacers(node_pieces, best)
                if cost < best_cost:
                    best_cost = cost
                    improved = True
                    break
                best[v] = old
        if not improved:
            break
    return best


def _dsatur(adj: List[set]) -> List[int]:
    n = len(adj)
    colors = [-1] * n
    for _ in range(n):
        best, key = -1, None
        for v in range(n):
            if colors[v] >= 0:
                continue
            sat = len({colors[u] for u in adj[v] if colors[u] >= 0})
            k = (sat, len(adj[v]), -v)
            if key is None or k > key:
                best, key = v, k
        used = {colors[u] for u in adj[best] if colors[u] >= 0}
        c = 0
        while c in used:
            c += 1
        colors[best] = c
    return colors


def _backtrack(adj: List[set], k: int, step_limit: int = 3000) -> Optional[List[int]]:
    n = len(adj)
    order = sorted(range(n), key=lambda v: -len(adj[v]))
    colors = [-1] * n
    steps = [0]

    def pick() -> int:
        best, key = -1, None
        for v in order:
            if colors[v] >= 0:
                continue
            sat = len({colors[u] for u in adj[v] if colors[u] >= 0})
            kk = (sat, len(adj[v]))
            if key is None or kk > key:
                best, key = v, kk
        return best

    def rec(done: int) -> bool:
        if done == n:
            return True
        steps[0] += 1
        if steps[0] > step_limit:
            raise TimeoutError
        v = pick()
        used = {colors[u] for u in adj[v] if colors[u] >= 0}
        top = max(colors) + 1  # symmetry break: at most one new colour
        for c in range(min(k, top + 1)):
            if c in used:
                continue
            colors[v] = c
            if rec(done + 1):
                return True
            colors[v] = -1
        return False

    try:
        return colors if rec(0) else None
    except TimeoutError:
        return None


# ---------------------------------------------------------------------------
# Building one design
# ---------------------------------------------------------------------------

def _range_label(kind: str, numbers: Sequence[int]) -> str:
    nums = sorted(set(numbers))
    parts = []
    i = 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(f"{nums[i]}" if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return kind + "/".join(parts)


def build_design(
    params: TrussParams, truss_type: str, n: int, m: int,
    enforce_layers: bool = True,
) -> Optional[TrussDesign]:
    """Build one candidate, or None if it breaks a constraint."""
    W, H = float(params.width), float(params.height)
    if W <= _TOL or H <= _TOL:
        raise ValueError("Frame width and height must be positive")
    if params.max_span <= _TOL:
        raise ValueError("Stick too short for any member (L - W - 2e <= 0)")
    if truss_type == "K" and m % 2:
        return None
    nodes, bars = build_topology(truss_type, n, m, W, H)
    for a, b in bars:
        (ax, ay), (bx, by) = nodes[a], nodes[b]
        ln = math.hypot(bx - ax, by - ay)
        if ln > params.max_span + _TOL or ln < params.min_span - _TOL:
            return None
        dx, dy = abs(bx - ax), abs(by - ay)
        if dx > _TOL and dy > _TOL:
            ang = math.degrees(math.atan2(dy, dx))
            if not (params.min_angle - _TOL <= ang <= params.max_angle + _TOL):
                return None
    if not is_rigid(nodes, bars):
        return None

    chains = find_chains(nodes, bars)
    node_chains: Dict[int, set] = {}
    for ci, ch in enumerate(chains):
        for v in ch:
            node_chains.setdefault(v, set()).add(ci)

    e = params.end_offset
    nodes = list(nodes)
    aux = [False] * len(nodes)
    pieces: List[Piece] = []
    for ci, ch in enumerate(chains):
        p0 = nodes[ch[0]]
        p_end = nodes[ch[-1]]
        total = math.dist(p0, p_end)
        ux, uy = (p_end[0] - p0[0]) / total, (p_end[1] - p0[1]) / total
        pos = [math.dist(p0, nodes[v]) for v in ch]
        # Node splice at k: this chain's two pieces + every other chain there.
        splice = [1 + len(node_chains[v]) for v in ch]
        cuts = split_chain(pos, params, splice)
        if cuts is None:
            return None
        kind = _chain_kind(nodes, ch, H)
        lap_ids: Dict[Tuple[int, int], int] = {}
        for c in cuts:
            ids: List[int] = []
            lap_seen = 0
            for h, ni in zip(c.holes, c.node_idx):
                if ni is not None:
                    ids.append(ch[ni])
                    continue
                key = (round(h, 6), 0)
                if key not in lap_ids:
                    lap_ids[key] = len(nodes)
                    nodes.append((p0[0] + ux * h, p0[1] + uy * h))
                    aux.append(True)
                ids.append(lap_ids[key])
                lap_seen += 1
            first, last = c.holes[0], c.holes[-1]
            pieces.append(Piece(
                kind=kind,
                nodes=ids,
                p0=(p0[0] + ux * first, p0[1] + uy * first),
                p1=(p0[0] + ux * last, p0[1] + uy * last),
                span=last - first,
                length=last - first + 2 * e,
                node_offsets=[e + (h - first) for h in c.holes],
            ))

    # Stable labels by position: chords bottom-up then left-right.
    order = {"T": 0, "B": 1, "H": 2, "V": 3, "D": 4}
    counters: Dict[str, int] = {}
    for p in sorted(
        pieces,
        key=lambda p: (order[p.kind], round(min(p.p0[1], p.p1[1]), 6),
                       round(min(p.p0[0], p.p1[0]), 6), p.p0[1]),
    ):
        counters[p.kind] = counters.get(p.kind, 0) + 1
        p.label = f"{p.kind}{counters[p.kind]}"
    pieces.sort(key=lambda p: (order[p.kind], int(p.label[1:])))

    node_pieces: Dict[int, List[int]] = {v: [] for v in range(len(nodes))}
    for idx, p in enumerate(pieces):
        for v in p.nodes:
            node_pieces[v].append(idx)
    max_stack = max((len(v) for v in node_pieces.values()), default=0)
    if enforce_layers and max_stack > params.max_layers:
        return None
    adj = conflict_graph(pieces, params)
    colors = color_graph(adj, max_colors=max(params.max_layers, max_stack, 6),
                         lower=max_stack)
    colors = improve_layers(adj, node_pieces, colors)
    layers = (max(colors) + 1) if colors else 0
    if enforce_layers and layers > params.max_layers:
        return None
    for p, c in zip(pieces, colors):
        p.layer = c

    design = TrussDesign(
        params=params, truss_type=truss_type, panels=n, rows=m,
        nodes=nodes, bars=bars, pieces=pieces, layers=layers, aux=aux,
    )
    design.node_pieces = node_pieces
    apply_joints(design)
    pack_design(design, method="heuristic")
    return design


def default_pins(design: TrussDesign) -> List[bool]:
    """Pins by load level: Light none, Medium corners + splices, Heavy all."""
    load = design.params.load
    nn = len(design.nodes)
    if load == "Heavy":
        return [True] * nn
    if load == "Light":
        return [False] * nn  # glue everywhere (lap splices glued too)
    W, H = design.params.width, design.params.height
    pins = [False] * nn
    for v, is_aux in enumerate(design.aux):
        if is_aux:
            pins[v] = True  # lap splices carry their pins
    for v, (x, y) in enumerate(design.nodes):
        if v < len(design.aux) and design.aux[v]:
            continue
        if (abs(x) < _TOL or abs(x - W) < _TOL) and (abs(y) < _TOL or abs(y - H) < _TOL):
            pins[v] = True
    # Splice nodes: two pieces of the same line meet there.
    for v, idxs in design.node_pieces.items():
        ends = [i for i in idxs
                if v in (design.pieces[i].nodes[0], design.pieces[i].nodes[-1])]
        kinds_dirs = {}
        for i in ends:
            p = design.pieces[i]
            key = (p.kind, round(_unit_pts(p.p0, p.p1)[0], 6),
                   round(_unit_pts(p.p0, p.p1)[1], 6))
            kinds_dirs[key] = kinds_dirs.get(key, 0) + 1
        if any(c >= 2 for c in kinds_dirs.values()):
            pins[v] = True
    return pins


def _unit_pts(a, b):
    ln = math.dist(a, b)
    return ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)


def apply_joints(design: TrussDesign) -> None:
    """(Re)compute pins, holes and spacers from load level + overrides."""
    pins = default_pins(design)
    for v, val in design.pin_override.items():
        if 0 <= v < len(pins):
            pins[v] = bool(val)
    design.pins = pins
    every = design.params.holes_every_node
    for p in design.pieces:
        p.holes = [off for v, off in zip(p.nodes, p.node_offsets)
                   if every or pins[v]]
    # Spacer discs fill skipped layers in a node's stack.
    e = design.params.end_offset
    spacers: List[Piece] = []
    for v in range(len(design.nodes)):
        lay = design.node_layers(v)
        if len(lay) < 2:
            continue
        present = set(lay)
        for layer in range(lay[0], lay[-1] + 1):
            if layer in present:
                continue
            pos = design.nodes[v]
            spacers.append(Piece(
                kind="S", nodes=[v], p0=pos, p1=pos, span=0.0,
                length=2 * e, node_offsets=[e], layer=layer,
                holes=[e] if (every or pins[v]) else [],
                spacer_node=v,
            ))
    for i, s in enumerate(spacers, start=1):
        s.label = f"S{i}"
    design.spacers = spacers


def pack_design(design: TrussDesign, method: str = "heuristic") -> None:
    """Count sticks with the Small parts packer and update the score."""
    lengths = [p.length for p in design.all_pieces]
    bins, unplaced = pack_pieces(
        design.params.usable, lengths, method=method, time_limit=0.5,
    )
    if unplaced:
        raise ValueError("A truss piece is longer than the usable stick length")
    if method == "auto":
        # Keep the exact solver snappy; fall back to the heuristic.
        heur, _ = pack_pieces(design.params.usable, lengths, method="heuristic")
        if len(heur) < len(bins):
            bins = heur
    design.sticks = len(bins)
    design.waste = design.sticks * design.params.usable - sum(lengths)
    design.exact = method != "heuristic"
    design.score = score_design(design)


def score_design(design: TrussDesign) -> float:
    return (
        W_STICK * design.sticks
        + W_NODE * len(design.nodes)
        + W_PIECE * len(design.all_pieces)
        + W_PIN * design.pin_count
        + W_LAYER * max(0, design.layers - 2)
        + W_SPACER * len(design.spacers)
    )


def refresh(design: TrussDesign, method: str = "auto") -> None:
    """Re-apply joints after a pin toggle and repack."""
    apply_joints(design)
    pack_design(design, method=method)


def toggle_pin(design: TrussDesign, node: int, method: str = "auto") -> bool:
    """Flip glue/pin at a node; returns the new state."""
    new = not design.pins[node]
    design.pin_override[node] = new
    refresh(design, method=method)
    return new


# ---------------------------------------------------------------------------
# Optimiser
# ---------------------------------------------------------------------------

def candidate_grid(params: TrussParams) -> List[Tuple[str, int, int]]:
    W, H = float(params.width), float(params.height)
    if params.max_span <= _TOL:
        raise ValueError("Stick too short for any member (L - W - 2e <= 0)")
    types = TRUSS_TYPES if params.truss_type in ("", "Auto", None) else (params.truss_type,)
    if params.panels:
        ns = [int(params.panels)]
    else:
        n_lo = max(1, math.ceil(W / params.max_span - 1e-9))
        n_hi = max(n_lo, min(params.max_panels, int(W // params.min_span)))
        ns = list(range(n_lo, n_hi + 1))
    if params.rows:
        ms = [int(params.rows)]
    else:
        m_lo = max(1, math.ceil(H / params.max_span - 1e-9))
        m_hi = max(m_lo, min(params.max_rows, int(H // params.min_span)))
        ms = list(range(m_lo, m_hi + 1))
    return [(t, n, m) for t in types for n in ns for m in ms]


def optimise(params: TrussParams, top: int = 3,
             exact_finalists: int = 5) -> List[TrussDesign]:
    """Return up to `top` best designs (sticks first, then joints).

    Layouts above params.max_layers are dropped; if none fits, the
    thinnest layouts are returned with relaxed_layers set.
    """
    found: List[TrussDesign] = []
    for t, n, m in candidate_grid(params):
        d = build_design(params, t, n, m, enforce_layers=False)
        if d is not None:
            found.append(d)
    if not found:
        return []
    ok = [d for d in found if d.layers <= params.max_layers]
    if not ok:
        thinnest = min(d.layers for d in found)
        ok = [d for d in found if d.layers == thinnest]
        for d in ok:
            d.relaxed_layers = thinnest
    ok.sort(key=lambda d: (d.score, d.sticks))
    finalists = ok[:max(top, exact_finalists)]
    for d in finalists:
        try:
            pack_design(d, method="auto")
        except Exception:
            pack_design(d, method="heuristic")
    finalists.sort(key=lambda d: (d.score, d.sticks, len(d.all_pieces)))
    return finalists[:top]


# ---------------------------------------------------------------------------
# Output for Small parts
# ---------------------------------------------------------------------------

def to_small_parts(design: TrussDesign) -> List[Part]:
    """Group identical pieces into Small parts lines with label + qty.

    Every piece has both ends rounded (cap concentric with the end
    hole). Labels list the grouped piece numbers, e.g. "V1-3/5".
    """
    groups: Dict[Tuple, List[Piece]] = {}
    order: List[Tuple] = []
    for p in design.all_pieces:
        key = (p.kind,) + p.signature()
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(p)
    parts: List[Part] = []
    for key in order:
        ps = groups[key]
        kind = ps[0].kind
        label = _range_label(kind, [int(p.label[1:]) for p in ps])
        parts.append(Part(
            length=round(ps[0].length, 3),
            is_cut_down=True,
            is_cut_up=True,
            hole_centers=[round(h, 3) for h in ps[0].holes],
            label=label,
            qty=len(ps),
        ))
    return parts
