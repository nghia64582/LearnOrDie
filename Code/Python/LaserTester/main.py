import tkinter as tk
from tkinter import messagebox

# ------- DPI FIX -------
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()
# -----------------------
SIZE = 10.0
SPACING = SIZE * 1.2

LASER_POWER = 1000


def generate_square(x, y, speed, passes):
    lines = []

    for _ in range(passes):
        lines.append(f"G0 X{x:.3f} Y{y:.3f}")
        lines.append(f"M3 S{LASER_POWER}")

        lines.append(f"G1 X{x + SIZE:.3f} Y{y:.3f} F{speed}")
        lines.append(f"G1 X{x + SIZE:.3f} Y{y + SIZE:.3f}")
        lines.append(f"G1 X{x:.3f} Y{y + SIZE:.3f}")
        lines.append(f"G1 X{x:.3f} Y{y:.3f}")

        lines.append("M5")

    return lines


def generate_circle(x, y, speed, passes):
    lines = []

    r = SIZE / 2

    center_x = x + r
    center_y = y + r

    for _ in range(passes):
        lines.append(f"G0 X{center_x + r:.3f} Y{center_y:.3f}")
        lines.append(f"M3 S{LASER_POWER}")

        # Full circle using two half arcs
        lines.append(
            f"G2 X{center_x - r:.3f} Y{center_y:.3f} "
            f"I{-r:.3f} J0 F{speed}"
        )

        lines.append(
            f"G2 X{center_x + r:.3f} Y{center_y:.3f} "
            f"I{r:.3f} J0"
        )

        lines.append("M5")

    return lines


def generate_gcode():
    text = input_box.get("1.0", tk.END).strip()

    if not text:
        messagebox.showerror("Error", "Input is empty")
        return

    lines = []

    # Header
    lines.append("G21")      # mm mode
    lines.append("G90")      # absolute mode
    lines.append("M5")       # laser off

    entries = text.splitlines()

    for i, line in enumerate(entries):
        parts = line.strip().split()

        if len(parts) != 3:
            continue

        shape = parts[0].upper()

        try:
            speed = float(parts[1])
            passes = int(parts[2])
        except:
            continue

        x = i * SPACING
        y = 0

        if shape == "S":
            lines.extend(generate_square(x, y, speed, passes))

        elif shape == "C":
            lines.extend(generate_circle(x, y, speed, passes))

    # Return home safely
    lines.append("M5")
    lines.append("G0 X0 Y0")

    with open("cut_test.gcode", "w") as f:
        f.write("\n".join(lines))

    messagebox.showinfo(
        "Done",
        "Generated cut_test.gcode"
    )


root = tk.Tk()
root.title("Laser Cut Test Generator")

label = tk.Label(
    root,
    text="Format: S speed pass OR C speed pass"
)
label.pack(pady=5)

input_box = tk.Text(root, width=40, height=15)
input_box.pack(padx=10, pady=10)

generate_btn = tk.Button(
    root,
    text="Generate GCode",
    command=generate_gcode
)
generate_btn.pack(pady=10)

root.mainloop()