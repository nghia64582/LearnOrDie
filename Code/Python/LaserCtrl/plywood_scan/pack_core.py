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
    for i, st in enumerate(strips):
        st["id"] = i + 1
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


def _fmt(v, decimals=2):
    s = ("%." + str(decimals) + "f") % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def strips_to_dsl(strips, decimals=2, style="add", offset=(0.0, 0.0)):
    """
    Xuat cac thanh thanh DSL (mm).
      style="add" (mac dinh): moi thanh la mot khung toa do cuc bo
            ADD x y <so thu tu>
            R 0 0 w h
            END
        de co the them chi tiet (JF / JM, lo...) ben trong tung thanh, toa do
        tinh tu goc duoi-trai cua thanh.
      style="rect": moi thanh 1 dong "R x y w h".
    offset: cong vao x, y (offset may, dung chung voi gcode can chinh).
    """
    out = []
    ox, oy = float(offset[0]), float(offset[1])
    for i, s in enumerate(strips):
        x, y = _fmt(s["x"] + ox, decimals), _fmt(s["y"] + oy, decimals)
        w, h = _fmt(s["w"], decimals), _fmt(s["h"], decimals)
        if style == "rect":
            out.append("R %s %s %s %s" % (x, y, w, h))
        else:
            out += ["ADD %s %s %s" % (x, y, s.get("id", i + 1)),
                    "R 0 0 %s %s" % (w, h),
                    "END"]
    return out


def parse_dsl_strips(lines):
    """
    Doc nguoc DSL do strips_to_dsl tao (ca 2 kieu), mo phong cach
    tab_designer xu ly ADD (cong don stack) / END (bo lop cuoi).
    Tra ve list dict x, y, w, h, label (de kiem tra lai).
    """
    stack = []
    out = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == "ADD":
            stack.append((float(parts[1]), float(parts[2]),
                          " ".join(parts[3:])))
        elif parts[0] == "END":
            if stack:
                stack.pop()
        elif parts[0] == "R":
            x, y, w, h = map(float, parts[1:5])
            out.append({"x": x + sum(d[0] for d in stack),
                        "y": y + sum(d[1] for d in stack), "w": w, "h": h,
                        "label": stack[-1][2] if stack else ""})
    return out


def parse_lengths(text):
    """
    Doc danh sach do dai nhap tay, vd "80,80,100,100" hoac "80 80; 100".
    Ho tro dang "100x3" / "100*3" = 3 thanh 100 mm.
    Tra ve list float (mm, lam tron 0.01). Loi -> ValueError (tieng Anh).
    """
    import re
    tokens = [t for t in re.split(r"[,;\s]+", text.strip()) if t]
    if not tokens:
        raise ValueError("Enter at least one length, e.g. 80,80,100,100")
    out = []
    for t in tokens:
        m = re.fullmatch(r"([0-9]*\.?[0-9]+)(?:[x*]([0-9]+))?", t.lower())
        if not m:
            raise ValueError("Invalid length: '%s' (use numbers in mm, "
                             "e.g. 80,80,100 or 100x3)" % t)
        L = round(float(m.group(1)), 2)
        n = int(m.group(2)) if m.group(2) else 1
        if L <= 0:
            raise ValueError("Length must be > 0: '%s'" % t)
        if n <= 0 or n > 1000:
            raise ValueError("Invalid repeat count: '%s'" % t)
        out += [L] * n
    if len(out) > 2000:
        raise ValueError("Too many pieces (max 2000)")
    return out


# ---------------------------------------------------------------------------
# Che do chinh: xep dung danh sach thanh nguoi dung nhap
# ---------------------------------------------------------------------------

def _integral(a):
    s = np.zeros((a.shape[0] + 1, a.shape[1] + 1), np.int32)
    s[1:, 1:] = np.cumsum(np.cumsum(a.astype(np.int32), axis=0), axis=1)
    return s


def _box_sums(S, h, w):
    """Tong cua moi o h x w (goc tren-trai (r, c)) tu anh tich phan S."""
    return S[h:, w:] - S[:-h, w:] - S[h:, :-w] + S[:-h, :-w]


