"""
Loi thuat toan xep thanh chu nhat (strip) vao vung go con lai.

Khong phu thuoc GUI. Ham chinh: pack_strips(mask, mm_per_px, ...).

Quy uoc:
    - mask uint8: 255 (hoac > 0) = go dung duoc, 0 = da cat. Hang 0 = mep TREN.
    - Ket qua tra ve theo toa do DSL (mm): goc (0, 0) = goc DUOI-TRAI cua tam,
      truc x sang phai, truc y huong LEN (giong canvas cua tab_designer).
    - Moi strip: dict(x, y, w, h, orient) voi (x, y) la goc duoi-trai cua
      hinh chu nhat, dung luon cho lenh DSL "R x y w h".

Thuat toan (heuristic, nhanh, dam bao dung):
    1. Voi 1 huong (vd ngang): moi "bang" (band) la mot dai ngang cao bang
       be rong thanh, bat dau o hang r. Trong band, cac cot ma toan bo chieu
       cao band la go tao thanh cac doan lien tuc (run).
    2. Moi run dai n pixel: chon tap do dai thanh toi uu bang knapsack
       (do dai cho phep trong [min, max] theo buoc step, giua 2 thanh cach
       nhau gap). Gia tri chi phu thuoc n nen tinh truoc 1 lan.
    3. Chon tap cac band khong chong nhau (cach nhau >= be rong + gap) toi
       uu bang quy hoach dong 1 chieu theo hang.
    4. Chien luoc ket hop 2 huong: chi ngang, chi doc, ngang roi lap phan
       con lai bang doc, doc roi ngang, va chon chien luoc tot nhat cho tung
       vung go lien thong. Lay ket qua tot nhat.
    5. Kiem tra lai ket qua (verify_strips): nam tron trong go, khong chong
       nhau, cach nhau >= gap.
"""
import math

import cv2
import numpy as np

EPS = 1e-9


def _ceil_px(mm, res):
    return int(math.ceil(mm / res - 1e-6))


def _floor_px(mm, res):
    return int(math.floor(mm / res + 1e-6))


def _grid_slack(res):
    """
    Toa do xuat ra DSL lam tron toi 0.01 mm. Neu mm_per_px khong phai boi so
    cua 0.01 (vd do phan giai tu dong 0.5393) thi diem dau thanh bi lam tron
    len toi da 0.01 mm => moi thanh can chua them 0.01 mm trong so pixel no
    chiem de khong bao gio tran ra ngoai vung pixel da kiem tra.
    """
    return 0.0 if abs(res * 100 - round(res * 100)) < 1e-9 else 0.01


def allowed_lengths(min_len, max_len, step, res):
    """
    Danh sach (do dai mm, so pixel chiem cho) cua cac do dai cho phep.
    Do dai luon lam tron toi 0.01 mm.
    """
    if max_len < min_len:
        min_len, max_len = max_len, min_len
    q = _grid_slack(res)
    out = []
    if step and step > 0:
        n = int(math.floor((max_len - min_len) / step + 1e-6))
        for i in range(n + 1):
            L = round(min_len + i * step, 2)
            out.append((L, _ceil_px(L + q, res)))
    else:
        # Khong co buoc: do dai = phan nguyen 0.01 mm lon nhat vua so pixel
        seen = set()
        for p in range(_ceil_px(min_len + q, res),
                       _floor_px(max_len + q, res) + 2):
            L = math.floor((p * res - q) * 100 + 1e-6) / 100.0
            if min_len - 1e-9 <= L <= max_len + 1e-9 and L not in seen:
                seen.add(L)
                out.append((L, p))
    return out


