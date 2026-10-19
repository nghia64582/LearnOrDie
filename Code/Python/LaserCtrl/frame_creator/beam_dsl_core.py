"""
Core geometry generator for L / T / Plus cross-section beams (stick DSL).

All widths and joint depths are FIXED constants (per spec):
  - Sheet thickness driving every joint = 3mm
  - L stick: single 17mm-wide strip, cut by a zigzag line (7mm <-> 10mm) into
    2 halves that fold/join at 90 degrees.
  - T stick: "ti" piece (10mm wide, with 3x10mm through-slots) + "back" piece
    (7mm shank with 3mm-wide, 10mm-tall tabs that plug into ti's slots).
    Combined sheet footprint width = 10 + 10 = 20mm.
  - Plus stick: two identical 10mm-wide pieces, each with ONE long slot
    (width 3mm, spanning half the stick's length) so they cross-lap into a
    + cross-section. Combined sheet footprint width = 10 + 10 = 20mm.
"""

import math

TOOTH = 3.0          # sheet thickness / joint feature size (mm)
L_WIDTH = 17.0
T_TI_WIDTH = 10.0
T_BACK_WIDTH = 10.0   # bounding box width of the back comb (shank 7 + tab 3)
T_SLOT_HEIGHT = 10.0
T_SLOT_PITCH_NOMINAL = 20.0
L_ZIGZAG_PITCH_NOMINAL = 10.0
PLUS_WIDTH = 10.0


# ---------------------------------------------------------------------------
# L stick
# ---------------------------------------------------------------------------
def generate_L(length, name, x_offset=0.0):
    n_seg = max(1, round(length / L_ZIGZAG_PITCH_NOMINAL))
    pitch = length / n_seg

    outer = [(0, 0), (0, length), (L_WIDTH, length), (L_WIDTH, 0), (0, 0)]

    zz = [(10.0, 0.0)]
    x = 10.0
    for i in range(n_seg):
        y = (i + 1) * pitch
        zz.append((x, y))
        if i != n_seg - 1:
            x = 7.0 if x == 10.0 else 10.0
            zz.append((x, y))

    dsl = [f"ADD {_g(x_offset)} 0 {name}", _fmt_line("P", outer), _fmt_line("M", zz), "END"]
    draw = {
        "rects": [{"x": 0, "y": 0, "w": L_WIDTH, "h": length}],
        "lines": [zz],
        "polys": [],
    }
    return dsl, draw, L_WIDTH


# ---------------------------------------------------------------------------
# T stick (ti + back, nested)
# ---------------------------------------------------------------------------
def generate_T(length, name_ti, name_back, x_offset=0.0):
    n_slots = max(1, round(length / T_SLOT_PITCH_NOMINAL))
    pitch = length / n_slots
    centers = [pitch / 2 + k * pitch for k in range(n_slots)]

    ti_lines = [f"ADD {_g(x_offset)} 0 {name_ti}", f"R 0 0 {_g(T_TI_WIDTH)} {_g(length)}"]
    for c in centers:
        ti_lines.append(f"RC {_g(T_TI_WIDTH/2)} {_g(c)} {_g(TOOTH)} {_g(T_SLOT_HEIGHT)}")

    back_pts = [(TOOTH, 0), (T_BACK_WIDTH, 0), (T_BACK_WIDTH, length), (TOOTH, length)]
    for c in sorted(centers, reverse=True):
        top, bot = c + T_SLOT_HEIGHT / 2, c - T_SLOT_HEIGHT / 2
        back_pts += [(TOOTH, top), (0, top), (0, bot), (TOOTH, bot)]
    back_closed = back_pts + [back_pts[0]]

    back_lines = [f"ADD {_g(T_TI_WIDTH)} 0 {name_back}", "P " + " ".join(_g(v) for pt in back_closed for v in pt), "END"]

    dsl = ti_lines + back_lines + ["END"]

    draw = {
        "rects": [{"x": 0, "y": 0, "w": T_TI_WIDTH, "h": length}],
        "cuts": [{"x": T_TI_WIDTH / 2 - TOOTH / 2, "y": c - T_SLOT_HEIGHT / 2,
                  "w": TOOTH, "h": T_SLOT_HEIGHT} for c in centers],
        "polys": [{"points": back_closed, "offset": (T_TI_WIDTH, 0)}],
        "lines": [],
    }
    total_width = T_TI_WIDTH + T_BACK_WIDTH
    return dsl, draw, total_width


# ---------------------------------------------------------------------------
# Plus stick (two identical pieces, nested)
# ---------------------------------------------------------------------------
def generate_plus(length, name_a, name_b, x_offset=0.0):
    slot_h = length / 2
    slot_c = length / 4

    def piece_lines(name, x_off):
        return [f"ADD {_g(x_off)} 0 {name}",
                f"R 0 0 {_g(PLUS_WIDTH)} {_g(length)}",
                f"RC {_g(PLUS_WIDTH/2)} {_g(slot_c)} {_g(TOOTH)} {_g(slot_h)}"]

    a_lines = piece_lines(name_a, x_offset)
    b_lines = piece_lines(name_b, PLUS_WIDTH)  # relative offset, nested inside `a`'s block
    dsl = a_lines + b_lines + ["END", "END"]

    draw = {
        "rects": [{"x": 0, "y": 0, "w": PLUS_WIDTH, "h": length}],
        "cuts": [{"x": PLUS_WIDTH / 2 - TOOTH / 2, "y": slot_c - slot_h / 2,
                  "w": TOOTH, "h": slot_h}],
        "polys": [{"points": [(0, 0), (PLUS_WIDTH, 0), (PLUS_WIDTH, length), (0, length), (0, 0)],
                   "offset": (PLUS_WIDTH, 0),
                   "cuts": [{"x": PLUS_WIDTH / 2 - TOOTH / 2, "y": slot_c - slot_h / 2,
                             "w": TOOTH, "h": slot_h}]}],
        "lines": [],
    }
    total_width = PLUS_WIDTH * 2
    return dsl, draw, total_width


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _g(v):
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _fmt_line(cmd, points):
    return cmd + " " + " ".join(_g(v) for pt in points for v in pt)


# ---------------------------------------------------------------------------
# Full sheet assembler
# ---------------------------------------------------------------------------
def build_sheet(n_L, n_T, n_plus, length):
    dsl_all = []
    x_cursor = 0.0
    instances = []  # for canvas: {"kind","x","draw","width"}

    for i in range(1, n_L + 1):
        dsl, draw, w = generate_L(length, f"el-{i}", x_offset=x_cursor)
        dsl_all += dsl
        instances.append({"kind": "L", "x": x_cursor, "draw": draw, "width": w})
        x_cursor += w

    for i in range(1, n_T + 1):
        dsl, draw, w = generate_T(length, f"ti-{i}", f"back-{i}", x_offset=x_cursor)
        dsl_all += dsl
        instances.append({"kind": "T", "x": x_cursor, "draw": draw, "width": w})
        x_cursor += w

    for i in range(1, n_plus + 1):
        dsl, draw, w = generate_plus(length, f"plus-{i}-a", f"plus-{i}-b", x_offset=x_cursor)
        dsl_all += dsl
        instances.append({"kind": "P", "x": x_cursor, "draw": draw, "width": w})
        x_cursor += w

    dsl_text = "\n".join(dsl_all) + "\n"
    return dsl_text, instances, x_cursor