def _best_position(S_av, S_bl, H, W, h, w, rule):
    """
    Tim vi tri dat hcn h x w (pixel). S_av: anh tich phan cua vung con trong,
    S_bl: anh tich phan cua vung bi chan (da pad 1 pixel). Tra ve
    (score, r, c) hoac None.
      rule "contact": uu tien vi tri tiep xuc nhieu voi vung da dung / mep
          (xep chat), hoa thi gan goc toa do (duoi-trai)
      rule "bl": gan goc duoi-trai nhat (bottom-left)
    """
    if h > H or w > W:
        return None
    ok = _box_sums(S_av, h, w) == h * w
    rr, cc = np.nonzero(ok)
    if rr.size == 0:
        return None
    # khoang cach toi goc DSL (0,0) = goc duoi-trai: (H - (r + h)) + c
    dist = (H - (rr + h)) + cc
    if rule == "bl":
        key = -((H - (rr + h)).astype(np.int64) * (W + 1) + cc)
    else:
        ring = (S_bl[rr + h + 2, cc + w + 2] - S_bl[rr, cc + w + 2]
                - S_bl[rr + h + 2, cc] + S_bl[rr, cc])
        frac = ring / float(2 * (h + w) + 4)
        key = np.round(frac * 1000).astype(np.int64) * (H + W + 2) - dist
    i = int(np.argmax(key))
    return int(key[i]), int(rr[i]), int(cc[i])