class _Knapsack:
    """Bang toi uu cho 1 run dai n pixel (tinh truoc cho moi n)."""

    def __init__(self, lengths, gap_px, max_n, objective):
        self.gap = gap_px
        self.items = []
        for L, p in lengths:
            if objective == "count":
                v = 10 ** 7 + int(round(L * 100))
            else:
                # tie-break: cung tong chieu dai thi uu tien it thanh (it cat)
                v = int(round(L * 100)) * 1000 - 1
            self.items.append((p + gap_px, v, L, p))
        cap = max_n + gap_px + 1
        best = np.zeros(cap, dtype=np.int64)
        choice = np.full(cap, -1, dtype=np.int64)
        for c in range(1, cap):
            b = best[c - 1]
            ch = -1
            for i, (s, v, _, _) in enumerate(self.items):
                if s <= c and best[c - s] + v > b:
                    b = best[c - s] + v
                    ch = i
            best[c] = b
            choice[c] = ch
        self.best = best
        self.choice = choice

    def value(self, n):
        return int(self.best[n + self.gap])

    def pieces(self, n):
        """Danh sach (L_mm, px) cua cac thanh dat trong run dai n."""
        c = n + self.gap
        out = []
        while c > 0:
            ch = self.choice[c]
            if ch < 0:
                c -= 1
                continue
            s, _, L, p = self.items[ch]
            out.append((L, p))
            c -= s
        out.sort(key=lambda t: -t[0])
        return out


def _runs(row_bool):
    """Tra ve list (start, length) cac doan True lien tuc."""
    if not row_bool.any():
        return []
    d = np.diff(np.concatenate(([0], row_bool.astype(np.int8), [0])))
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return list(zip(starts.tolist(), (ends - starts).tolist()))


def _pack_one_orientation(free, w_px, gap_px, ks):
    """
    Xep thanh nam ngang (dai theo truc cot) tren mang bool free (hang x cot).
    Tra ve (tong gia tri, list (r0, c0, L_mm, len_px)).
    """
    H, W = free.shape
    if H < w_px:
        return 0, []
    cs = np.vstack([np.zeros((1, W), np.int32),
                    np.cumsum(free.astype(np.int32), axis=0)])
    nb = H - w_px + 1
    vals = np.zeros(nb, dtype=np.int64)
    runs_at = [None] * nb
    for r in range(nb):
        colfree = (cs[r + w_px] - cs[r]) == w_px
        runs = _runs(colfree)
        if gap_px > 0 and len(runs) > 1:
            # 2 run sat nhau (ngan cach boi vet cat hep hon gap): lui diem
            # dau run sau de van dam bao khoang cach gap giua cac thanh
            fixed = [runs[0]]
            for st, n in runs[1:]:
                pst, pn = fixed[-1]
                between = st - (pst + pn)
                if between < gap_px:
                    d = gap_px - between
                    st, n = st + d, n - d
                if n > 0:
                    fixed.append((st, n))
            runs = fixed
        v = 0
        for _, n in runs:
            v += ks.value(n)
        vals[r] = v
        runs_at[r] = runs
    # Quy hoach dong chon band: F[r] = max(F[r+1], vals[r] + F[r+w+gap])
    stride = w_px + gap_px
    F = np.zeros(nb + stride + 1, dtype=np.int64)
    take = np.zeros(nb, dtype=bool)
    for r in range(nb - 1, -1, -1):
        a = F[r + 1]
        b = vals[r] + F[r + stride] if vals[r] > 0 else -1
        if b > a:
            F[r] = b
            take[r] = True
        else:
            F[r] = a
    placed = []
    r = 0
    while r < nb:
        if take[r]:
            for c0, n in runs_at[r]:
                c = c0
                for L, p in ks.pieces(n):
                    placed.append((r, c, L, p))
                    c += p + gap_px
            r += stride
        else:
            r += 1
    return int(F[0]), placed


def _strip_value(L, objective):
    if objective == "count":
        return 10 ** 7 + int(round(L * 100))
    return int(round(L * 100)) * 1000 - 1


