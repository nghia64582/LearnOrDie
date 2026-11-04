"""Kiem tra giao cat giua block dang keo va cac doan con lai.

Dinh nghia (doan a cua block keo, doan b cua vat can):
- Hai doan song song / trung nhau (dinh sat) -> KHONG giao.
- Cat nhau tai diem nam giua CA HAI doan -> giao.
- Dau mut cham dau mut -> KHONG giao.
- Dau mut cua doan nay nam giua doan kia (chu T) -> giao NEU doan co dau
  mut do di vao PHIA TRONG hinh kia (kiem tra bang 1 diem do cach dau mut
  1e-3 mm theo huong doan, ray-casting voi cac doan cua hinh kia). Neu di
  ra phia ngoai thi chi la "cham" (vd canh doc cua block dang truot tren
  canh tren cua 1 hinh chu nhat) -> KHONG giao.
"""
import math

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

EPS = 1e-6      # mm
PROBE = 1e-3    # mm


def _cross(ax, ay, bx, by):
    return ax * by - ay * bx


def classify(a, b, eps=EPS):
    """'none' | 'cross' | 'a_end' (dau mut a nam giua b) | 'b_end'."""
    px, py, qx, qy = a
    sx, sy, tx, ty = b
    rx, ry = qx - px, qy - py
    ux, uy = tx - sx, ty - sy
    la, lb = math.hypot(rx, ry), math.hypot(ux, uy)
    if la < eps or lb < eps:
        return "none"
    d = _cross(rx, ry, ux, uy)
    if abs(d) <= eps * la * lb:
        return "none"
    wx, wy = sx - px, sy - py
    t = _cross(wx, wy, ux, uy) / d
    u = _cross(wx, wy, rx, ry) / d
    et, eu = eps / la, eps / lb
    if t < -et or t > 1 + et or u < -eu or u > 1 + eu:
        return "none"
    t_end = t < et or t > 1 - et
    u_end = u < eu or u > 1 - eu
    if t_end and u_end:
        return "none"
    if not t_end and not u_end:
        return "cross"
    return "a_end" if t_end else "b_end"


def point_inside(x, y, segs):
    inside = False
    for x1, y1, x2, y2 in segs:
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def _probe(seg, at_start):
    x1, y1, x2, y2 = seg
    L = math.hypot(x2 - x1, y2 - y1)
    if at_start:
        return x1 + (x2 - x1) / L * PROBE, y1 + (y2 - y1) / L * PROBE
    return x2 + (x1 - x2) / L * PROBE, y2 + (y1 - y2) / L * PROBE


def t_is_collision(a, b, a_shape_segs, b_shape_segs, kind):
    """Xu ly truong hop chu T: doan co dau mut di vao trong hinh kia?"""
    if kind == "a_end":
        seg, other, region = a, b, b_shape_segs
    else:
        seg, other, region = b, a, a_shape_segs
    d0 = _dist_point_seg(seg[0], seg[1], other)
    px, py = _probe(seg, at_start=d0 < _dist_point_seg(seg[2], seg[3], other))
    return point_inside(px, py, region)


def _dist_point_seg(x, y, s):
    x1, y1, x2, y2 = s
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
    return math.hypot(x - x1 - t * dx, y - y1 - t * dy)