def pack_pieces(mask, mm_per_px, lengths, strip_w=10.0, gap=0.5,
                orient="both", trials=None, seed=0, time_limit=6.0):
    """
    Xep DUNG danh sach thanh (do dai trong lengths, mm; be rong strip_w).
    Moi thanh giu nguyen do dai (lam tron 0.01 mm), so thu tu = vi tri trong
    danh sach nhap (bat dau tu 1).

    Heuristic: thu nhieu thu tu (dai truoc, theo thu tu nhap, ngan truoc,
    xao tron ngau nhien giu uu tien dai) x quy tac chon vi tri (tiep xuc
    nhieu nhat / goc duoi-trai) x uu tien huong; moi thanh chon vi tri + huong
    tot nhat tren vung con trong (da tru khoang cach gap). Lay phuong an dat
    duoc NHIEU thanh nhat, roi tong chieu dai lon nhat, roi gon / gan goc.
    Cac thu tu co dinh luon duoc chay; cac thu tu ngau nhien dung khi het
    time_limit (giay) hoac khi da dat du tat ca thanh.

    Tra ve dict: strips (da dat, co id, length, x, y, w, h, orient),
    unplaced (list dict id, length), count, requested, total_length,
    strategy, params.
    """
    res = float(mm_per_px)
    strip_w = round(float(strip_w), 2)
    lengths = [round(float(L), 2) for L in lengths]
    free = np.asarray(mask) > 0
    H, W = free.shape
    q = _grid_slack(res)
    g = _ceil_px(gap, res) if gap > 0 else 0
    w_px = _ceil_px(strip_w + q, res)
    orients = ["H", "V"] if orient == "both" else [orient.upper()]
    n = len(lengths)
    ids = list(range(n))

    orders = [("longest first", sorted(ids, key=lambda i: (-lengths[i], i))),
              ("input order", ids[:]),
              ("shortest first", sorted(ids, key=lambda i: (lengths[i], i)))]
    if trials is None:
        trials = max(2, min(12, 600 // max(1, n)))
    rng = np.random.default_rng(seed)
    for t in range(trials):
        # xao tron nhe: dai truoc nhung co nhieu ngau nhien
        noise = rng.uniform(0, 0.35, n)
        orders.append(("random #%d" % (t + 1),
                       sorted(ids, key=lambda i: -lengths[i] * (1 - noise[i]))))

    def run(order, rule, pref):
        avail = free.copy()
        placed = []
        # Vung trong chi co thu hep lai => neu thanh dai p pixel khong vua
        # theo huong o thi moi thanh >= p cung khong vua: bo qua cho nhanh
        fail = {o: 10 ** 9 for o in pref}
        for i in order:
            L = lengths[i]
            p = _ceil_px(L + q, res)
            if all(p >= fail[o] for o in pref):
                continue
            best = None
            S_av = _integral(avail)
            S_bl = _integral(np.pad(~avail, 1, constant_values=True)) \
                if rule == "contact" else None
            for o in pref:
                if p >= fail[o]:
                    continue
                hh, ww = (w_px, p) if o == "H" else (p, w_px)
                bp = _best_position(S_av, S_bl, H, W, hh, ww, rule)
                if bp is None:
                    fail[o] = p
                if bp and (best is None or bp[0] > best[0]):
                    best = (bp[0], bp[1], bp[2], hh, ww, o)
            if best is None:
                continue
            _, r, c, hh, ww, o = best
            avail[max(0, r - g):min(H, r + hh + g),
                  max(0, c - g):min(W, c + ww + g)] = False
            placed.append((i, r, c, hh, ww, o))
        return placed

    def layout_key(placed):
        cnt = len(placed)
        tot = sum(lengths[i] for i, *_ in placed)
        spread = sum((H - (r + hh)) + c for _, r, c, hh, ww, _ in placed)
        return (cnt, round(tot, 2), -spread)

    import time
    t0 = time.time()
    best, best_key, best_name = [], None, ""
    prefs = [orients] if len(orients) == 1 else [["H", "V"], ["H"], ["V"]]
    for k_order, (oname, order) in enumerate(orders):
        if k_order >= 3:
            # thu tu ngau nhien: chi chay khi con thoi gian va chua dat het
            if best_key and best_key[0] == n:
                break
            if time.time() - t0 > time_limit:
                break
        for rule in ("contact", "bl"):
            for pref in (prefs if k_order == 0 else prefs[:1]):
                pl = run(order, rule, pref)
                k = layout_key(pl)
                if best_key is None or k > best_key:
                    best, best_key = pl, k
                    best_name = "%s, %s, %s" % (oname, rule, "+".join(pref))

    strips = []
    for i, r, c, hh, ww, o in sorted(best, key=lambda t: t[0]):
        L = lengths[i]
        w_mm, h_mm = (L, strip_w) if o == "H" else (strip_w, L)
        x = math.ceil(c * res * 100 - 1e-6) / 100.0
        y_top = math.floor((H - r) * res * 100 + 1e-6) / 100.0
        strips.append({"id": i + 1, "length": L, "orient": o,
                       "x": round(x, 2), "y": round(y_top - h_mm, 2),
                       "w": round(w_mm, 2), "h": round(h_mm, 2)})
    placed_ids = {s["id"] for s in strips}
    unplaced = [{"id": i + 1, "length": lengths[i]} for i in ids
                if i + 1 not in placed_ids]
    return {
        "strips": strips,
        "unplaced": unplaced,
        "count": len(strips),
        "requested": n,
        "total_length": round(sum(s["length"] for s in strips), 2),
        "strategy": best_name,
        "params": dict(strip_w=strip_w, gap=gap, orient=orient,
                       lengths=lengths, mm_per_px=res, mode="pieces"),
    }


def render_result(warped_or_mask, mask, mm_per_px, strips, scale=2,
                  labels=True, align_points=None, cross_mm=5.0):
    """Ve ket qua: nen anh (neu co) + vung cat to do + thanh xep to xanh,
    kem so thu tu cua tung thanh."""
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
    for i, s in enumerate(strips):
        x0 = int(round(s["x"] * k))
        x1 = int(round((s["x"] + s["w"]) * k))
        y0 = int(round((H * mm_per_px - s["y"] - s["h"]) * k))
        y1 = int(round((H * mm_per_px - s["y"]) * k))
        col = (60, 170, 40) if s["orient"] == "H" else (200, 120, 20)
        cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), col, -1)
        cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), (0, 0, 0), 1)
        if labels:
            txt = str(s.get("id", i + 1))
            short = min(x1 - x0, y1 - y0)
            fs = max(0.3, min(1.0, short / 40.0))
            th = 1 if fs < 0.6 else 2
            (tw, tht), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX,
                                           fs, th)
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            org = (cx - tw // 2, cy + tht // 2)
            cv2.putText(out, txt, org, cv2.FONT_HERSHEY_SIMPLEX, fs,
                        (255, 255, 255), th + 2, cv2.LINE_AA)
            cv2.putText(out, txt, org, cv2.FONT_HERSHEY_SIMPLEX, fs,
                        (0, 0, 0), th, cv2.LINE_AA)
    # Diem can chinh P1 (do), P2 (xanh) + khoang cach
    cols = [(60, 60, 255), (255, 150, 40)]
    cpx = []
    for i, pt in enumerate(align_points or []):
        if pt is None:
            continue
        xm, ym = pt
        cx = int(round(xm * k))
        cy = int(round((H * mm_per_px - ym) * k))
        cpx.append((cx, cy))
        half = max(8, int(round(cross_mm / 2 * k)))
        col = cols[i % 2]
        for d in ((half, 0), (0, half)):
            cv2.line(out, (cx - d[0], cy - d[1]), (cx + d[0], cy + d[1]),
                     (255, 255, 255), 5, cv2.LINE_AA)
            cv2.line(out, (cx - d[0], cy - d[1]), (cx + d[0], cy + d[1]),
                     col, 2, cv2.LINE_AA)
        txt = "P%d (%.2f, %.2f)" % (i + 1, xm, ym)
        (tw, tht), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        tx = cx + half + 6
        if tx + tw > out.shape[1] - 2:
            tx = cx - half - 6 - tw
        ty = min(max(cy - 8, tht + 4), out.shape[0] - 4)
        cv2.rectangle(out, (tx - 3, ty - tht - 4), (tx + tw + 3, ty + 5),
                      (30, 30, 30), -1)
        cv2.putText(out, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.8, col,
                    2, cv2.LINE_AA)
    if len(cpx) == 2:
        cv2.line(out, cpx[0], cpx[1], (0, 230, 255), 1, cv2.LINE_AA)
    return out