class _Packer:
    def __init__(self, free, res, strip_w, lengths, gap, objective):
        self.res = res
        self.strip_w = strip_w
        self.w_px = _ceil_px(strip_w + _grid_slack(res), res)
        self.gap_px = _ceil_px(gap, res) if gap > 0 else 0
        self.objective = objective
        n = max(free.shape) + 2
        self.ks = _Knapsack(lengths, self.gap_px, n, objective)

    def run(self, free, orient):
        """orient: 'H' hoac 'V'. Tra ve list rect pixel (r0, c0, hpx, wpx,
        L_mm, orient)."""
        if orient == "H":
            _, pl = _pack_one_orientation(free, self.w_px, self.gap_px,
                                          self.ks)
            return [(r, c, self.w_px, p, L, "H") for r, c, L, p in pl]
        _, pl = _pack_one_orientation(free.T, self.w_px, self.gap_px, self.ks)
        return [(c, r, p, self.w_px, L, "V") for r, c, L, p in pl]

    def block(self, free, rects):
        """Danh dau vung da dung (mo rong them gap) la khong con trong."""
        f = free.copy()
        g = self.gap_px
        H, W = f.shape
        for r, c, h, w, _, _ in rects:
            f[max(0, r - g):min(H, r + h + g), max(0, c - g):min(W, c + w + g)] = False
        return f

    def score(self, rects):
        return sum(_strip_value(t[4], self.objective) for t in rects)

    def strategies(self, free, orients):
        cands = {}
        for o in orients:
            cands[o] = self.run(free, o)
        if len(orients) == 2:
            # Xep huong a truoc, sau do lap xen ke b, a, b... vao phan con
            # lai cho toi khi khong them duoc thanh nao
            for a, b in (("H", "V"), ("V", "H")):
                rects = list(cands[a])
                name = a
                cur = [b, a]
                for k in range(4):
                    o = cur[k % 2]
                    more = self.run(self.block(free, rects), o)
                    if not more:
                        break
                    rects += more
                    name += "+" + o
                cands[name] = rects
        return cands


def pack_strips(mask, mm_per_px, strip_w=10.0, min_len=30.0, max_len=100.0,
                step=0.0, gap=0.5, orient="both", objective="length"):
    """
    Xep cac thanh rong strip_w (mm), dai trong [min_len, max_len] (mm, buoc
    step neu > 0) vao vung go cua mask.

    orient: "H" (thanh nam ngang, song song Ox), "V" (doc), "both".
    objective: "length" (tong chieu dai lon nhat) hoac "count" (nhieu thanh).
    gap: khoang cach toi thieu giua 2 thanh (mm), vd do rong vet cat.

    Tra ve dict: strips (list dict x,y,w,h,orient,length), count,
    total_length, strategy, params.
    """
    res = float(mm_per_px)
    strip_w = round(float(strip_w), 2)
    free = np.asarray(mask) > 0
    lengths = allowed_lengths(min_len, max_len, step, res)
    if not lengths:
        raise ValueError("No valid length in the selected range")
    orients = ["H", "V"] if orient == "both" else [orient.upper()]
    pk = _Packer(free, res, strip_w, lengths, gap, objective)

    # Chien luoc toan cuc
    cands = pk.strategies(free, orients)
    best_name, best = max(cands.items(), key=lambda kv: pk.score(kv[1]))

    # Chien luoc theo tung vung go lien thong: moi vung chon cach tot nhat
    n, lab, stats, _ = cv2.connectedComponentsWithStats(
        free.astype(np.uint8), connectivity=4)
    if n > 2:
        order = sorted(range(1, n), key=lambda i: -stats[i, cv2.CC_STAT_AREA])
        cur_free = free.copy()
        comp_rects = []
        for i in order:
            x, y, w, h = stats[i, :4]
            if w < pk.w_px and h < pk.w_px:
                continue
            sub = (lab[y:y + h, x:x + w] == i) & cur_free[y:y + h, x:x + w]
            sc = pk.strategies(sub, orients)
            rs = max(sc.values(), key=pk.score)
            rs = [(r + y, c + x, hh, ww, L, o) for r, c, hh, ww, L, o in rs]
            comp_rects += rs
            cur_free = pk.block(cur_free, rs)
        if pk.score(comp_rects) > pk.score(best):
            best_name, best = "per region", comp_rects

    H = free.shape[0]
    strips = []
    for r, c, hpx, wpx, L, o in best:
        if o == "H":
            w_mm, h_mm = L, strip_w
        else:
            w_mm, h_mm = strip_w, L
        # Lam tron toi 0.01 mm ve phia TRONG vung pixel: mep trai lam tron
        # len, mep tren lam tron xuong (truc y huong len)
        x = math.ceil(c * res * 100 - 1e-6) / 100.0
        y_top = math.floor((H - r) * res * 100 + 1e-6) / 100.0
        y = y_top - h_mm
        strips.append({"x": round(x, 2), "y": round(y, 2),
                       "w": round(w_mm, 2), "h": round(h_mm, 2),
                       "orient": o, "length": round(L, 2)})
    total = sum(s["length"] for s in strips)
    return {
        "strips": strips,
        "count": len(strips),
        "total_length": round(total, 3),
        "strategy": best_name,
        "params": dict(strip_w=strip_w, min_len=min_len, max_len=max_len,
                       step=step, gap=gap, orient=orient,
                       objective=objective, mm_per_px=res),
    }


