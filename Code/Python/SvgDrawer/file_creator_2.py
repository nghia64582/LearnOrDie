import tkinter as tk
from tkinter import messagebox, filedialog
import webbrowser
from pathlib import Path

# ===================== CONFIG =====================
APP_FONT = ("Times New Roman", 12)   # <<== CUSTOM FONT ở đây
GRID_SIZE = 10                 # size ô lưới
GRID_COUNT = 20                # số ô lưới mỗi chiều
SVG_FILE = "output.svg"
GCODE_FILE = "output.gcode"
# ===================================================

def parse_shapes(shape_text):
    shapes = []
    lines = shape_text.strip().split("\n")
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        t = parts[0].upper()

        try:
            if t == "C":  # Circle
                _, x, y, r = parts
                shapes.append(("CIRCLE", float(x), float(y), float(r)))
            elif t == "R":  # Rectangle
                _, x, y, w, h = parts
                shapes.append(("RECT", float(x), float(y), float(w), float(h)))
            elif t == "L":  # Line segment
                _, x1, y1, x2, y2 = parts
                shapes.append(("LINE", float(x1), float(y1), float(x2), float(y2)))
            elif t == "LH":  # Horizontal
                _, x, y, L = parts
                shapes.append(("LINE", float(x), float(y), float(x) + float(L), float(y)))
            elif t == "LV":  # Vertical
                _, x, y, L = parts
                shapes.append(("LINE", float(x), float(y), float(x), float(y) + float(L)))
        except Exception:
            raise ValueError(f"Lỗi định dạng dòng: {line}")

    return shapes

def generate_svg(shapes):
    # --- Compute bounds ---
    min_x = min([s[1] - (s[3] if s[0]=="CIRCLE" else 0) for s in shapes] + [0])
    min_y = min([s[2] - (s[3] if s[0]=="CIRCLE" else 0) for s in shapes] + [0])
    max_x = max([s[1] + (s[3] if s[0]=="CIRCLE" else s[3] if s[0]=="RECT" else 0) for s in shapes] + [100])
    max_y = max([s[2] + (s[4] if s[0]=="RECT" else s[3] if s[0]=="CIRCLE" else 0) for s in shapes] + [100])

    # Add padding and allow negative X
    PAD = 40
    OY_OFFSET = 20         # shift Oy right a bit
    min_x = min(min_x, -10)

    width = (max_x - min_x) + PAD * 2
    height = (max_y - min_y) + PAD * 2

    # SVG header
    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )

    # ====== GRID (normal SVG coordinate) =======
    svg.append('<g stroke="#cccccc" stroke-width="0.3">')
    for x in range(0, int(width), 10):
        svg.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}"/>')
    for y in range(0, int(height), 10):
        svg.append(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}"/>')
    svg.append('</g>')

    # ====== AXIS (0,0 at bottom-left user space) ======
    # Convert (0,0) and (max_x, max_y)
    def uy(y): return height - y

    svg.append('<g stroke="red" stroke-width="1">')
    # Ox – from (min_x, 0) to (max_x, 0)
    svg.append(f'<line x1="{PAD}" y1="{uy(0+PAD)}" '
               f'x2="{width - PAD}" y2="{uy(0+PAD)}"/>')
    # Oy – vertical at PAD + offset
    OY = PAD + OY_OFFSET
    svg.append(f'<line x1="{OY}" y1="{uy(PAD)}" '
               f'x2="{OY}" y2="{uy(max_y + PAD)}"/>')
    svg.append('</g>')

    # ====== SHAPES (scaled 3×) ======
    svg.append('<g transform="scale(3)">')

    def fix_x(x): return (x - min_x + PAD) / 3
    def fix_y(y): return (height - (y - min_y + PAD)) / 3

    for s in shapes:
        if s[0] == "RECT":
            _, x, y, w, h = s
            svg.append(
                f'<rect x="{fix_x(x)}" y="{fix_y(y+h)}" '
                f'width="{w/3}" height="{h/3}" '
                f'stroke="black" fill="none" stroke-width="0.3"/>'
            )

        elif s[0] == "CIRCLE":
            _, x, y, r = s
            svg.append(
                f'<circle cx="{fix_x(x)}" cy="{fix_y(y)}" r="{r/3}" '
                f'stroke="black" fill="none" stroke-width="0.3"/>'
            )

        elif s[0] == "LINE":
            _, x1, y1, x2, y2 = s
            svg.append(
                f'<line x1="{fix_x(x1)}" y1="{fix_y(y1)}" '
                f'x2="{fix_x(x2)}" y2="{fix_y(y2)}" '
                f'stroke="black" stroke-width="0.3"/>'
            )

    svg.append('</g>')
    svg.append('</svg>')

    Path(SVG_FILE).write_text("\n".join(svg), encoding="utf-8")

