"""1D cutting-stock helpers for the Small parts tab.

Packs piece lengths into the fewest sticks of a given capacity.
No kerf is applied; the caller treats usable stick length as L.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

# Lengths within this tolerance are treated as fitting / equal.
_TOL = 1e-9


def _fits(used: float, item: float, capacity: float) -> bool:
    return used + item <= capacity + _TOL


def _pack_decreasing(
    capacity: float,
    lengths: Sequence[float],
    indices: Sequence[int],
    pick: str,
) -> List[List[int]]:
    """Place the given indices, longest first.

    pick='first' is First Fit Decreasing; pick='best' is Best Fit Decreasing.
    Each returned bin is a list of original part indices (placement order
    is pack order, not a geometric arrangement).
    """
    order = sorted(indices, key=lambda i: (-float(lengths[i]), i))
    bins: List[List[int]] = []
    used: List[float] = []

    for i in order:
        item = float(lengths[i])
        if pick == "best":
            best_idx = -1
            best_remain = capacity + 1.0
            for b, u in enumerate(used):
                if _fits(u, item, capacity):
                    remain = capacity - (u + item)
                    if remain < best_remain - _TOL:
                        best_remain = remain
                        best_idx = b
            if best_idx >= 0:
                bins[best_idx].append(i)
                used[best_idx] += item
            else:
                bins.append([i])
                used.append(item)
        else:
            placed = False
            for b, u in enumerate(used):
                if _fits(u, item, capacity):
                    bins[b].append(i)
                    used[b] += item
                    placed = True
                    break
            if not placed:
                bins.append([i])
                used.append(item)
    return bins


def cut_ffd(capacity: float, lengths: Sequence[float]) -> List[List[int]]:
    """First Fit Decreasing. Returns bins of original indices."""
    return _pack_decreasing(
        capacity, lengths, range(len(lengths)), pick="first"
    )


def cut_bfd(capacity: float, lengths: Sequence[float]) -> List[List[int]]:
    """Best Fit Decreasing. Returns bins of original indices."""
    return _pack_decreasing(
        capacity, lengths, range(len(lengths)), pick="best"
    )


def _bin_score(bins: List[List[int]]) -> Tuple[int, int]:
    """Fewer bins is better. Tie-break: stable (0)."""
    return (len(bins), 0)


def pack_heuristic(
    capacity: float,
    lengths: Sequence[float],
    indices: Optional[Sequence[int]] = None,
) -> List[List[int]]:
    """Best of FFD and BFD (fewer sticks; FFD on a tie)."""
    if indices is None:
        indices = list(range(len(lengths)))
    ffd = _pack_decreasing(capacity, lengths, indices, pick="first")
    bfd = _pack_decreasing(capacity, lengths, indices, pick="best")
    if _bin_score(bfd) < _bin_score(ffd):
        return bfd
    return ffd


def pack_exact(
    capacity: float,
    lengths: Sequence[float],
    indices: Optional[Sequence[int]] = None,
    time_limit: float = 2.0,
) -> List[List[int]]:
    """Exact min-stick packing via CP-SAT. Raises if ortools is missing."""
    from ortools.sat.python import cp_model

    if indices is None:
        indices = list(range(len(lengths)))
    items = list(indices)
    n = len(items)
    if n == 0:
        return []

    # Scale to integers for CP-SAT.
    def decimals(x: float) -> int:
        s = f"{float(x):.6f}".rstrip("0").rstrip(".")
        return len(s.split(".")[1]) if "." in s else 0

    max_dec = max([decimals(capacity)] + [decimals(lengths[i]) for i in items])
    scale = 10 ** min(max_dec, 4)
    cap = int(round(float(capacity) * scale))
    L = [int(round(float(lengths[i]) * scale)) for i in items]
    max_bins = n

    model = cp_model.CpModel()
    # x[j][b] = item j assigned to bin b
    x = [[model.NewBoolVar(f"x_{j}_{b}") for b in range(max_bins)]
         for j in range(n)]
    used = [model.NewBoolVar(f"u_{b}") for b in range(max_bins)]

    for j in range(n):
        model.Add(sum(x[j][b] for b in range(max_bins)) == 1)

    for b in range(max_bins):
        model.Add(sum(L[j] * x[j][b] for j in range(n)) <= cap * used[b])
        # Force bin order so the assignment is unique up to permutation.
        if b + 1 < max_bins:
            model.Add(used[b] >= used[b + 1])

    model.Minimize(sum(used))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Exact packer found no feasible layout")

    bins: List[List[int]] = []
    for b in range(max_bins):
        if solver.Value(used[b]):
            group = [items[j] for j in range(n) if solver.Value(x[j][b])]
            bins.append(group)
    return bins


def pack_pieces(
    capacity: float,
    lengths: Sequence[float],
    method: str = "auto",
    time_limit: float = 2.0,
) -> Tuple[List[List[int]], List[int]]:
    """Pack lengths into sticks of `capacity`.

    method:
      - 'heuristic' or 'ffd' / 'bfd': no ortools
      - 'exact': CP-SAT (requires ortools)
      - 'auto': exact when ortools is available, else best of FFD/BFD;
        falls back to the heuristic if the exact solve fails

    Returns (bins, unplaced). Unplaced indices are pieces with length
    <= 0 or longer than capacity. No kerf is subtracted.
    """
    unplaced = [
        i for i, raw in enumerate(lengths)
        if float(raw) <= _TOL or float(raw) > float(capacity) + _TOL
    ]
    placeable = [i for i in range(len(lengths)) if i not in set(unplaced)]
    if not placeable:
        return [], unplaced

    method = (method or "auto").lower()
    bins: List[List[int]]
    if method == "ffd":
        bins = _pack_decreasing(capacity, lengths, placeable, pick="first")
    elif method == "bfd":
        bins = _pack_decreasing(capacity, lengths, placeable, pick="best")
    elif method == "heuristic":
        bins = pack_heuristic(capacity, lengths, placeable)
    elif method == "exact":
        bins = pack_exact(capacity, lengths, placeable, time_limit=time_limit)
    elif method == "auto":
        try:
            bins = pack_exact(
                capacity, lengths, placeable, time_limit=time_limit
            )
        except Exception:
            bins = pack_heuristic(capacity, lengths, placeable)
    else:
        raise ValueError(f"Unknown packing method: {method}")
    return bins, unplaced


def cut_optimize(
    capacity: float,
    lengths: Sequence[float],
) -> List[List[int]]:
    """Backward-compatible wrapper: heuristic bins of original indices."""
    bins, unplaced = pack_pieces(capacity, lengths, method="heuristic")
    if unplaced:
        # Previous API always opened a new bin; pieces longer than the
        # stick cannot be placed and are omitted here. Call pack_pieces
        # directly if you need the unplaced list.
        pass
    return bins
