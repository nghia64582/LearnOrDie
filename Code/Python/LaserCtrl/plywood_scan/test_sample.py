"""
Test khong GUI tren anh mau sample/plywood_01.png.

Chay:  python test_sample.py [thu_muc_output]

Kich thuoc tam trong anh mau: 306 x 460 mm (kich thuoc dien hinh cua tam,
moi tam co the khac - khi dung that hay do bang thuoc). Do phan giai mm/px
tinh tu dong tu 4 goc (giong scan_app).
"""
import os
import sys
import time

import numpy as np

import align_core as ac
import scan_core as sc
from pack_core import (pack_strips, pack_pieces, parse_lengths, verify_strips,
                       strips_to_dsl, parse_dsl_strips, render_result)

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "sample", "plywood_01.png")
# Goc uoc luong bang tay tren anh mau (TL, TR, BR, BL), pixel
CORNERS = [[6, 165], [569, 166], [579, 1019], [10, 1022]]
W_MM, H_MM, MARGIN = 306.0, 460.0, 1.0
# 2 diem can chinh mau (mm, toa do tam)
ALIGN_PTS = [[12.5, 20.0], [290.0, 447.25]]


def check_alignment(meta, folder):
    """Doc gcode can chinh, mo phong va kiem tra dau + dung vi tri / thong so."""
    al = meta["alignment"]
    assert al["points_mm"] == ALIGN_PTS, al["points_mm"]
    with open(os.path.join(folder, al["gcode_file"])) as f:
        lines = f.read().splitlines()
    sim = ac.simulate_gcode(lines)
    ok = (lines[:2] == ["G21", "G90"] and sim["rapids_on"] == 0
          and sim["g1_off"] == 0 and not sim["laser_on_at_end"]
          and lines[-1] == "M5" and sim["end_pos"] == (0.0, 0.0)
          and len(sim["burns"]) == 2 * len(ALIGN_PTS))
    for k, (px_, py_) in enumerate(ALIGN_PTS):
        hseg, vseg = sim["burns"][2 * k], sim["burns"][2 * k + 1]
        for (x1, y1, x2, y2, S, F), horiz in ((hseg, True), (vseg, False)):
            L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ok &= abs(L - 5.0) < 1e-6 and S == 100 and F == 200
            ok &= abs(mx - px_) < 1e-6 and abs(my - py_) < 1e-6
            ok &= (abs(y1 - y2) < 1e-9) if horiz else (abs(x1 - x2) < 1e-9)
    d = ac.distance(*ALIGN_PTS)
    print("Gcode can chinh: %d dong, %d net, P1-P2 = %.2f mm, %s" % (
        len(lines), len(sim["burns"]), d, "OK" if ok else "LOI"))
    # Offset: toa do may = toa do tam + offset
    lo = ac.alignment_gcode(ALIGN_PTS, offset_mm=(10, -5))
    so = ac.simulate_gcode(lo)
    ok_off = abs((so["burns"][0][0] + so["burns"][0][2]) / 2 - 22.5) < 1e-6 \
        and abs(so["burns"][0][1] - 15.0) < 1e-6 and so["end_pos"] == (10, -5)
    print("Offset (10, -5):", "OK" if ok_off else "LOI")
    return bool(ok and ok_off)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    img = sc.imread_unicode(SAMPLE)
    auto = sc.detect_sheet_corners(img)
    print("Goc tu dong:", np.round(auto, 1).tolist())
    print("Goc dung de test:", CORNERS)
    RES, rx, ry = sc.auto_resolution(CORNERS, W_MM, H_MM)
    print("Do phan giai tu dong: %.4f mm/px (%.3f px/mm), X %.4f, Y %.4f"
          % (RES, 1 / RES, rx, ry))
    warped = sc.warp_sheet(img, CORNERS, W_MM, H_MM, RES)
    raw, thr = sc.auto_mask(warped, RES)
    px, py = sc.estimate_grid_period_mm(warped, raw, RES)
    print("Nguong Otsu: %d, luoi tham do duoc: %.2f x %.2f mm" % (thr, px, py))
    final = sc.erode_margin(raw, MARGIN, RES)
    # Luu giong scan_app: <out_dir>/<ten anh>/mask.* + alignment.gcode
    folder = os.path.join(out_dir, sc.sanitize_name(
        os.path.splitext(os.path.basename(SAMPLE))[0]))
    os.makedirs(folder, exist_ok=True)
    align = dict(ac.ALIGN_DEFAULTS, points_mm=ALIGN_PTS)
    gpath = ac.write_alignment_gcode(folder, align)
    align["gcode_file"] = os.path.basename(gpath)
    sc.save_mask_file(os.path.join(folder, sc.MASK_BASENAME + ".png"), final,
                      W_MM, H_MM, RES, MARGIN, source=SAMPLE, raw_mask=raw,
                      warped=warped, corners=CORNERS,
                      extra={"mm_per_px_mode": "auto", "alignment": align})
    print("Da luu vao", folder, sorted(os.listdir(folder)))
    sc.imwrite_unicode(os.path.join(out_dir, "warped_grid.png"),
                       sc.draw_mm_grid(warped, RES))
    sc.imwrite_unicode(os.path.join(out_dir, "mask_overlay.png"),
                       sc.overlay_mask(warped, raw, 0.5,
                                       extra=((raw > 0) & (final == 0))
                                       .astype(np.uint8)))
    # Doc lai tu file nhu tool 2
    mask, meta, _ = sc.load_mask_file(os.path.join(folder, "mask.json"))
    assert mask.shape == (int(round(H_MM / RES)), int(round(W_MM / RES)))
    print("Anh nan: %d x %d px" % (mask.shape[1], mask.shape[0]))
    all_ok = check_alignment(meta, folder)
    print("Go con lai: %.1f%%" % (100 * (mask > 0).mean()))

    res = meta["mm_per_px"]

    def check(r, gap, label):
        """Kiem tra ket qua + doc nguoc DSL (ADD/R/END) roi kiem tra lai."""
        ok = True
        errs = verify_strips(mask, res, r["strips"], gap)
        back = parse_dsl_strips(strips_to_dsl(r["strips"]))
        errs2 = verify_strips(mask, res, back, gap)
        same = len(back) == len(r["strips"]) and all(
            abs(a[k] - b[k]) < 1e-9 and str(b["label"]) == str(a["id"])
            for a, b in zip(r["strips"], back) for k in "xywh"
            if k in a) and all(str(b["label"]) == str(a["id"])
                               for a, b in zip(r["strips"], back))
        if errs or errs2 or not same:
            ok = False
            print("   LOI %s:" % label, errs[:3], errs2[:3], "dsl_ok", same)
        return ok

    # --- Che do chinh: danh sach thanh nhap tay ---
    for text in ("80,80,100,100",
                 "100x40, 80x30; 60 60 60 30x20",     # 93 thanh, khong du cho
                 "300 300 500 120"):                   # co thanh qua dai
        L = parse_lengths(text)
        t0 = time.time()
        r = pack_pieces(mask, res, L, strip_w=10, gap=0.5)
        ok = check(r, 0.5, text)
        # do dai phai giu nguyen dung nhu nhap
        exact = all(abs(max(s["w"], s["h"]) - L[s["id"] - 1]) < 1e-9 and
                    abs(min(s["w"], s["h"]) - 10) < 1e-9 for s in r["strips"])
        ok &= exact and len(r["strips"]) + len(r["unplaced"]) == len(L)
        all_ok &= ok
        print("pieces '%s': dat %d / %d, tong %.1f mm, %.2fs, %s" % (
            text if len(text) < 30 else text[:27] + "...", r["count"], len(L),
            r["total_length"], time.time() - t0, "OK" if ok else "LOI"))
        if r["unplaced"]:
            print("   khong vua:", ", ".join("#%d(%g)" % (u["id"], u["length"])
                                         for u in r["unplaced"][:12]),
                  "..." if len(r["unplaced"]) > 12 else "")
        if text == "80,80,100,100":
            sc.imwrite_unicode(os.path.join(out_dir, "result.png"),
                               render_result(warped, mask, res, r["strips"],
                                             align_points=ALIGN_PTS))
            with open(os.path.join(out_dir, "strips_dsl.txt"), "w") as f:
                f.write("\n".join(strips_to_dsl(r["strips"])) + "\n")
        elif r["unplaced"] and r["count"] > 20:
            sc.imwrite_unicode(os.path.join(out_dir, "result_large_list.png"),
                               render_result(warped, mask, res, r["strips"]))

    # --- Che do phu: tu lap day ---
    for kw in (dict(), dict(objective="count"), dict(step=5)):
        t0 = time.time()
        r = pack_strips(mask, res, **kw)
        ok = check(r, r["params"]["gap"], str(kw))
        all_ok &= ok
        print("auto-fill %-22s %3d thanh, tong %7.1f mm, %.2fs, %s" % (
            kw or "mac dinh", r["count"], r["total_length"], time.time() - t0,
            "OK" if ok else "LOI"))
    print("Ket qua ->", out_dir, "| tat ca hop le:", all_ok)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else os.path.join(HERE, "out")))
