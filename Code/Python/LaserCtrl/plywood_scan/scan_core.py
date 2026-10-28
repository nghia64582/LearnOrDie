"""
Loi xu ly anh cho scan_app (khong phu thuoc GUI, co the import de test).

Quy uoc mask:
    - mask la anh uint8, 255 = go con lai (dung duoc), 0 = da cat / khong phai go
    - hang 0 cua mask = mep TREN cua tam (theo anh), cot 0 = mep TRAI
    - toa do DSL (mm): goc (0, 0) = goc DUOI-TRAI cua tam, truc y huong len
      => y_mm = (so_hang - hang) * mm_per_px
"""
import json
import os

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Doc / ghi anh an toan voi duong dan co dau tieng Viet tren Windows
# (cv2.imread khong doc duoc duong dan unicode tren Windows)
# ---------------------------------------------------------------------------

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, flags)
    if img is None:
        raise ValueError("Cannot read image: %s" % path)
    return img


def imwrite_unicode(path, img):
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise ValueError("Cannot write image: %s" % path)
    buf.tofile(path)


# ---------------------------------------------------------------------------
# Goc tam go
# ---------------------------------------------------------------------------

def order_corners(pts):
    """Sap xep 4 diem theo thu tu: tren-trai, tren-phai, duoi-phai, duoi-trai."""
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = pts[:, 0] - pts[:, 1]
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmax(d)]
    bl = pts[np.argmin(d)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def detect_sheet_corners(img):
    """
    Goi y 4 goc tam go: tim vung sang lon nhat (go mau sang), lay bao loi
    roi xap xi thanh tu giac. Tra ve np.array 4x2 (thu tu TL, TR, BR, BL)
    hoac None neu khong tim duoc.
    """
    h, w = img.shape[:2]
    scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
    small = cv2.resize(img, None, fx=scale, fy=scale) if scale != 1.0 else img
    blur = cv2.GaussianBlur(small, (5, 5), 0)
    L = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB)[:, :, 0]
    S = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)[:, :, 1]
    # Nguong Otsu cua do sang chi tinh tren cac pixel it bao hoa (bo qua
    # tham cat xanh), de tach go sang khoi mat ban / nen toi hon
    low_sat = L[S < 80]
    if low_sat.size < 100:
        low_sat = L.ravel()
    t, _ = cv2.threshold(low_sat.reshape(-1, 1), 0, 255,
                         cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = ((L > t) * 255).astype(np.uint8)
    # Lo da cat nam trong tam: dong lai bang cach lap day contour ngoai
    k = max(3, int(round(min(small.shape[:2]) * 0.02)) | 1)
    kern = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    # mo de cat cac cau noi mong voi ban / nen sang
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kern)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 0.1 * small.shape[0] * small.shape[1]:
        return None
    hull = cv2.convexHull(c)
    peri = cv2.arcLength(hull, True)
    quad = None
    for eps in np.linspace(0.01, 0.1, 19):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4:
            quad = approx.reshape(4, 2)
            break
    if quad is None:
        # Fallback: hinh chu nhat xoay nho nhat
        quad = cv2.boxPoints(cv2.minAreaRect(hull))
    return order_corners(np.asarray(quad, dtype=np.float32) / scale)


def auto_resolution(corners, width_mm, height_mm):
    """
    Tinh do phan giai (mm / pixel) tu 4 goc da chon va kich thuoc that,
    de anh nan giu xap xi do phan giai goc cua anh chup:
        rx = W / trung binh(do dai canh tren, canh duoi)   (pixel)
        ry = H / trung binh(do dai canh trai, canh phai)
        mm_per_px = (rx + ry) / 2
    Tra ve (mm_per_px, rx, ry). rx va ry lech nhieu => kich thuoc nhap sai
    hoac goc dat lech (hoac anh nghieng manh).
    """
    c = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    tl, tr, br, bl = c
    top = np.linalg.norm(tr - tl)
    bottom = np.linalg.norm(br - bl)
    left = np.linalg.norm(bl - tl)
    right = np.linalg.norm(br - tr)
    if min(top, bottom, left, right) < 1:
        raise ValueError("Corners are too close together")
    rx = float(width_mm) / float((top + bottom) / 2.0)
    ry = float(height_mm) / float((left + right) / 2.0)
    res = round((rx + ry) / 2.0, 5)
    return res, rx, ry