class Collider:
    """Chuan bi 1 lan khi bat dau keo; collides(ox, oy) goi nhieu lan."""

    def __init__(self, moving, obstacles):
        # moving / obstacles: list (shape_id, [segments])
        self.m_segs, self.m_sid, self.m_shape = [], [], {}
        for sid, segs in moving:
            self.m_shape[sid] = segs
            for s in segs:
                self.m_segs.append(s)
                self.m_sid.append(sid)
        self.o_segs, self.o_sid, self.o_shape = [], [], {}
        for sid, segs in obstacles:
            self.o_shape[sid] = segs
            for s in segs:
                self.o_segs.append(s)
                self.o_sid.append(sid)
        self.use_np = np is not None
        if self.use_np:
            self.M = np.array(self.m_segs, float).reshape(-1, 4)
            self.O = np.array(self.o_segs, float).reshape(-1, 4)
            self.O_min = np.minimum(self.O[:, :2], self.O[:, 2:])
            self.O_max = np.maximum(self.O[:, :2], self.O[:, 2:])
        xs = [c for s in self.m_segs for c in (s[0], s[2])] or [0]
        ys = [c for s in self.m_segs for c in (s[1], s[3])] or [0]
        self.m_bbox = (min(xs), min(ys), max(xs), max(ys))

    def _near_obstacles(self, ox, oy, pad=EPS * 10):
        x0, y0, x1, y1 = self.m_bbox
        x0, x1, y0, y1 = x0 + ox - pad, x1 + ox + pad, y0 + oy - pad, y1 + oy + pad
        if self.use_np:
            mask = ((self.O_max[:, 0] >= x0) & (self.O_min[:, 0] <= x1) &
                    (self.O_max[:, 1] >= y0) & (self.O_min[:, 1] <= y1))
            return np.nonzero(mask)[0]
        out = []
        for i, (a, b, c, d) in enumerate(self.o_segs):
            if max(a, c) >= x0 and min(a, c) <= x1 and \
               max(b, d) >= y0 and min(b, d) <= y1:
                out.append(i)
        return out

    def _shift(self, sid, ox, oy):
        return [(a + ox, b + oy, c + ox, d + oy) for a, b, c, d in self.m_shape[sid]]

    def collides(self, ox, oy):
        idx = self._near_obstacles(ox, oy)
        if len(idx) == 0 or not self.m_segs:
            return False
        if self.use_np:
            return self._collides_np(ox, oy, idx)
        for j in idx:
            b = self.o_segs[j]
            for i, s in enumerate(self.m_segs):
                a = (s[0] + ox, s[1] + oy, s[2] + ox, s[3] + oy)
                if self._pair(a, b, i, j, ox, oy):
                    return True
        return False

    def _pair(self, a, b, i, j, ox, oy):
        k = classify(a, b)
        if k == "cross":
            return True
        if k in ("a_end", "b_end"):
            return t_is_collision(a, b, self._shift(self.m_sid[i], ox, oy),
                                  self.o_shape[self.o_sid[j]], k)
        return False

    def _collides_np(self, ox, oy, idx):
        A = self.M + np.array([ox, oy, ox, oy])
        B = self.O[idx]
        # Loc them theo bbox tung doan cua A
        amin = np.minimum(A[:, :2], A[:, 2:]) - EPS * 10
        amax = np.maximum(A[:, :2], A[:, 2:]) + EPS * 10
        bmin = np.minimum(B[:, :2], B[:, 2:])
        bmax = np.maximum(B[:, :2], B[:, 2:])
        ov = ((amax[:, None, 0] >= bmin[None, :, 0]) &
              (amin[:, None, 0] <= bmax[None, :, 0]) &
              (amax[:, None, 1] >= bmin[None, :, 1]) &
              (amin[:, None, 1] <= bmax[None, :, 1]))
        ii, jj = np.nonzero(ov)
        if len(ii) == 0:
            return False
        a, b = A[ii], B[jj]
        rx, ry = a[:, 2] - a[:, 0], a[:, 3] - a[:, 1]
        ux, uy = b[:, 2] - b[:, 0], b[:, 3] - b[:, 1]
        la, lb = np.hypot(rx, ry), np.hypot(ux, uy)
        d = rx * uy - ry * ux
        ok = (la > EPS) & (lb > EPS) & (np.abs(d) > EPS * la * lb)
        ds = np.where(ok, d, 1.0)
        wx, wy = b[:, 0] - a[:, 0], b[:, 1] - a[:, 1]
        t = (wx * uy - wy * ux) / ds
        u = (wx * ry - wy * rx) / ds
        et, eu = EPS / np.maximum(la, EPS), EPS / np.maximum(lb, EPS)
        hit = ok & (t >= -et) & (t <= 1 + et) & (u >= -eu) & (u <= 1 + eu)
        t_end = (t < et) | (t > 1 - et)
        u_end = (u < eu) | (u > 1 - eu)
        if np.any(hit & ~t_end & ~u_end):
            return True
        for k in np.nonzero(hit & (t_end ^ u_end))[0]:
            i, j = ii[k], idx[jj[k]]
            kind = "a_end" if t_end[k] else "b_end"
            if t_is_collision(tuple(a[k]), tuple(b[k]),
                              self._shift(self.m_sid[i], ox, oy),
                              self.o_shape[self.o_sid[j]], kind):
                return True
        return False

    # ------------------------------------------------------------
    def _bsearch(self, L, T, iters=14):
        lo, hi = 0.0, 1.0
        for _ in range(iters):
            mid = (lo + hi) / 2
            if self.collides(L[0] + (T[0] - L[0]) * mid,
                             L[1] + (T[1] - L[1]) * mid):
                hi = mid
            else:
                lo = mid
        return (L[0] + (T[0] - L[0]) * lo, L[1] + (T[1] - L[1]) * lo)

    def resolve(self, last, cand, step=0.5, max_steps=200):
        """Tra ve (offset hop le, bi_chan). last phai hop le.

        Di tung buoc nho (<= step mm) tu last den cand de block khong
        "xuyen" qua vat can mong khi chuot di chuyen nhanh.
        """
        cur, blocked = last, False
        for _ in range(max_steps):
            dx, dy = cand[0] - cur[0], cand[1] - cur[1]
            dist = math.hypot(dx, dy)
            if dist < 1e-9:
                break
            f = min(1.0, step / dist)
            new, b = self._resolve_one(cur, (cur[0] + dx * f, cur[1] + dy * f))
            blocked = blocked or b
            moved = math.hypot(new[0] - cur[0], new[1] - cur[1])
            cur = new
            if b and moved < 1e-4:
                break
        return cur, blocked

    def _resolve_one(self, last, cand):
        if not self.collides(*cand):
            return self.snap(cand), False
        opts = []
        for T in ((cand[0], last[1]), (last[0], cand[1])):
            opts.append(T if not self.collides(*T) else self._bsearch(last, T))
        opts.append(self._bsearch(last, cand))
        best = min(opts, key=lambda p: math.hypot(p[0] - cand[0], p[1] - cand[1]))
        return self.snap(best), True

    def snap(self, pos, tol=0.02):
        """Hit nhe (< tol mm) toa do x / y cua block vao canh vat can."""
        ox, oy = pos
        idx = self._near_obstacles(ox, oy, pad=tol * 2)
        if len(idx) == 0:
            return pos
        oxs = {round(c, 9) for j in idx for c in (self.o_segs[j][0], self.o_segs[j][2])}
        oys = {round(c, 9) for j in idx for c in (self.o_segs[j][1], self.o_segs[j][3])}
        mxs = {c for s in self.m_segs for c in (s[0], s[2])}
        mys = {c for s in self.m_segs for c in (s[1], s[3])}

        def best(cur, mine, theirs):
            cands = []
            for t in theirs:
                for m in mine:
                    v = t - m
                    if abs(v - cur) < tol:
                        cands.append(v)
            return sorted(cands, key=lambda v: abs(v - cur))

        for vx in best(ox, mxs, oxs)[:3]:
            if not self.collides(vx, oy):
                ox = vx
                break
        for vy in best(oy, mys, oys)[:3]:
            if not self.collides(ox, vy):
                oy = vy
                break
        return ox, oy
