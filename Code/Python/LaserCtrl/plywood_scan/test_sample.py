"""
Test khong GUI tren anh mau sample/plywood_01.png.

Chay:  python test_sample.py [thu_muc_output]

Kich thuoc tam trong anh mau la GIA DINH (300 x 450 mm, uoc luong tu luoi
1cm cua tham cat) - khi dung that hay do tam bang thuoc.
"""
import os
import sys
import time

import numpy as np

import scan_core as sc
from pack_core import pack_strips, verify_strips, strips_to_dsl, render_result

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "sample", "plywood_01.png")
# Goc uoc luong bang tay tren anh mau (TL, TR, BR, BL), pixel
CORNERS = [[6, 165], [569, 166], [579, 1019], [10, 1022]]
W_MM, H_MM, RES, MARGIN = 300.0, 450.0, 0.5, 1.0


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    img = sc.imread_unicode(SAMPLE)
    auto = sc.detect_sheet_corners(img)
    print("Goc tu dong:", np.round(auto, 1).tolist())
    print("Goc dung de test:", CORNERS)
    warped = sc.warp_sheet(img, CORNERS, W_MM, H_MM, RES)
    raw, thr = sc.auto_mask(warped, RES)
    px, py = sc.estimate_grid_period_mm(warped, raw, RES)
    print("Nguong Otsu: %d, luoi tham do duoc: %.2f x %.2f mm" % (thr, px, py))
    final = sc.erode_margin(raw, MARGIN, RES)
    sc.save_mask_file(os.path.join(out_dir, "mask.png"), final, W_MM, H_MM,
                      RES, MARGIN, source=SAMPLE, raw_mask=raw,
                      warped=warped, corners=CORNERS)
    sc.imwrite_unicode(os.path.join(out_dir, "warped_grid.png"),
                       sc.draw_mm_grid(warped, RES))
    sc.imwrite_unicode(os.path.join(out_dir, "mask_overlay.png"),
                       sc.overlay_mask(warped, raw, 0.5,
                                       extra=((raw > 0) & (final == 0))
                                       .astype(np.uint8)))
    # Doc lai tu file nhu tool 2
    mask, meta, _ = sc.load_mask_file(os.path.join(out_dir, "mask.json"))
    assert mask.shape == (int(H_MM / RES), int(W_MM / RES))
    print("Go con lai: %.1f%%" % (100 * (mask > 0).mean()))

    all_ok = True
    for kw in (dict(), dict(objective="count"), dict(orient="H"),
               dict(orient="V"), dict(step=5), dict(gap=0)):
        t0 = time.time()
        r = pack_strips(mask, meta["mm_per_px"], **kw)
        errs = verify_strips(mask, meta["mm_per_px"], r["strips"],
                             r["params"]["gap"])
        all_ok &= not errs
        print("%-22s %3d thanh, tong %7.1f mm, %-10s %.2fs, loi: %d" % (
            kw or "mac dinh", r["count"], r["total_length"], r["strategy"],
            time.time() - t0, len(errs)))
        if not kw:
            best = r
    sc.imwrite_unicode(os.path.join(out_dir, "result.png"),
                       render_result(warped, mask, RES, best["strips"]))
    with open(os.path.join(out_dir, "strips_dsl.txt"), "w") as f:
        f.write("\n".join(strips_to_dsl(best["strips"])) + "\n")
    print("Ket qua ->", out_dir, "| tat ca hop le:", all_ok)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else os.path.join(HERE, "out")))
