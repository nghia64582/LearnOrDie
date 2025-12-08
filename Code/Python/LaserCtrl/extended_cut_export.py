from cut_plan_builder import *
import math

def export_gcode_extended(
    plan: CutPlan,
    filename: str,
    feedrate: int = 280,
    power: int = 1000,
):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("; GCODE generated from CutPlan\n")
        f.write("G21 ; set mm mode\n")
        f.write("G90 ; absolute positioning\n")
        f.write("G0 X0 Y0\n\n")

        # ---- CẮT ĐƯỜNG THẲNG ----
        for (start_x, y, length_of_cut) in plan.cuts:
            end_x = start_x + length_of_cut

            f.write(f"G0 X{start_x:.3f} Y{y:.3f}\n")
            f.write(f"M3 S{power}\n")
            f.write(f"G1 X{end_x:.3f} Y{y:.3f} F{feedrate}\n")
            f.write("M5\n\n")

        # ---- KHOAN LỖ ----
        for (center_x, center_y) in plan.holes:
            # bắt đầu ở điểm bên phải (cx + R, cy)
            x_start = center_x + plan.radius
            y_start = center_y

            # move to start on circle perimeter
            f.write(f"G0 X{x_start:.3f} Y{y_start:.3f}\n")
            f.write(f"M3 S{power}\n")

            # 1st half-circle: từ (cx+R, cy) -> (cx-R, cy)
            # I = center_x - x_start = -plan.radius
            f.write(f"G2 X{center_x - plan.radius:.3f} Y{center_y:.3f} I{-plan.radius:.3f} J0.000 F{feedrate}\n")

            # 2nd half-circle: từ (cx-R, cy) -> (cx+R, cy)
            # Now start is (cx-R,cy), so I = center_x - (cx-R) = +plan.radius
            f.write(f"G2 X{x_start:.3f} Y{y_start:.3f} I{plan.radius:.3f} J0.000 F{feedrate}\n")

            f.write("M5\n\n")

        # ---- CẮT CUNG BO GÓC ----
        for (center_x, center_y, is_up) in plan.arches:
            # giả sử dùng cung 180° với bán kính = radius
            # điểm bắt đầu là bên trái: center_x - radius
            start_x = center_x - plan.stick_width / 2
            end_x = center_x + plan.stick_width / 2
            y = center_y

            f.write(f"G0 X{start_x:.3f} Y{y:.3f}\n")
            f.write(f"M3 S{power}\n")

            # G2 CW hoặc G3 CCW dựa theo hướng
            if is_up:
                # cung hướng lên: CCW (G3)
                f.write(f"G3 X{end_x:.3f} Y{y:.3f} I{plan.stick_width / 2:.3f} J0.000 F{feedrate}\n")
            else:
                # cung hướng xuống: CW (G2)
                f.write(f"G2 X{end_x:.3f} Y{y:.3f} I{plan.stick_width / 2:.3f} J0.000 F{feedrate}\n")

            f.write("M5\n\n")

        f.write("G0 X0 Y0\n")
        f.write("; END\n")