def warp_sheet(img, corners, width_mm, height_mm, mm_per_px):
    """Nan phoi canh 4 goc ve anh chu nhat width_mm x height_mm."""
    out_w = int(round(width_mm / mm_per_px))
    out_h = int(round(height_mm / mm_per_px))
    src = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    dst = np.array([[0, 0], [out_w, 0], [out_w, out_h], [0, out_h]],
                   dtype=np.float32)
    m = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, m, (out_w, out_h),
                               flags=cv2.INTER_AREA if mm_per_px > 0.3
                               else cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)


def rotate_corners(corners, times=1):
    """Xoay thu tu 4 goc 90 do (dung khi muon xoay huong tam truoc khi nan)."""
    c = list(np.asarray(corners, dtype=np.float32).reshape(4, 2))
    for _ in range(times % 4):
        c = c[1:] + c[:1]
    return np.array(c, dtype=np.float32)


# ---------------------------------------------------------------------------
# Phan doan go / khong phai go
# ---------------------------------------------------------------------------

SEG_METHODS = {
    "combo": "Combined (low saturation + bright)",
    "sat": "HSV saturation (inverted)",
    "light": "Lightness L",
    "lab_b": "Lab b* (yellowness)",
}


def wood_score(warped, method="combo", blur_px=3):
    """
    Tra ve anh xam uint8: gia tri cang cao cang giong go.
    Go plywood: sang, hoi vang, bao hoa thap. Tham cat xanh: bao hoa cao,
    b* thap. Bong trong lo: toi.
    """
    img = warped
    if blur_px and blur_px > 1:
        k = int(blur_px) | 1
        img = cv2.GaussianBlur(img, (k, k), 0)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    L, a, b = lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]
    if method == "lab_b":
        s = b - a * 0.5
    elif method == "light":
        s = L
    elif method == "sat":
        s = 255.0 - hsv[:, :, 1]
    else:
        # ket hop: go vua sang vua it bao hoa (tham xanh bao hoa cao,
        # bong trong lo thi toi)
        s = 0.6 * (255.0 - hsv[:, :, 1]) + 0.4 * L
    s = cv2.normalize(s, None, 0, 255, cv2.NORM_MINMAX)
    return s.astype(np.uint8)


def otsu_threshold(score):
    t, _ = cv2.threshold(score, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return int(t)


def kmeans_mask(warped):
    """Phan cum 2 nhom tren Lab, nhom co L trung binh cao hon = go."""
    lab = cv2.cvtColor(cv2.GaussianBlur(warped, (3, 3), 0), cv2.COLOR_BGR2LAB)
    data = lab.reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(data, 2, None, crit, 3,
                                    cv2.KMEANS_PP_CENTERS)
    wood = int(np.argmax(centers[:, 0] + (centers[:, 2] - 128)))
    return ((labels.reshape(lab.shape[:2]) == wood) * 255).astype(np.uint8)


def mm_to_px(mm, mm_per_px):
    return int(round(float(mm) / float(mm_per_px)))


def cleanup_mask(mask, mm_per_px, open_mm=0.5, close_mm=0.0,
                 min_wood_mm2=4.0, min_hole_mm2=4.0):
    """
    Lam sach mask: mo/dong hinh thai, bo dom go nho va lo nho.
    Chu y: dong (close) co the lap mat cac duong cat manh (kerf) chua tach
    roi vat lieu, nen mac dinh close_mm = 0.
    """
    m = mask.copy()
    ko = mm_to_px(open_mm, mm_per_px)
    kc = mm_to_px(close_mm, mm_per_px)
    if ko >= 1:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ko + 1,) * 2)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    if kc >= 1:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * kc + 1,) * 2)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    px_area = mm_per_px * mm_per_px
    if min_wood_mm2 > 0:
        m = _remove_small(m, min_wood_mm2 / px_area)
    if min_hole_mm2 > 0:
        m = 255 - _remove_small(255 - m, min_hole_mm2 / px_area)
    return m


