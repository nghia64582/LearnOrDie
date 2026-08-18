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

        sample = """C 50 50 30\nR 20 30 40 50\nRC 120 100 50 30\nLV 10 10 100\nLH 50 50 80\nL 10 10 100 100\n"""

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

        tk.Label(gcode_frame, text="Speed_x").grid(row=0, column=0)

        self.speed_x_var = tk.StringVar(value="400")
        self.speed_y_var = tk.StringVar(value="200")

        tk.Entry(
            gcode_frame,
            textvariable=self.speed_x_var,
            width=10
        ).grid(row=0, column=1)

        tk.Label(gcode_frame, text="Speed_y").grid(row=1, column=0)
        tk.Entry(
            gcode_frame,
            textvariable=self.speed_y_var,
            width=10
        ).grid(row=1, column=1)


        tk.Label(gcode_frame, text="Power").grid(row=2, column=0)

        self.power_var = tk.StringVar(value="1000")

        tk.Entry(
            gcode_frame,
            textvariable=self.power_var,
            width=10
        ).grid(row=2, column=1)

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

    def show_help(self):

        text = """
            C x y r
            Circle

            R x y w h
            Rectangle (bottom-left)

            RC cx cy w h
            Rectangle (center)

            LH x y length
            Horizontal line

            LV x y length
            Vertical line

            L x1 y1 x2 y2
            Any line

            A x y s_alpha e_alpha
            Arc, tam (x, y), goc bat dau s_alpha, goc ket thuc e_alpha.
            Goc 0 = huong len (truc +y), 180 = huong xuong (truc -y),
            90 = huong phai (truc +x), 270 = huong trai (truc -x),
            360 = trung voi 0 (mot vong tron day du).

            ADD x y
            Tu dong nay tro di, moi hinh se duoc cong them (x, y)
            cho den khi gap dong END (delta ve lai 0, 0).

            P x1 y1 x2 y2 ... xn yn
            Da giac (polygon) tuy y so dinh, tu dong noi dinh cuoi
            ve dinh dau de dong kin hinh.

            M x1 y1 x2 y2 ... xn yn
            Day doan thang (polyline) tuy y so dinh, giong P nhung
            KHONG noi diem cuoi ve diem dau (hinh ho).

            Examples:

            C 50 50 30
            R 20 30 40 50
            RC 100 100 80 40
            LV 10 20 50
            LH 30 40 80
            L 0 0 100 100
            A 50 50 0 180
            P 0 0 40 0 40 40 20 60 0 40
            M 0 0 20 30 40 0 60 30
            ADD 20 20
            C 0 0 10
            END
            """

        messagebox.showinfo(
            "Format Help",
            text
        )

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

            # -----------------------------------------------------
            # Delta hien hanh, duoc cong don vao tat ca cac hinh
            # cho den khi gap dong END
            # -----------------------------------------------------

            delta_x = 0.0
            delta_y = 0.0

            for line in text.strip().splitlines():

                line = line.strip()

                if not line:
                    continue

                parts = line.split()

                cmd = parts[0]

                if cmd == "ADD":

                    dx, dy = map(float, parts[1:])

                    delta_x = dx
                    delta_y = dy

                    continue

                if cmd == "END":

                    delta_x = 0.0
                    delta_y = 0.0

                    continue

                nums = list(map(float, parts[1:]))

                nums = self._apply_delta(
                    cmd, nums, delta_x, delta_y
                )

                self.shapes.append((cmd, nums))

                self.draw_shape(cmd, nums)
        except Exception as e:
            messagebox.showerror(
                "Error",
                str(e)
            )

    def _apply_delta(self, cmd, nums, dx, dy):

        # Chi cong delta vao cac toa do vi tri (x, y / cx, cy),
        # khong dong vao w, h, r, length hay goc

        if cmd in ("C", "RC", "LH", "LV", "A"):

            x, rest = nums[0], nums[1:]
            y = rest[0]

            return [x + dx, y + dy] + rest[1:]

        if cmd == "R":

            x, y, w, h = nums

            return [x + dx, y + dy, w, h]

        if cmd == "L":

            x1, y1, x2, y2 = nums

            return [x1 + dx, y1 + dy, x2 + dx, y2 + dy]

        if cmd in ("P", "M"):

            # Cong delta vao tung cap (x, y) cua da giac / polyline
            result = []

            for i in range(0, len(nums), 2):

                result.append(nums[i] + dx)
                result.append(nums[i + 1] + dy)

            return result

        return nums

    def draw_shape(self, cmd, nums):

        colors = {
            "C": "black",
            "A": "black",
            "R": "green",
            "RC": "green",
            "P": "purple",
            "M": "orange",
        }

        color = colors.get(cmd, "black")

        segments = self._shape_to_segments(cmd, nums)

        for x1, y1, x2, y2 in segments:

            px1, py1 = self.to_canvas(x1, y1)
            px2, py2 = self.to_canvas(x2, y2)

            self.canvas.create_line(
                px1, py1, px2, py2,
                fill=color,
                width=2
            )

    def _arc_segments(self, cx, cy, r, s_alpha, e_alpha):

        # Goc tinh theo kieu la ban: 0 = huong len (+y), 90 = huong
        # phai (+x), 180 = huong xuong (-y), 270 = huong trai (-x).
        # Doi sang goc toan hoc (radian) de dung cos/sin:
        # math_angle = 90 - bearing

        span = e_alpha - s_alpha

        segment_count = max(
            2,
            round(abs(span) / 360 * 60)
        )

        points = []

        for i in range(segment_count + 1):

            bearing = s_alpha + span * i / segment_count

            math_angle = math.radians(90 - bearing)

            x = cx + r * math.cos(math_angle)
            y = cy + r * math.sin(math_angle)

            points.append((x, y))

        segments = []

        for i in range(len(points) - 1):

            p1 = points[i]
            p2 = points[i + 1]

            segments.append(
                (p1[0], p1[1], p2[0], p2[1])
            )

        return segments

    def _shape_to_segments(self, cmd, nums):

        segments = []

        if cmd == "L":

            x1, y1, x2, y2 = nums

            segments.append(
                (x1, y1, x2, y2)
            )

        elif cmd == "LH":

            x, y, length = nums

            segments.append(
                (x, y, x + length, y)
            )

        elif cmd == "LV":

            x, y, length = nums

            segments.append(
                (x, y, x, y + length)
            )

        elif cmd == "R":

            x, y, w, h = nums

            segments.append(
                (x, y, x + w, y)
            )

            segments.append(
                (x + w, y, x + w, y + h)
            )

            segments.append(
                (x + w, y + h, x, y + h)
            )

            segments.append(
                (x, y + h, x, y)
            )

        elif cmd == "RC":

            cx, cy, w, h = nums

            x = cx - w / 2
            y = cy - h / 2

            segments.append(
                (x, y, x + w, y)
            )

            segments.append(
                (x + w, y, x + w, y + h)
            )

            segments.append(
                (x + w, y + h, x, y + h)
            )

            segments.append(
                (x, y + h, x, y)
            )

        elif cmd == "C":

            cx, cy, r = nums

            segments.extend(
                self._arc_segments(cx, cy, r, 0, 360)
            )

        elif cmd == "A":

            cx, cy, r, s_alpha, e_alpha = nums

            segments.extend(
                self._arc_segments(cx, cy, r, s_alpha, e_alpha)
            )

        elif cmd == "P":

            points = [
                (nums[i], nums[i + 1])
                for i in range(0, len(nums), 2)
            ]

            point_count = len(points)

            for i in range(point_count):

                p1 = points[i]
                p2 = points[(i + 1) % point_count]

                segments.append(
                    (p1[0], p1[1], p2[0], p2[1])
                )

        elif cmd == "M":

            points = [
                (nums[i], nums[i + 1])
                for i in range(0, len(nums), 2)
            ]

            # Khong noi diem cuoi ve diem dau (khac voi P)
            for i in range(len(points) - 1):

                p1 = points[i]
                p2 = points[i + 1]

                segments.append(
                    (p1[0], p1[1], p2[0], p2[1])
                )

        return segments

    def _shapes_to_segments(self):

        segments = []

        for cmd, nums in self.shapes:

            segments.extend(
                self._shape_to_segments(cmd, nums)
            )

        return segments

    def _segment_key(self, segment):
        x1, y1, x2, y2 = segment

        # Làm tròn để tránh floating point
        p1 = (
            round(x1, 6),
            round(y1, 6)
        )

        p2 = (
            round(x2, 6),
            round(y2, 6)
        )

        # A->B và B->A là cùng segment
        if p1 <= p2:
            return (p1, p2)

        return (p2, p1)
    
    def _remove_duplicate_segments(self, segments):

        result = []
        seen = set()

        for segment in segments:

            key = self._segment_key(segment)

            if key in seen:
                continue

            seen.add(key)
            result.append(segment)

        return result

    def _distance_sq(self, p1, p2):

        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]

        return dx * dx + dy * dy   

    def _optimize_segments_greedy(self, segments):
        if not segments:
            return []

        remaining = segments.copy()

        result = []

        # Điểm bắt đầu
        current = (0.0, 0.0)

        while remaining:

            best_index = None
            best_distance = float("inf")
            best_reversed = False

            for i, segment in enumerate(remaining):

                x1, y1, x2, y2 = segment

                p1 = (x1, y1)
                p2 = (x2, y2)

                d1 = self._distance_sq(current, p1)
                d2 = self._distance_sq(current, p2)

                if d1 < best_distance:

                    best_distance = d1
                    best_index = i
                    best_reversed = False

                if d2 < best_distance:

                    best_distance = d2
                    best_index = i
                    best_reversed = True

            segment = remaining.pop(best_index)

            x1, y1, x2, y2 = segment

            if best_reversed:

                segment = (
                    x2, y2,
                    x1, y1
                )

            result.append(segment)

            current = (
                segment[2],
                segment[3]
            )

        return result
    
    def generate_gcode(self):

        self.preview()

        speed_x = float(self.speed_x_var.get())
        speed_y = float(self.speed_y_var.get())
        power = float(self.power_var.get())

        lines = []

        lines.append("G21")
        lines.append("G90")

        # =========================================================
        # B1: tất cả shape -> line segments
        # =========================================================

        segments = self._shapes_to_segments()

        # =========================================================
        # Loại các segment trùng nhau
        # =========================================================

        segments = self._remove_duplicate_segments(
            segments
        )

        # =========================================================
        # B2: greedy tìm đường đi
        # =========================================================

        segments = self._optimize_segments_greedy(
            segments
        )

        # =========================================================
        # Xuất G-code
        # =========================================================

        current = None
        laser_on = False

        for x1, y1, x2, y2 in segments:

            start = (x1, y1)
            end = (x2, y2)

            # -----------------------------------------------------
            # Nếu segment mới bắt đầu đúng tại vị trí hiện tại
            # thì có thể tiếp tục cắt
            # -----------------------------------------------------

            connected = (
                current is not None
                and abs(current[0] - x1) < 1e-6
                and abs(current[1] - y1) < 1e-6
            )

            if not connected:

                if laser_on:

                    lines.append("M5")
                    laser_on = False

                lines.append(
                    f"G0 X{x1:.3f} Y{y1:.3f}"
                )

                lines.append(
                    f"M3 S{power}"
                )

                laser_on = True

            elif not laser_on:

                lines.append(
                    f"G0 X{x1:.3f} Y{y1:.3f}"
                )

                lines.append(
                    f"M3 S{power}"
                )

                laser_on = True

            # -----------------------------------------------------
            # Cắt segment
            # -----------------------------------------------------

            dx = x2 - x1
            dy = y2 - y1

            length = (dx ** 2 + dy ** 2) ** 0.5

            if length > 1e-9:
                # Thành phần hướng của chuyển động
                ux = abs(dx) / length
                uy = abs(dy) / length

                # Feed rate tối đa sao cho:
                # vx <= speed_x
                # vy <= speed_y
                feed_x = speed_x / ux if ux > 1e-9 else float("inf")
                feed_y = speed_y / uy if uy > 1e-9 else float("inf")

                feed = min(feed_x, feed_y)

            else:
                feed = speed_x

            lines.append(
                f"G1 X{x2:.3f} Y{y2:.3f} F{feed:.3f}"
            )

            current = end

        if laser_on:

            lines.append("M5")

        with open("cut_plan.gcode", "w") as f:
            f.write("\n".join(lines))
            messagebox.showinfo(
                "Done",
                "Generated cut_plan.gcode"
            )