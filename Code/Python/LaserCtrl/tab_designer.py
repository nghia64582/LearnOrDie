import tkinter as tk
from tkinter import ttk, messagebox
import math


class DesignerTab(ttk.Frame):

    GRID_MM = 10

    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app
        self.font = ("Times New Roman", 11)

        self.shapes = []

        self.canvas_width = 1000
        self.canvas_height = 700

        self.build_gui()

    # =========================================================
    # GUI
    # =========================================================

    def build_gui(self):

        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        right_frame = tk.Frame(self)
        right_frame.pack(side="right", fill="both", expand=True)

        # =====================================================
        # HELP BUTTON
        # =====================================================

        top_btn_frame = tk.Frame(left_frame)
        top_btn_frame.pack(fill="x")

        tk.Button(
            top_btn_frame,
            text="Help",
            command=self.show_help,
            font=self.font
        ).pack(side="left")

        # =====================================================
        # TEXT INPUT
        # =====================================================

        tk.Label(
            left_frame,
            text="Shapes",
            font=self.font
        ).pack(anchor="w")

        self.text_input = tk.Text(
            left_frame,
            width=40,
            height=28,
            font=("Consolas", 11)
        )

        self.text_input.pack(fill="y")

        sample = """C 50 50 30
R 20 30 40 50
RC 120 100 50 30
LV 10 10 100
LH 50 50 80
L 10 10 100 100
"""

        self.text_input.insert("1.0", sample)

        # Ctrl + Enter
        self.text_input.bind(
            "<Control-Return>",
            lambda e: self.preview()
        )

        # =====================================================
        # VIEWPORT
        # =====================================================

        view_frame = tk.LabelFrame(
            left_frame,
            text="Viewport (mm)",
            font=self.font
        )

        view_frame.pack(fill="x", pady=5)

        tk.Label(view_frame, text="Left").grid(row=0, column=0)
        tk.Label(view_frame, text="Bottom").grid(row=0, column=2)

        self.left_var = tk.StringVar(value="-20")
        self.bottom_var = tk.StringVar(value="-20")

        tk.Entry(view_frame, textvariable=self.left_var, width=10)\
            .grid(row=0, column=1)

        tk.Entry(view_frame, textvariable=self.bottom_var, width=10)\
            .grid(row=0, column=3)

        tk.Label(view_frame, text="Right").grid(row=1, column=0)
        tk.Label(view_frame, text="Top").grid(row=1, column=2)

        self.right_var = tk.StringVar(value="250")
        self.top_var = tk.StringVar(value="180")

        tk.Entry(view_frame, textvariable=self.right_var, width=10)\
            .grid(row=1, column=1)

        tk.Entry(view_frame, textvariable=self.top_var, width=10)\
            .grid(row=1, column=3)

        # =====================================================
        # GCODE SETTINGS
        # =====================================================

        gcode_frame = tk.LabelFrame(
            left_frame,
            text="GCODE",
            font=self.font
        )

        gcode_frame.pack(fill="x", pady=5)

        tk.Label(gcode_frame, text="Speed").grid(row=0, column=0)

        self.speed_var = tk.StringVar(value="280")

        tk.Entry(
            gcode_frame,
            textvariable=self.speed_var,
            width=10
        ).grid(row=0, column=1)

        tk.Label(gcode_frame, text="Power").grid(row=1, column=0)

        self.power_var = tk.StringVar(value="1000")

        tk.Entry(
            gcode_frame,
            textvariable=self.power_var,
            width=10
        ).grid(row=1, column=1)

        # =====================================================
        # BUTTONS
        # =====================================================

        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill="x", pady=5)

        tk.Button(
            btn_frame,
            text="Preview (Ctrl+Enter)",
            command=self.preview,
            font=self.font
        ).pack(side="left", padx=2)

        tk.Button(
            btn_frame,
            text="Generate GCODE",
            command=self.generate_gcode,
            font=self.font
        ).pack(side="left", padx=2)

        # =====================================================
        # CANVAS
        # =====================================================

        self.canvas = tk.Canvas(
            right_frame,
            bg="white",
            width=self.canvas_width,
            height=self.canvas_height
        )

        self.canvas.pack(fill="both", expand=True)

        self.preview()

    # =========================================================
    # HELP
    # =========================================================

    def show_help(self):

        text = """
C x y r
Circle

R x y w h
Rectangle (bottom-left)

RC cx cy w h
Rectangle (center)

LV x y length
Horizontal line

LH x y length
Vertical line

L x1 y1 x2 y2
Any line

Examples:

C 50 50 30
R 20 30 40 50
RC 100 100 80 40
LV 10 20 50
LH 30 40 80
L 0 0 100 100
"""

        messagebox.showinfo(
            "Format Help",
            text
        )

    # =========================================================
    # COORD
    # =========================================================

    def to_canvas(self, x, y):

        px = (
            (x - self.view_left)
            / self.view_width
            * self.canvas_width
        )

        py = (
            self.canvas_height
            - (
                (y - self.view_bottom)
                / self.view_height
                * self.canvas_height
            )
        )

        return px, py

    # =========================================================
    # GRID
    # =========================================================

    def draw_grid(self):

        self.canvas.delete("all")

        step = self.GRID_MM

        x = math.floor(self.view_left / step) * step

        while x <= self.view_right:

            px1, py1 = self.to_canvas(x, self.view_bottom)
            px2, py2 = self.to_canvas(x, self.view_top)

            self.canvas.create_line(
                px1, py1, px2, py2,
                fill="#dddddd"
            )

            self.canvas.create_text(
                px1 + 2,
                self.canvas_height - 10,
                text=str(x),
                font=("Arial", 8),
                anchor="nw"
            )

            x += step

        y = math.floor(self.view_bottom / step) * step

        while y <= self.view_top:

            px1, py1 = self.to_canvas(self.view_left, y)
            px2, py2 = self.to_canvas(self.view_right, y)

            self.canvas.create_line(
                px1, py1, px2, py2,
                fill="#dddddd"
            )

            self.canvas.create_text(
                2,
                py1,
                text=str(y),
                font=("Arial", 8),
                anchor="nw"
            )

            y += step

        # X axis
        if self.view_bottom <= 0 <= self.view_top:

            px1, py1 = self.to_canvas(self.view_left, 0)
            px2, py2 = self.to_canvas(self.view_right, 0)

            self.canvas.create_line(
                px1, py1, px2, py2,
                fill="red",
                width=2
            )

        # Y axis
        if self.view_left <= 0 <= self.view_right:

            px1, py1 = self.to_canvas(0, self.view_bottom)
            px2, py2 = self.to_canvas(0, self.view_top)

            self.canvas.create_line(
                px1, py1, px2, py2,
                fill="blue",
                width=2
            )

    # =========================================================
    # PREVIEW
    # =========================================================

    def preview(self):

        try:

            self.view_left = float(self.left_var.get())
            self.view_bottom = float(self.bottom_var.get())
            self.view_right = float(self.right_var.get())
            self.view_top = float(self.top_var.get())

            self.view_width = self.view_right - self.view_left
            self.view_height = self.view_top - self.view_bottom

            self.draw_grid()

            self.shapes = []

            text = self.text_input.get("1.0", "end")

            for line in text.strip().splitlines():

                line = line.strip()

                if not line:
                    continue

                parts = line.split()

                cmd = parts[0]

                nums = list(map(float, parts[1:]))

                self.shapes.append((cmd, nums))

                self.draw_shape(cmd, nums)

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =========================================================
    # DRAW SHAPE
    # =========================================================

    def draw_shape(self, cmd, nums):

        if cmd == "C":

            cx, cy, r = nums

            x1, y1 = self.to_canvas(cx - r, cy - r)
            x2, y2 = self.to_canvas(cx + r, cy + r)

            self.canvas.create_oval(
                x1, y2, x2, y1,
                outline="black",
                width=2
            )

        elif cmd in ["R", "RC"]:

            if cmd == "R":

                x, y, w, h = nums

            else:

                cx, cy, w, h = nums

                x = cx - w / 2
                y = cy - h / 2

            x1, y1 = self.to_canvas(x, y)
            x2, y2 = self.to_canvas(x + w, y + h)

            self.canvas.create_rectangle(
                x1, y2, x2, y1,
                outline="green",
                width=2
            )

        elif cmd == "LV":

            x, y, length = nums

            x1, y1 = self.to_canvas(x, y)
            x2, y2 = self.to_canvas(x + length, y)

            self.canvas.create_line(
                x1, y1, x2, y2,
                width=2
            )

        elif cmd == "LH":

            x, y, length = nums

            x1, y1 = self.to_canvas(x, y)
            x2, y2 = self.to_canvas(x, y + length)

            self.canvas.create_line(
                x1, y1, x2, y2,
                width=2
            )

        elif cmd == "L":

            x1, y1, x2, y2 = nums

            px1, py1 = self.to_canvas(x1, y1)
            px2, py2 = self.to_canvas(x2, y2)

            self.canvas.create_line(
                px1, py1,
                px2, py2,
                width=2
            )

    # =========================================================
    # GCODE
    # =========================================================

    def generate_gcode(self):

        self.preview()

        speed = float(self.speed_var.get())
        power = float(self.power_var.get())

        lines = []

        lines.append("G21")
        lines.append("G90")

        for cmd, nums in self.shapes:

            if cmd == "L":

                x1, y1, x2, y2 = nums

                lines.append(f"G0 X{x1:.3f} Y{y1:.3f}")
                lines.append(f"M3 S{power}")
                lines.append(f"G1 X{x2:.3f} Y{y2:.3f} F{speed}")
                lines.append("M5")

            elif cmd == "LV":

                x, y, length = nums

                lines.append(f"G0 X{x:.3f} Y{y:.3f}")
                lines.append(f"M3 S{power}")
                lines.append(f"G1 X{x+length:.3f} Y{y:.3f} F{speed}")
                lines.append("M5")

            elif cmd == "LH":

                x, y, length = nums

                lines.append(f"G0 X{x:.3f} Y{y:.3f}")
                lines.append(f"M3 S{power}")
                lines.append(f"G1 X{x:.3f} Y{y+length:.3f} F{speed}")
                lines.append("M5")

            elif cmd in ["R", "RC"]:

                if cmd == "R":

                    x, y, w, h = nums

                else:

                    cx, cy, w, h = nums

                    x = cx - w/2
                    y = cy - h/2

                lines.append(f"G0 X{x:.3f} Y{y:.3f}")
                lines.append(f"M3 S{power}")

                lines.append(f"G1 X{x+w:.3f} Y{y:.3f} F{speed}")
                lines.append(f"G1 X{x+w:.3f} Y{y+h:.3f}")
                lines.append(f"G1 X{x:.3f} Y{y+h:.3f}")
                lines.append(f"G1 X{x:.3f} Y{y:.3f}")

                lines.append("M5")

            elif cmd == "C":

                cx, cy, r = nums

                segments = 60

                sx = cx + r
                sy = cy

                lines.append(f"G0 X{sx:.3f} Y{sy:.3f}")
                lines.append(f"M3 S{power}")

                for i in range(1, segments + 1):

                    angle = math.radians(i * 360 / segments)

                    x = cx + r * math.cos(angle)
                    y = cy + r * math.sin(angle)

                    lines.append(
                        f"G1 X{x:.3f} Y{y:.3f} F{speed}"
                    )

                lines.append("M5")

        with open("cut_plan.gcode", "w") as f:

            f.write("\n".join(lines))

        messagebox.showinfo(
            "Done",
            "Generated cut_plan.gcode"
        )