def _remove_small(mask, min_area_px):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8), connectivity=8)
    keep = np.zeros(n, dtype=bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area_px
    return (keep[lab] * 255).astype(np.uint8)


def cut_border(mask, border_mm, mm_per_px):
    """Coi mot dai border_mm quanh mep tam la da cat (mep tam thuong xau)."""
    b = mm_to_px(border_mm, mm_per_px)
    if b <= 0:
        return mask
    m = mask.copy()
    m[:b, :] = 0
    m[-b:, :] = 0
    m[:, :b] = 0
    m[:, -b:] = 0
    return m


def apply_edits(mask, edits):
    """edits: int8, +1 = to giu go, -1 = to cat, 0 = theo mask tu dong."""
    m = mask.copy()
    if edits is not None:
        m[edits > 0] = 255
        m[edits < 0] = 0
    return m


def erode_margin(mask, margin_mm, mm_per_px):
    """
    Co vung go vao margin_mm (khoang an toan voi mep chay, kerf).
    Dung distance transform de co dung theo khoang cach Euclid.
    Mep anh (ngoai tam) cung duoc coi la da cat.
    """
    if margin_mm <= 0:
        return mask.copy()
    padded = cv2.copyMakeBorder((mask > 0).astype(np.uint8), 1, 1, 1, 1,
                                cv2.BORDER_CONSTANT, value=0)
    dist = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[1:-1, 1:-1]
    # dist tinh tu tam pixel den tam pixel 0 gan nhat (don vi pixel);
    # pixel giu lai neu canh gan nhat cua no cach mep >= margin
    return ((dist * mm_per_px - 0.5 * mm_per_px >= margin_mm - 1e-9)
            * 255).astype(np.uint8)


def auto_mask(warped, mm_per_px, method="combo", threshold=None,
              open_mm=0.5, close_mm=0.0, min_wood_mm2=4.0, min_hole_mm2=4.0,
              border_mm=0.0):
    """Pipeline tu dong (dung cho test khong GUI). Tra ve (mask, threshold)."""
    if method == "kmeans":
        raw = kmeans_mask(warped)
        threshold = -1
    else:
        score = wood_score(warped, method,
                           blur_px=max(1, mm_to_px(1.0, mm_per_px)))
        if threshold is None:
            threshold = otsu_threshold(score)
        raw = ((score > threshold) * 255).astype(np.uint8)
    m = cleanup_mask(raw, mm_per_px, open_mm, close_mm,
                     min_wood_mm2, min_hole_mm2)
    m = cut_border(m, border_mm, mm_per_px)
    return m, threshold


# ---------------------------------------------------------------------------
# Hien thi
# ---------------------------------------------------------------------------

def draw_mm_grid(img, mm_per_px, step_mm=10, color=(255, 0, 255),
                 label_every=50):
    """Ve luoi mm len anh da nan (goc toa do duoi-trai) de doi chieu luoi
    1cm cua tham cat."""
    out = img.copy()
    h, w = out.shape[:2]
    n = int(w * mm_per_px // step_mm) + 1
    for i in range(n):
        x = int(round(i * step_mm / mm_per_px))
        thick = 2 if (i * step_mm) % label_every == 0 else 1
        cv2.line(out, (x, 0), (x, h - 1), color, thick)
    n = int(h * mm_per_px // step_mm) + 1
    for i in range(n):
        y = int(round(h - i * step_mm / mm_per_px))
        thick = 2 if (i * step_mm) % label_every == 0 else 1
        cv2.line(out, (0, y), (w - 1, y), color, thick)
    return out


def overlay_mask(img, mask, alpha=0.45, cut_color=(0, 0, 255),
                 extra=None, extra_color=(0, 165, 255)):
    """To mau vung da cat (mask == 0) len anh; extra: vung bi co do margin."""
    out = img.copy()
    col = np.zeros_like(out)
    col[:] = cut_color
    sel = mask == 0
    out[sel] = (out[sel] * (1 - alpha) + col[sel] * alpha).astype(np.uint8)
    if extra is not None:
        col[:] = extra_color
        sel = extra > 0
        out[sel] = (out[sel] * (1 - alpha) + col[sel] * alpha).astype(np.uint8)
    return out


# ---------------------------------------------------------------------------
# Luu / doc file mask
# ---------------------------------------------------------------------------

def wood_area_stats(mask, mm_per_px):
    """Dien tich go (mask > 0) va ti le so voi ca tam (mm2, 0..1)."""
    m = np.asarray(mask) > 0
    a = float(mm_per_px) ** 2
    wood, sheet = float(m.sum()) * a, float(m.size) * a
    return {"wood_area_mm2": round(wood, 1), "sheet_area_mm2": round(sheet, 1),
            "wood_ratio": round(wood / sheet, 5) if sheet else 0.0}


def save_mask_file(png_path, mask, width_mm, height_mm, mm_per_px,
                   margin_mm, source="", raw_mask=None, warped=None,
                   corners=None, extra=None):
    """
    Ghi:
      <ten>.png         mask cuoi (da co margin), 255 = go, 0 = cat
      <ten>.json        thong tin kich thuoc
      <ten>_raw.png     mask truoc khi co margin (de mo lai sua tiep)
      <ten>_warped.png  anh da nan (de mo lai sua tiep)
    """
    base = os.path.splitext(png_path)[0]
    imwrite_unicode(base + ".png", mask)
    meta = {
        "width_mm": float(width_mm),
        "height_mm": float(height_mm),
        "mm_per_px": float(mm_per_px),
        "margin_mm": float(margin_mm),
        "source": source,
        "mask_file": os.path.basename(base + ".png"),
        "px_per_mm": round(1.0 / float(mm_per_px), 5),
    }
    meta.update(wood_area_stats(mask, mm_per_px))
    if raw_mask is not None:
        rs = wood_area_stats(raw_mask, mm_per_px)
        meta["wood_area_raw_mm2"] = rs["wood_area_mm2"]
        meta["wood_ratio_raw"] = rs["wood_ratio"]
    meta.update({
        "convention": "255 = wood remaining, 0 = cut; row 0 = top edge; "
                      "DSL origin (0,0) = bottom-left corner, y up",
    })
    if raw_mask is not None:
        imwrite_unicode(base + "_raw.png", raw_mask)
        meta["raw_mask_file"] = os.path.basename(base + "_raw.png")
    if warped is not None:
        imwrite_unicode(base + "_warped.png", warped)
        meta["warped_file"] = os.path.basename(base + "_warped.png")
    if corners is not None:
        meta["corners_px"] = np.asarray(corners).reshape(4, 2).tolist()
    if extra:
        meta.update(extra)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return base + ".png", base + ".json"


def load_mask_file(path):
    """
    path co the la .png hoac .json. Tra ve (mask, meta, folder).
    mask la uint8 0/255.
    """
    base = os.path.splitext(path)[0]
    json_path = base + ".json"
    meta = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    folder = os.path.dirname(os.path.abspath(json_path))
    png = os.path.join(folder, meta.get("mask_file",
                                        os.path.basename(base + ".png")))
    mask = imread_unicode(png, cv2.IMREAD_GRAYSCALE)
    mask = ((mask > 127) * 255).astype(np.uint8)
    if "mm_per_px" not in meta:
        raise ValueError("Missing JSON sidecar (mm_per_px) for mask: %s" % png)
    meta.setdefault("height_mm", mask.shape[0] * meta["mm_per_px"])
    meta.setdefault("width_mm", mask.shape[1] * meta["mm_per_px"])
    return mask, meta, folder


# ---------------------------------------------------------------------------
# Kiem tra kich thuoc bang luoi tham cat (nhin qua cac lo)
# ---------------------------------------------------------------------------

def estimate_grid_period_mm(warped, mask, mm_per_px, min_mm=1.5, max_mm=30.0):
    """
    Uoc luong chu ky luoi cua tham cat nhin thay qua cac lo (vung mask == 0),
    theo truc x va y, don vi mm theo kich thuoc tam dang nhap.
    Neu kich thuoc nhap dung va luoi tham la 10mm thi ket qua ~10mm.
    Luu y: tham nam thap hon mat go 1 do day van, nen sai so vai %.
    Tra ve (period_x_mm, period_y_mm), co the None neu khong do duoc.
    """
    L = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    # Bo vung sat mep lo (bong, mep chay) de khong anh huong pho
    e = max(1, mm_to_px(2.0, mm_per_px))
    hole = cv2.erode((mask == 0).astype(np.uint8),
                     np.ones((2 * e + 1, 2 * e + 1), np.uint8)) > 0
    if hole.sum() < 1000:
        return None, None
    # Chi giu chi tiet nho (duong luoi): tru nen mo
    k = mm_to_px(max_mm, mm_per_px) | 1
    hp = L - cv2.blur(L, (k, k))
    hp[~hole] = np.nan
    res = []
    for axis in (0, 1):  # axis 0 -> profile theo x, 1 -> theo y
        cnt = hole.sum(axis=axis)
        # Dung trung vi: duong luoi chinh lien mach nen trung vi cao, con
        # cac dau + nho (moc 5mm) chi chiem it pixel nen bi loai
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                prof = np.nanmedian(hp, axis=axis)
        prof = np.where(cnt >= 10, prof, 0)
        prof = np.nan_to_num(prof - np.nanmean(prof[cnt >= 10]))
        prof[cnt < 10] = 0
        n = len(prof)
        nfft = 1 << int(np.ceil(np.log2(n * 8)))
        spec = np.abs(np.fft.rfft(prof * np.hanning(n), nfft))
        freqs = np.fft.rfftfreq(nfft, d=mm_per_px)  # chu ky / mm
        ok = (freqs > 1.0 / max_mm) & (freqs < 1.0 / min_mm)
        if not ok.any():
            res.append(None)
            continue
        sp_ok = np.where(ok, spec, 0)
        idx = int(np.argmax(sp_ok))
        period = 1.0 / freqs[idx]
        # Tham thuong co vach chia nua o (5mm) => dinh manh nhat co the la
        # nua chu ky luoi chinh. Neu o chu ky gap doi cung co dinh du manh
        # thi lay chu ky gap doi (luoi chinh)
        f2 = freqs[idx] / 2.0
        win = (freqs > f2 * 0.95) & (freqs < f2 * 1.05)
        if win.any() and 2 * period <= max_mm:
            j = int(np.argmax(np.where(win, spec, 0)))
            if spec[j] >= 0.3 * spec[idx]:
                period = 1.0 / freqs[j]
        res.append(float(period))
    return res[0], res[1]


# ---------------------------------------------------------------------------
# Thu muc output: plywood_scan/output/<ten>/
# ---------------------------------------------------------------------------

MASK_BASENAME = "mask"   # => mask.png, mask.json, mask_raw.png, mask_warped.png


def default_output_root():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def sanitize_name(name):
    """Bo ky tu khong hop le tren Windows, tra ve ten thu muc an toan."""
    import re
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name)).strip().rstrip(".")
    return name or "scan"


def unique_dir(root, name):
    """Tra ve <root>/<name>, hoac <name>_2, _3... neu da ton tai."""
    base = os.path.join(root, name)
    if not os.path.exists(base):
        return base
    k = 2
    while os.path.exists("%s_%d" % (base, k)):
        k += 1
    return "%s_%d" % (base, k)


def output_dir_has_files(path):
    return os.path.isdir(path) and any(os.scandir(path))
