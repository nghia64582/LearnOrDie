"""
Diem can chinh (alignment marks) va gcode can chinh.

Quy trinh: user chon 2 diem tren anh tam (toa do tam, mm, goc (0,0) = goc
duoi-trai, x sang phai, y huong len - cung he toa do voi DSL / gcode cat).
Gcode can chinh ve dau "+" tai moi diem voi cong suat thap. Dat tam len may,
chay gcode, xe dich tam cho toi khi dau + trung voi 2 diem da danh dau tren
tam => tam nam dung vi tri nhu luc chup, roi moi chay gcode cat.

Offset: toa do may = toa do tam + offset (mac dinh 0, 0). Gcode can chinh va
DSL xuat tu strip_packer dung CHUNG offset nay.

Quy uoc gcode giong engraver_ctrl/tab_designer.py (generate_bounds_gcode):
G21, G90, moi doan: G0 toi diem dau, M3 S<power>, G1 ... F<feed>, M5.
Ket thuc: M5 va G0 ve goc (giong tab Machine tu them M5 + G0 X0 Y0).
"""
import math
import os
import re

ALIGN_DEFAULTS = {
    "cross_mm": 5.0,       # do dai moi net cua dau +
    "power": 100,          # S, thang 0-1000 (100 = 10%)
    "feed": 200.0,         # mm/phut
    "offset_mm": [0.0, 0.0],
    "return_home": True,   # ve (offset) 0,0 sau khi xong
}

ALIGN_GCODE_FILE = "alignment.gcode"


def distance(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def alignment_gcode(points_mm, cross_mm=5.0, power=100, feed=200.0,
                    offset_mm=(0.0, 0.0), return_home=True):
    """
    Tao list dong gcode ve dau + tai moi diem (toa do tam, mm).
    Moi dau + gom 2 net vuong goc dai cross_mm, tam tai diem.
    Laser tat (M5) khi di chuyen G0 giua cac net.
    """
    points_mm = [p for p in (points_mm or []) if p is not None]
    if not points_mm:
        raise ValueError("No alignment points")
    if cross_mm <= 0:
        raise ValueError("Cross size must be > 0")
    if not (0 <= power <= 1000):
        raise ValueError("Power must be between 0 and 1000")
    if feed <= 0:
        raise ValueError("Feed must be > 0")
    ox, oy = float(offset_mm[0]), float(offset_mm[1])
    half = cross_mm / 2.0
    p = int(round(power))
    # Khong ghi dong chu thich (;) de giong gcode cua tab_designer va an
    # toan voi moi trinh gui gcode
    lines = ["G21", "G90", "M5"]
    for x, y in points_mm:
        cx, cy = x + ox, y + oy
        # Net ngang cua dau +
        lines.append(f"G0 X{cx - half:.3f} Y{cy:.3f}")
        lines.append(f"M3 S{p}")
        lines.append(f"G1 X{cx + half:.3f} Y{cy:.3f} F{feed:g}")
        lines.append("M5")
        # Net doc cua dau +
        lines.append(f"G0 X{cx:.3f} Y{cy - half:.3f}")
        lines.append(f"M3 S{p}")
        lines.append(f"G1 X{cx:.3f} Y{cy + half:.3f} F{feed:g}")
        lines.append("M5")
    if return_home:
        lines.append(f"G0 X{ox:.3f} Y{oy:.3f}")
    lines.append("M5")
    return lines


def write_alignment_gcode(folder, align, filename=ALIGN_GCODE_FILE):
    """Ghi gcode can chinh vao folder theo dict align (nhu trong JSON)."""
    lines = alignment_gcode(align["points_mm"],
                            align.get("cross_mm", 5.0),
                            align.get("power", 100),
                            align.get("feed", 200.0),
                            align.get("offset_mm", (0.0, 0.0)),
                            align.get("return_home", True))
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def simulate_gcode(lines):
    """
    Mo phong don gian (de test): tra ve dict
      burns: list (x1, y1, x2, y2, S, F) cac doan G1 khi laser bat
      rapids_on: so lenh G0 khi laser dang bat (phai = 0)
      g1_off: so lenh G1 khi laser tat
      laser_on_at_end: bool
    """
    x = y = 0.0
    on = False
    s = 0
    f = None
    burns, rapids_on, g1_off = [], 0, 0
    for raw in lines:
        line = raw.split(";")[0].strip().upper()
        if not line:
            continue
        words = dict((m.group(1), float(m.group(2))) for m in
                     re.finditer(r"([A-Z])([-+]?[0-9]*\.?[0-9]+)", line))
        if line.startswith("M3") or line.startswith("M4"):
            on = True
            s = int(words.get("S", s))
        elif line.startswith("M5"):
            on = False
        elif line.startswith("G0") or line.startswith("G1"):
            nx, ny = words.get("X", x), words.get("Y", y)
            if "F" in words:
                f = words["F"]
            if line.startswith("G0"):
                if on:
                    rapids_on += 1
            else:
                if on:
                    burns.append((x, y, nx, ny, s, f))
                else:
                    g1_off += 1
            x, y = nx, ny
    return {"burns": burns, "rapids_on": rapids_on, "g1_off": g1_off,
            "laser_on_at_end": on, "end_pos": (x, y)}


def cut_plan_path():
    """Duong dan engraver_ctrl/cut_plan.gcode (file tab Machine doc va chay)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "engraver_ctrl",
                        "cut_plan.gcode")