def verify_strips(mask, mm_per_px, strips, gap):
    """
    Kiem tra ket qua. Tra ve list loi (rong = dung).
      - moi thanh nam tron trong vung go (tat ca pixel ma no phu deu la go)
      - 2 thanh bat ky cach nhau >= gap (khoang cach Euclid giua 2 hcn)
    """
    res = float(mm_per_px)
    m = np.asarray(mask) > 0
    H, W = m.shape
    errs = []
    for i, s in enumerate(strips):
        x0, x1 = s["x"], s["x"] + s["w"]
        yt = H * res - (s["y"] + s["h"])      # mep tren, tinh tu tren xuong
        yb = H * res - s["y"]
        c0, c1 = int(math.floor(x0 / res + 1e-6)), int(math.ceil(x1 / res - 1e-6))
        r0, r1 = int(math.floor(yt / res + 1e-6)), int(math.ceil(yb / res - 1e-6))
        if c0 < 0 or r0 < 0 or c1 > W or r1 > H:
            errs.append("strip %d is outside the sheet" % i)
            continue
        if not m[r0:r1, c0:c1].all():
            errs.append("strip %d overlaps a cut area" % i)
    # Kiem tra khoang cach tung cap (sap theo x de cat tia)
    idx = sorted(range(len(strips)), key=lambda k: strips[k]["x"])
    for a in range(len(idx)):
        sa = strips[idx[a]]
        for b in range(a + 1, len(idx)):
            sb = strips[idx[b]]
            if sb["x"] - (sa["x"] + sa["w"]) >= max(gap, 1e-6):
                break
            ox = min(sa["x"] + sa["w"], sb["x"] + sb["w"]) - max(sa["x"], sb["x"])
            oy = min(sa["y"] + sa["h"], sb["y"] + sb["h"]) - max(sa["y"], sb["y"])
            if ox > 1e-6 and oy > 1e-6:
                errs.append("strips %d and %d overlap" % (idx[a], idx[b]))
                continue
            dx = max(0.0, sb["x"] - (sa["x"] + sa["w"]),
                     sa["x"] - (sb["x"] + sb["w"]))
            dy = max(0.0, sb["y"] - (sa["y"] + sa["h"]),
                     sa["y"] - (sb["y"] + sb["h"]))
            d = math.hypot(dx, dy)
            if d < gap - 1e-6:
                errs.append("strips %d and %d too close (%.3f mm)"
                            % (idx[a], idx[b], d))
    return errs


def strips_to_dsl(strips, decimals=2):
    """Xuat cac thanh thanh lenh DSL 'R x y w h' (mm)."""
    def f(v):
        s = ("%." + str(decimals) + "f") % v
        s = s.rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return ["R %s %s %s %s" % (f(s["x"]), f(s["y"]), f(s["w"]), f(s["h"]))
            for s in strips]


def render_result(warped_or_mask, mask, mm_per_px, strips, scale=2):
    """Ve ket qua: nen anh (neu co) + vung cat to do + thanh xep to xanh."""
    if warped_or_mask is None:
        base = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        base[mask > 0] = (200, 225, 240)
        base[mask == 0] = (60, 60, 60)
    else:
        base = warped_or_mask.copy()
        if base.ndim == 2:
            base = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
        red = np.zeros_like(base)
        red[:] = (0, 0, 200)
        sel = mask == 0
        base[sel] = (base[sel] * 0.5 + red[sel] * 0.5).astype(np.uint8)
    H = mask.shape[0]
    out = cv2.resize(base, None, fx=scale, fy=scale,
                     interpolation=cv2.INTER_NEAREST)
    k = scale / mm_per_px
    for s in strips:
        x0 = int(round(s["x"] * k))
        x1 = int(round((s["x"] + s["w"]) * k))
        y0 = int(round((H * mm_per_px - s["y"] - s["h"]) * k))
        y1 = int(round((H * mm_per_px - s["y"]) * k))
        col = (60, 170, 40) if s["orient"] == "H" else (200, 120, 20)
        cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), col, -1)
        cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), (0, 0, 0), 1)
    return out
