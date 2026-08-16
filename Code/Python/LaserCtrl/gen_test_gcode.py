OUTPUT_FILE = r"D:\Workspace\LearnOrDie\Code\Python\LaserCtrl\test_gcode.gcode"

STEP = 20.0

# Kích thước mỗi vết cắt
CUT_LENGTH = 5.0

# Khoảng cách giữa các vết cắt
SPACING = 3.0

# Công suất laser
POWER = 1000.0


def get_float(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Vui lòng nhập một số hợp lệ.")


def get_range(axis):
    print(f"\n--- Test trục {axis} ---")

    min_speed = get_float(f"{axis} min feed rate: ")
    max_speed = get_float(f"{axis} max feed rate: ")

    if min_speed > max_speed:
        min_speed, max_speed = max_speed, min_speed

    return min_speed, max_speed


def generate_speeds(min_speed, max_speed):
    speeds = []

    speed = min_speed

    while speed <= max_speed + 1e-9:
        speeds.append(speed)
        speed += STEP

    # Nếu max không nằm đúng theo STEP thì vẫn test max
    if not speeds or abs(speeds[-1] - max_speed) > 1e-9:
        speeds.append(max_speed)

    return speeds


def generate_gcode():
    x_min, x_max = get_range("X")
    y_min, y_max = get_range("Y")

    x_speeds = generate_speeds(x_min, x_max)
    y_speeds = generate_speeds(y_min, y_max)

    lines = []

    lines.append("G21")
    lines.append("G90")
    lines.append("")

    # ==========================================================
    # X AXIS TEST
    # ==========================================================

    lines.append("; ==========================================")
    lines.append("; X-AXIS CUT TEST")
    lines.append(f"; Cut length: {CUT_LENGTH} mm")
    lines.append(f"; Spacing: {SPACING} mm")
    lines.append(f"; Power: S{POWER}")
    lines.append(
        f"; Feed: {x_speeds[0]:.0f} -> {x_speeds[-1]:.0f} mm/min"
    )
    lines.append("; ==========================================")
    lines.append("")

    x_start = 5.0
    y_start = 5.0

    for i, speed in enumerate(x_speeds):
        y = y_start + i * SPACING

        lines.append(f"; X test F{speed:.0f}")
        lines.append(f"G0 X{x_start:.3f} Y{y:.3f}")
        lines.append(f"M3 S{POWER:.0f}")
        lines.append(
            f"G1 X{x_start + CUT_LENGTH:.3f} Y{y:.3f} F{speed:.1f}"
        )
        lines.append("M5")
        lines.append("")

    # ==========================================================
    # Y AXIS TEST
    # ==========================================================

    lines.append("; ==========================================")
    lines.append("; Y-AXIS CUT TEST")
    lines.append(f"; Cut length: {CUT_LENGTH} mm")
    lines.append(f"; Spacing: {SPACING} mm")
    lines.append(f"; Power: S{POWER}")
    lines.append(
        f"; Feed: {y_speeds[0]:.0f} -> {y_speeds[-1]:.0f} mm/min"
    )
    lines.append("; ==========================================")
    lines.append("")

    # Y bắt đầu từ X = 10 mm
    x_start = 10.0
    y_start = 5.0

    for i, speed in enumerate(y_speeds):
        x = x_start + i * SPACING

        lines.append(f"; Y test F{speed:.0f}")
        lines.append(f"G0 X{x:.3f} Y{y_start:.3f}")
        lines.append(f"M3 S{POWER:.0f}")
        lines.append(
            f"G1 X{x:.3f} Y{y_start + CUT_LENGTH:.3f} F{speed:.1f}"
        )
        lines.append("M5")
        lines.append("")

    lines.append("M5")
    lines.append("G0 X0.000 Y0.000")
    lines.append("")

    return "\n".join(lines)


def main():
    print("==========================================")
    print("      LASER CUT SPEED TEST GENERATOR")
    print("==========================================")

    gcode = generate_gcode()

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(gcode)

        print("\nĐã tạo G-code thành công:")
        print(OUTPUT_FILE)

    except OSError as e:
        print("\nKhông thể ghi file:")
        print(e)


if __name__ == "__main__":
    main()