"""
Core geometry generator for L / T / Plus cross-section beams (stick DSL).

Sheet thickness (joint feature size) is a FIXED constant:
  TOOTH = 3mm

Flange / rail sizes come from strip_width W (default 10mm), which must
stay strictly greater than TOOTH:

  L stick: one strip of width 2W - T, split by a zigzag that alternates
    between x = W and x = W - T. The two halves fold to 90 degrees:
    each flange is W wide, and they share a T-thick corner, so the
    unfolded width is W + (W - T) = 2W - T (17mm when W=10, T=3).
    Nominal zigzag pitch = W.

  T stick: "ti" piece (W wide, with T-by-W through-slots) + "back" piece
    whose bounding box is also W: a (W - T) shank with T-wide, W-tall
    tabs that plug into ti's slots. Combined footprint = 2W.
    Nominal slot pitch = 2W.

  Plus stick: two identical W-wide pieces, each with one long slot
    (width T, spanning half the stick's length) so they cross-lap into
    a + cross-section. Combined footprint = 2W.
"""


TOOTH = 3.0          # sheet thickness / joint feature size (mm)
STRIP_WIDTH_DEFAULT = 10.0


def _require_strip_width(strip_width):
    w = float(strip_width)
    if w <= 0:
        raise ValueError("Strip width must be a positive number.")
    if w <= TOOTH:
        raise ValueError(
            f"Strip width must be greater than material thickness ({TOOTH:g} mm)."
        )
    return w


# ---------------------------------------------------------------------------
# L stick
# ---------------------------------------------------------------------------
def generate_L(length, name, x_offset=0.0, strip_width=STRIP_WIDTH_DEFAULT):
    w = _require_strip_width(strip_width)
    l_width = 2 * w - TOOTH
    zz_wide = w
    zz_narrow = w - TOOTH
    zz_pitch_nominal = w

    n_seg = max(1, round(length / zz_pitch_nominal))
    pitch = length / n_seg

    outer = [(0, 0), (0, length), (l_width, length), (l_width, 0), (0, 0)]

    zz = [(zz_wide, 0.0)]
    x = zz_wide
    for i in range(n_seg):
        y = (i + 1) * pitch
        zz.append((x, y))
        if i != n_seg - 1:
            x = zz_narrow if x == zz_wide else zz_wide
            zz.append((x, y))

    dsl = [f"ADD {_g(x_offset)} 0 {name}", _fmt_line("P", outer), _fmt_line("M", zz), "END"]
    draw = {
        "rects": [{"x": 0, "y": 0, "w": l_width, "h": length}],
        "lines": [zz],
        "polys": [],
    }
    return dsl, draw, l_width


# ---------------------------------------------------------------------------
# T stick (ti + back, nested)
# ---------------------------------------------------------------------------
def generate_T(length, name_ti, name_back, x_offset=0.0,
               strip_width=STRIP_WIDTH_DEFAULT):
    w = _require_strip_width(strip_width)
    t_ti_width = w
    t_back_width = w          # (W - T) shank + T-wide tabs
    t_slot_height = w
    t_slot_pitch_nominal = 2 * w

    n_slots = max(1, round(length / t_slot_pitch_nominal))
    pitch = length / n_slots
    centers = [pitch / 2 + k * pitch for k in range(n_slots)]

    ti_lines = [f"ADD {_g(x_offset)} 0 {name_ti}", f"R 0 0 {_g(t_ti_width)} {_g(length)}"]
    for c in centers:
        ti_lines.append(f"RC {_g(t_ti_width/2)} {_g(c)} {_g(TOOTH)} {_g(t_slot_height)}")

    back_pts = [(TOOTH, 0), (t_back_width, 0), (t_back_width, length), (TOOTH, length)]
    for c in sorted(centers, reverse=True):
        top, bot = c + t_slot_height / 2, c - t_slot_height / 2
        back_pts += [(TOOTH, top), (0, top), (0, bot), (TOOTH, bot)]
    back_closed = back_pts + [back_pts[0]]

    back_lines = [f"ADD {_g(t_ti_width)} 0 {name_back}",
                  "P " + " ".join(_g(v) for pt in back_closed for v in pt), "END"]

    dsl = ti_lines + back_lines + ["END"]

    draw = {
        "rects": [{"x": 0, "y": 0, "w": t_ti_width, "h": length}],
        "cuts": [{"x": t_ti_width / 2 - TOOTH / 2, "y": c - t_slot_height / 2,
                  "w": TOOTH, "h": t_slot_height} for c in centers],
        "polys": [{"points": back_closed, "offset": (t_ti_width, 0)}],
        "lines": [],
    }
    total_width = t_ti_width + t_back_width
    return dsl, draw, total_width


# ---------------------------------------------------------------------------
# Plus stick (two identical pieces, nested)
# ---------------------------------------------------------------------------
def generate_plus(length, name_a, name_b, x_offset=0.0,
                  strip_width=STRIP_WIDTH_DEFAULT):
    w = _require_strip_width(strip_width)
    plus_width = w

    slot_h = length / 2
    slot_c = length / 4

    def piece_lines(name, x_off):
        return [f"ADD {_g(x_off)} 0 {name}",
                f"R 0 0 {_g(plus_width)} {_g(length)}",
                f"RC {_g(plus_width/2)} {_g(slot_c)} {_g(TOOTH)} {_g(slot_h)}"]

    a_lines = piece_lines(name_a, x_offset)
    b_lines = piece_lines(name_b, plus_width)  # relative offset, nested inside `a`'s block
    dsl = a_lines + b_lines + ["END", "END"]

    draw = {
        "rects": [{"x": 0, "y": 0, "w": plus_width, "h": length}],
        "cuts": [{"x": plus_width / 2 - TOOTH / 2, "y": slot_c - slot_h / 2,
                  "w": TOOTH, "h": slot_h}],
        "polys": [{"points": [(0, 0), (plus_width, 0), (plus_width, length), (0, length), (0, 0)],
                   "offset": (plus_width, 0),
                   "cuts": [{"x": plus_width / 2 - TOOTH / 2, "y": slot_c - slot_h / 2,
                             "w": TOOTH, "h": slot_h}]}],
        "lines": [],
    }
    total_width = plus_width * 2
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
def build_sheet(n_L, n_T, n_plus, length, strip_width=STRIP_WIDTH_DEFAULT):
    dsl_all = []
    x_cursor = 0.0
    instances = []  # for canvas: {"kind","x","draw","width"}

    for i in range(1, n_L + 1):
        dsl, draw, w = generate_L(length, f"el-{i}", x_offset=x_cursor,
                                  strip_width=strip_width)
        dsl_all += dsl
        instances.append({"kind": "L", "x": x_cursor, "draw": draw, "width": w})
        x_cursor += w

    for i in range(1, n_T + 1):
        dsl, draw, w = generate_T(length, f"ti-{i}", f"back-{i}",
                                  x_offset=x_cursor, strip_width=strip_width)
        dsl_all += dsl
        instances.append({"kind": "T", "x": x_cursor, "draw": draw, "width": w})
        x_cursor += w

    for i in range(1, n_plus + 1):
        dsl, draw, w = generate_plus(length, f"plus-{i}-a", f"plus-{i}-b",
                                     x_offset=x_cursor, strip_width=strip_width)
        dsl_all += dsl
        instances.append({"kind": "P", "x": x_cursor, "draw": draw, "width": w})
        x_cursor += w

    dsl_text = "\n".join(dsl_all) + "\n"
    return dsl_text, instances, x_cursor