def generate_gcode(shapes, speed, power):
    g = ["G21 ; mm/min", "G90 ; absolute"]

    for s in shapes:
        if s[0] == "LINE":
            _, x1, y1, x2, y2 = s
            g += [
                f"G0 X{x1} Y{y1}",
                f"M3 S{power}",
                f"G1 X{x2} Y{y2} F{speed}",
                "M5"
            ]

        elif s[0] == "RECT":
            _, x, y, w, h = s
            pts = [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)]
            g.append(f"G0 X{x} Y{y}")
            g.append(f"M3 S{power}")
            for px, py in pts[1:]:
                g.append(f"G1 X{px} Y{py} F{speed}")
            g.append("M5")
        elif s[0] == "CIRCLE":

            _, cx, cy, r = s

            # Start point = rightmost point of circle
            x0 = cx + r
            y0 = cy

            g.append(f"G0 X{x0:.3f} Y{y0:.3f}")       # move to start
            g.append(f"M3 S{power}")                 # turn laser on

            # Full circle clockwise
            # End at same point, arc center offset I=-r, J=0
            g.append(f"G2 X{x0:.3f} Y{y0:.3f} I{-r:.3f} J{0:.3f} F{speed}")

            g.append("M5")                           # turn laser off


    Path(GCODE_FILE).write_text("\n".join(g), encoding="utf-8")


# ======================= UI =========================

def on_generate():
    try:
        shapes = parse_shapes(shape_input.get("1.0", tk.END))
    except Exception as e:
        messagebox.showerror("Parse Error", str(e))
        return

    try:
        spd = float(speed_var.get())
        pwr = float(power_var.get())
    except:
        messagebox.showerror("Error", "Speed/Power phải là số")
        return

    generate_svg(shapes)
    generate_gcode(shapes, spd, pwr)
    messagebox.showinfo("Done", "Generated SVG + G-code")


def on_preview():
    webbrowser.open(Path(SVG_FILE).absolute().as_uri())


# ---------------------- TK --------------------------
root = tk.Tk()
root.title("Laser SVG/G-code Generator")
root.geometry("900x600")

root.option_add("*Font", APP_FONT)   # dùng custom font toàn app

# Left panel
left = tk.Frame(root)
left.pack(side="left", fill="y", padx=10, pady=10)

tk.Label(left, text="Shapes:").pack(anchor="w")
shape_input = tk.Text(left, width=40, height=10)
shape_input.pack()

tk.Label(left, text="Speed (mm/min):").pack(anchor="w")
speed_var = tk.StringVar(value="600")
tk.Entry(left, textvariable=speed_var).pack(anchor="w", fill="x")

tk.Label(left, text="Power (%):").pack(anchor="w")
power_var = tk.StringVar(value="30")
tk.Entry(left, textvariable=power_var).pack(anchor="w", fill="x")

tk.Button(left, text="Generate (Ctrl+B)", command=on_generate).pack(fill="x", pady=5)
tk.Button(left, text="Preview (Ctrl+N)", command=on_preview).pack(fill="x")

# Bind hotkeys
root.bind("<Control-b>", lambda e: on_generate())
root.bind("<Control-n>", lambda e: on_preview())

root.mainloop()
