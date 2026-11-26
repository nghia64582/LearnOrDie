from engraver_ctrl.cut_plan_builder import *


def _num(value):
    """Format a number, dropping a trailing .0."""
    value = float(value)
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def export_gcode_extended(
    plan: CutPlan,
    filename: str,
    feedrate: int = 250,
    power: int = 1000,
):
    sticks = getattr(plan, "sticks", None) or []
    stock = getattr(plan, "stock_length", 0)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("; GCODE generated from CutPlan\n")
        f.write(f"; sticks={len(sticks)} stock={stock:g}x{plan.stick_width:g}\n")
        f.write("G21 ; set mm mode\n")
        f.write("G90 ; absolute positioning\n")
        f.write("G0 X0 Y0\n\n")

        feed = _num(feedrate)
        pwr = _num(power)

        for (start_x, y, length_of_cut) in plan.cuts:
            end_x = start_x + length_of_cut
            f.write(f"G0 X{start_x:.3f} Y{y:.3f}\n")
            f.write(f"M3 S{pwr}\n")
            f.write(f"G1 X{end_x:.3f} Y{y:.3f} F{feed}\n")
            f.write("M5\n\n")

        for (center_x, center_y) in plan.holes:
            x_start = center_x + plan.radius
            y_start = center_y
            f.write(f"G0 X{x_start:.3f} Y{y_start:.3f}\n")
            f.write(f"M3 S{pwr}\n")
            f.write(
                f"G2 X{center_x - plan.radius:.3f} Y{center_y:.3f} "
                f"I{-plan.radius:.3f} J0.000 F{feed}\n"
            )
            f.write(
                f"G2 X{x_start:.3f} Y{y_start:.3f} "
                f"I{plan.radius:.3f} J0.000 F{feed}\n"
            )
            f.write("M5\n\n")

        # Rounded caps: radius R = W/2 + CUT_EXTRA_MARGIN, start at
        # (cx - R, cy), end at (cx + R, cy), I=R J=0. The apex stays
        # on the piece end; the arc overcuts 1 mm past each stick edge.
        # In G17 (Y up): G2 CW bulges +Y (rounded top), G3 CCW bulges
        # -Y (rounded bottom).
        cap_r = getattr(plan, "cap_radius", None) or cap_radius(plan.stick_width)
        for (center_x, center_y, bulge_up) in plan.arches:
            start_x = center_x - cap_r
            end_x = center_x + cap_r
            y = center_y
            cmd = "G2" if bulge_up else "G3"
            f.write(f"G0 X{start_x:.3f} Y{y:.3f}\n")
            f.write(f"M3 S{pwr}\n")
            f.write(
                f"{cmd} X{end_x:.3f} Y{y:.3f} "
                f"I{cap_r:.3f} J0.000 F{feed}\n"
            )
            f.write("M5\n\n")

        f.write("G0 X0 Y0\n")
        f.write("; END\n")
