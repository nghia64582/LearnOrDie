import tkinter as tk
from tkinter import ttk, messagebox
import math


class DesignerTab(ttk.Frame):

    GRID_MM = 10

    # Speed tab: doan thang dai hon nguong, phan giua di nhanh (V3)
    # de khong cat xuyen het vat lieu
    SPEED_TAB_ENABLED = True
    SPEED_TAB_THRESHOLD = 8  # mm
    SPEED_TAB_DISTANCE = 8  # mm, khoang cach giua 2 tab lien tiep
    SPEED_TAB_LENGTH = 0.5  # mm
    SPEED_TAB_FEED = 550  # mm/min (V3)

    # Arc tab: cung (ke ca hinh tron, coi la cung 0-360 do) co ban
    # kinh > nguong nay se duoc chen tab theo do dai cung (dung
    # chung SPEED_TAB_* o tren), vi cac doan thang xap xi cung
    # thuong qua ngan de tu kich hoat tab theo do dai doan thang
    # thong thuong
    ARC_TAB_DIAMETER_THRESHOLD = 30  # mm

    # Short segment slowdown: doan ngan hon nguong se cat cham lai,
    # tranh cat khong dut het vat lieu
    SHORT_SLOW_ENABLED = True
    SHORT_SLOW_THRESHOLD = 15  # mm
    SHORT_SLOW_PERCENT = 60  # %

    # Font cho label cua tung lop ADD ve tren canvas
    ADD_LABEL_FONT = ("Times New Roman", 11)

    # Bounds mark: ve dau + tai 4 goc vung hoat dong (min/max x, y)
    # de kiem tra pham vi cat truoc khi chay that
    BOUNDS_MARK_LENGTH = 4  # mm, do dai moi doan cua dau +
    BOUNDS_MARK_POWER = 200
    BOUNDS_MARK_FEED = 600  # mm/min

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

        # --- Help button ---
        top_btn_frame = tk.Frame(left_frame)
        top_btn_frame.pack(fill="x")
        tk.Button(top_btn_frame, text="Help", command=self.show_help,
                  font=self.font).pack(side="left")

        # --- Text input ---
        tk.Label(left_frame, text="Shapes", font=self.font).pack(anchor="w")
        self.text_input = tk.Text(left_frame, width=40, height=28,
                                   font=("Consolas", 11))
        self.text_input.pack(fill="y")

        sample = ("C 50 50 30\nR 20 30 40 50\nRC 120 100 50 30\n"
                   "LV 10 10 100\nLH 50 50 80\nL 10 10 100 100\n")
        self.text_input.insert("1.0", sample)
        self.text_input.bind("<Control-Return>", lambda e: self.preview())

        # --- Viewport ---
        view_frame = tk.LabelFrame(left_frame, text="Viewport (mm)",
                                    font=self.font)
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

        # --- GCODE settings ---
        gcode_frame = tk.LabelFrame(left_frame, text="GCODE", font=self.font)
        gcode_frame.pack(fill="x", pady=5)

        tk.Label(gcode_frame, text="Speed_x").grid(row=0, column=0)
        self.speed_x_var = tk.StringVar(value="250")
        self.speed_y_var = tk.StringVar(value="200")
        tk.Entry(gcode_frame, textvariable=self.speed_x_var, width=10)\
            .grid(row=0, column=1)

        tk.Label(gcode_frame, text="Speed_y").grid(row=1, column=0)
        tk.Entry(gcode_frame, textvariable=self.speed_y_var, width=10)\
            .grid(row=1, column=1)

        tk.Label(gcode_frame, text="Power").grid(row=2, column=0)
        self.power_var = tk.StringVar(value="1000")
        tk.Entry(gcode_frame, textvariable=self.power_var, width=10)\
            .grid(row=2, column=1)

        # --- Buttons ---
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Preview (Ctrl+Enter)",
                  command=self.preview, font=self.font)\
            .pack(side="left", padx=2)
        tk.Button(btn_frame, text="Generate GCODE",
                  command=self.generate_gcode, font=self.font)\
            .pack(side="left", padx=2)
        tk.Button(btn_frame, text="Ve vung hoat dong",
                  command=self.generate_bounds_gcode, font=self.font)\
            .pack(side="left", padx=2)

        # --- Canvas ---
        self.canvas = tk.Canvas(right_frame, bg="white",
                                 width=self.canvas_width,
                                 height=self.canvas_height)
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

            ADD x y label
            Day them 1 lop delta (x, y) len stack, ap dung cho moi
            hinh phia sau cho den khi gap dong END tuong ung. Co
            the long nhau nhieu tang ADD (delta se cong don tat ca
            cac lop dang mo). label la mot chuoi tuy y, duoc ve
            kem cham danh dau tren canvas de de nhan biet.
            END chi bo di lop ADD/ROTATE gan nhat (giong dong ngoac).

            ROTATE goc
            Day them 1 lop xoay (theo do, chieu kim dong ho) len
            CUNG 1 stack voi ADD. Co the long nhieu lop ROTATE, goc
            se duoc cong don tuyen tinh. Neu dang co delta (x, y) tu
            ADD, hinh se duoc dich chuyen den (x, y) truoc, roi xoay
            quanh tam (x, y) do. END cung bo di lop ROTATE gan nhat.

            P x1 y1 x2 y2 ... xn yn
            Da giac (polygon) tuy y so dinh, tu dong noi dinh cuoi
            ve dinh dau de dong kin hinh.

            M x1 y1 x2 y2 ... xn yn
            Day doan thang (polyline) tuy y so dinh, giong P nhung
            KHONG noi diem cuoi ve diem dau (hinh ho).

            # ...
            Dong bat dau bang # la comment, se bi bo qua. Dong
            trong hoac dong khong dung format (lenh la, sai so
            tham so, ...) cung se tu dong bi bo qua, khong lam
            gian doan preview.

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

            # Vi du long 2 tang ADD
            ADD 20 20 Ban le ngoai
            C 0 0 10
            ADD 5 5 Ban le trong
            C 0 0 3
            END
            C 0 0 5
            END
            C 0 0 5

            # Vi du ADD + ROTATE: dich den (50, 0) roi xoay 45 do
            # quanh diem (50, 0)
            ADD 50 0 Xoay 45 do
            ROTATE 45
            R 0 0 20 10
            END
            END
            """
        messagebox.showinfo("Format Help", text)

    def to_canvas(self, x, y):
        px = (x - self.view_left) / self.view_width * self.canvas_width
        py = self.canvas_height - (
            (y - self.view_bottom) / self.view_height * self.canvas_height
        )
        return px, py

    def draw_grid(self):
        self.canvas.delete("all")
        step = self.GRID_MM

        x = math.floor(self.view_left / step) * step
        while x <= self.view_right:
            px1, py1 = self.to_canvas(x, self.view_bottom)
            px2, py2 = self.to_canvas(x, self.view_top)
            self.canvas.create_line(px1, py1, px2, py2, fill="#dddddd")
            self.canvas.create_text(px1 + 2, self.canvas_height - 10,
                                     text=str(x), font=("Arial", 8),
                                     anchor="nw")
            x += step

        y = math.floor(self.view_bottom / step) * step
        while y <= self.view_top:
            px1, py1 = self.to_canvas(self.view_left, y)
            px2, py2 = self.to_canvas(self.view_right, y)
            self.canvas.create_line(px1, py1, px2, py2, fill="#dddddd")
            self.canvas.create_text(2, py1, text=str(y), font=("Arial", 8),
                                     anchor="nw")
            y += step

        if self.view_bottom <= 0 <= self.view_top:
            px1, py1 = self.to_canvas(self.view_left, 0)
            px2, py2 = self.to_canvas(self.view_right, 0)
            self.canvas.create_line(px1, py1, px2, py2, fill="red", width=2)

        if self.view_left <= 0 <= self.view_right:
            px1, py1 = self.to_canvas(0, self.view_bottom)
            px2, py2 = self.to_canvas(0, self.view_top)
            self.canvas.create_line(px1, py1, px2, py2, fill="blue", width=2)

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

            # Key cua cac doan bi ep buoc la tab (vd tab hinh tron
            # lon), dung khi xuat gcode de biet doan nao phai cat
            # voi SPEED_TAB_FEED bat ke do dai cua no
            self._forced_tab_keys = set()

            text = self.text_input.get("1.0", "end")

            # Stack chung cho ADD va ROTATE: moi lan ADD/ROTATE day
            # them 1 lop (dx, dy, angle, label), moi lan END chi bo
            # lop cuoi cung (giong dong ngoac). Delta/goc hien hanh
            # = tong tat ca cac lop dang con trong stack.
            delta_stack = []
            known_cmds = {"C", "R", "RC", "LH", "LV", "L", "A", "P", "M"}

            for line in text.strip().splitlines():
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                cmd = parts[0]

                if cmd == "ADD":
                    if len(parts) < 3:
                        continue
                    try:
                        dx, dy = float(parts[1]), float(parts[2])
                    except ValueError:
                        continue
                    label = " ".join(parts[3:])
                    delta_stack.append((dx, dy, 0.0, label))
                    cum_x = sum(d[0] for d in delta_stack)
                    cum_y = sum(d[1] for d in delta_stack)
                    self._draw_add_label(cum_x, cum_y, label)
                    continue

                if cmd == "ROTATE":
                    if len(parts) < 2:
                        continue
                    try:
                        angle = float(parts[1])
                    except ValueError:
                        continue
                    delta_stack.append((0.0, 0.0, angle, None))
                    continue

                if cmd == "END":
                    if delta_stack:
                        delta_stack.pop()
                    continue

                # Dong khong dung format (cmd la, sai so tham so,
                # sai kieu du lieu, ...) -> bo qua, khong gian doan
                # toan bo preview
                if cmd not in known_cmds:
                    continue

                try:
                    nums = list(map(float, parts[1:]))
                except ValueError:
                    continue

                # Segment "tho", tinh truoc khi ap delta/xoay - de
                # xoay dung cho MOI loai hinh (ke ca R, RC von
                # khong the bieu dien bang x,y,w,h sau khi xoay
                # lech truc)
                raw_segments, raw_tab_flags = self._shape_to_segments(
                    cmd, nums
                )

                delta_x = sum(d[0] for d in delta_stack)
                delta_y = sum(d[1] for d in delta_stack)
                total_angle = sum(d[2] for d in delta_stack)

                segments = self._apply_transform(
                    raw_segments, delta_x, delta_y, total_angle
                )

                # Ghi nhan key cua cac doan bi ep buoc la tab, tinh
                # SAU khi transform de khop dung toa do cuoi cung
                for seg, is_tab in zip(segments, raw_tab_flags):
                    if is_tab:
                        self._forced_tab_keys.add(self._segment_key(seg))

                self.shapes.append((cmd, segments))
                self.draw_shape(cmd, segments)

            self._draw_speed_tab_marks()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _apply_transform(self, segments, dx, dy, angle_deg):
        # Xoay (chieu kim dong ho) quanh goc toa do roi dich chuyen
        # (dx, dy). ADD dich chuyen truoc roi ROTATE xoay quanh
        # chinh diem da dich chuyen do rut gon ve mat toan hoc
        # thanh: xoay diem goc quanh (0,0) roi cong dx, dy. Ap dung
        # cho tung diem cua segment nen dung cho moi loai hinh.
        if angle_deg == 0 and dx == 0 and dy == 0:
            return segments

        theta = math.radians(angle_deg)
        cos_t, sin_t = math.cos(theta), math.sin(theta)

        result = []
        for x1, y1, x2, y2 in segments:
            nx1 = x1 * cos_t + y1 * sin_t + dx
            ny1 = -x1 * sin_t + y1 * cos_t + dy
            nx2 = x2 * cos_t + y2 * sin_t + dx
            ny2 = -x2 * sin_t + y2 * cos_t + dy
            result.append((nx1, ny1, nx2, ny2))
        return result

    def _speed_tab_centers(self, length, threshold, distance):
        # Vi tri (tinh tu diem dau doan thang, theo mm) cua tam moi
        # tab, cu moi "distance" mm lai co 1 tab, chi ap dung cho
        # doan dai hon "threshold"
        if length <= threshold or distance <= 0:
            return []

        count = int(length // distance)
        if count < 1:
            return []

        return [
            distance / 2 + i * distance
            for i in range(count)
            if distance / 2 + i * distance < length
        ]

    def _draw_speed_tab_marks(self):
        # Highlight vi tri se bi speed-tab bang dau X tren canvas,
        # de de hinh dung truoc khi cat that. Dung cung logic gop
        # trung/gop overlap nhu generate_gcode de vi tri khop thuc te.
        if not self.SPEED_TAB_ENABLED:
            return

        threshold = self.SPEED_TAB_THRESHOLD
        distance = self.SPEED_TAB_DISTANCE
        tab_length = self.SPEED_TAB_LENGTH

        if tab_length <= 0:
            return

        segments = self._shapes_to_segments()
        segments = self._remove_duplicate_segments(segments)
        segments = self._merge_collinear_overlaps(segments)

        forced_keys = getattr(self, "_forced_tab_keys", set())

        for x1, y1, x2, y2 in segments:

            # Doan bi ep buoc la tab (vd tab hinh tron lon): danh
            # dau nguyen ca doan, khong chia nho theo nguong thong
            # thuong
            if self._segment_key((x1, y1, x2, y2)) in forced_keys:
                self._draw_x_mark((x1 + x2) / 2, (y1 + y2) / 2)
                continue

            length = math.hypot(x2 - x1, y2 - y1)
            centers = self._speed_tab_centers(length, threshold, distance)
            dx, dy = x2 - x1, y2 - y1

            for t in centers:
                self._draw_x_mark(x1 + dx * (t / length),
                                   y1 + dy * (t / length))

    def _draw_x_mark(self, x, y, size_px=5, color="magenta"):
        # Kich thuoc co dinh theo pixel (khong theo mm), de luon
        # nhin ro du zoom vao/ra viewport khac nhau
        px, py = self.to_canvas(x, y)
        self.canvas.create_line(px - size_px, py - size_px,
                                 px + size_px, py + size_px,
                                 fill=color, width=2)
        self.canvas.create_line(px - size_px, py + size_px,
                                 px + size_px, py - size_px,
                                 fill=color, width=2)

    def _draw_add_label(self, x, y, label):
        # Cham danh dau + label cho lop ADD, de nguoi dung de hinh
        # dung lop delta nay ap dung tu dau tren canvas
        px, py = self.to_canvas(x, y)
        self.canvas.create_oval(px - 3, py - 3, px + 3, py + 3,
                                 fill="red", outline="")
        if label:
            self.canvas.create_text(px + 5, py - 5, text=label,
                                     font=self.ADD_LABEL_FONT,
                                     anchor="sw", fill="red")

    def draw_shape(self, cmd, segments):
        colors = {"C": "black", "A": "black", "R": "green",
                  "RC": "green", "P": "purple", "M": "orange"}
        color = colors.get(cmd, "black")

        for x1, y1, x2, y2 in segments:
            px1, py1 = self.to_canvas(x1, y1)
            px2, py2 = self.to_canvas(x2, y2)
            self.canvas.create_line(px1, py1, px2, py2,
                                     fill=color, width=2)

    def _arc_segments_with_tabs(self, cx, cy, r, s_alpha, e_alpha):
        # Sinh segment cho 1 cung tu s_alpha den e_alpha (hinh tron
        # la truong hop dac biet voi s_alpha=0, e_alpha=360). Goc
        # kieu la ban: 0 = huong len (+y), 90 = huong phai (+x),
        # 180 = huong xuong (-y), 270 = huong trai (-x). Doi sang
        # goc toan hoc: math_angle = 90 - bearing.
        #
        # Neu ban kinh du lon (duong kinh > ARC_TAB_DIAMETER_
        # THRESHOLD) va speed tab dang bat, chen them diem gay
        # chinh xac tai ranh gioi tab (theo do dai cung, cu moi
        # SPEED_TAB_DISTANCE mm lai co 1 tab dai SPEED_TAB_LENGTH
        # mm), de cac doan trong vung tab co the danh dau rieng va
        # cat voi SPEED_TAB_FEED. Tinh toan hoan toan theo "vi tri
        # doc theo cung" (mm, tu 0 den do dai cung) de tranh cac
        # van de wraparound/chieu quet cua bearing.
        #
        # Tra ve (segments, tab_flags): tab_flags[i] = True neu
        # segments[i] nam trong vung tab.
        span = e_alpha - s_alpha

        if abs(span) < 1e-9:
            return [], []

        circumference = 2 * math.pi * r
        arc_length = abs(span) / 360 * circumference
        diameter = 2 * r

        segment_count = max(2, round(abs(span) / 360 * 60))
        base_positions = [
            i / segment_count * arc_length for i in range(segment_count + 1)
        ]

        tab_active = (
            self.SPEED_TAB_ENABLED
            and diameter > self.ARC_TAB_DIAMETER_THRESHOLD
            and self.SPEED_TAB_LENGTH > 0
            and self.SPEED_TAB_DISTANCE > 0
        )

        tab_ranges = []
        if tab_active:
            distance, length = self.SPEED_TAB_DISTANCE, self.SPEED_TAB_LENGTH
            half = length / 2
            count = int(arc_length // distance)
            for i in range(count):
                center = distance / 2 + i * distance
                if center < arc_length:
                    tab_ranges.append((center - half, center + half))

        # Diem gay chinh xac tai dau/cuoi moi tab, de doan tab co
        # dung do dai cau hinh, khong doi do phan giai vung khac
        extra_positions = [p for s, e in tab_ranges for p in (s, e)]

        all_positions = sorted(set(
            round(max(0.0, min(arc_length, p)), 6)
            for p in base_positions + extra_positions
        ))

        points = []
        for pos in all_positions:
            bearing = s_alpha + (pos / arc_length) * span
            math_angle = math.radians(90 - bearing)
            x = cx + r * math.cos(math_angle)
            y = cy + r * math.sin(math_angle)
            points.append((pos, x, y))

        segments, tab_flags = [], []
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i + 1]
            mid_pos = (p1[0] + p2[0]) / 2

            segments.append((p1[1], p1[2], p2[1], p2[2]))
            tab_flags.append(any(s <= mid_pos <= e for s, e in tab_ranges))

        return segments, tab_flags

    def _shape_to_segments(self, cmd, nums):

        segments = []

        if cmd == "L":
            x1, y1, x2, y2 = nums
            segments.append((x1, y1, x2, y2))

        elif cmd == "LH":
            x, y, length = nums
            segments.append((x, y, x + length, y))

        elif cmd == "LV":
            x, y, length = nums
            segments.append((x, y, x, y + length))

        elif cmd == "R":
            x, y, w, h = nums
            segments.extend([
                (x, y, x + w, y), (x + w, y, x + w, y + h),
                (x + w, y + h, x, y + h), (x, y + h, x, y),
            ])

        elif cmd == "RC":
            cx, cy, w, h = nums
            x, y = cx - w / 2, cy - h / 2
            segments.extend([
                (x, y, x + w, y), (x + w, y, x + w, y + h),
                (x + w, y + h, x, y + h), (x, y + h, x, y),
            ])

        elif cmd == "C":
            cx, cy, r = nums
            arc_segments, arc_tab_flags = (
                self._arc_segments_with_tabs(cx, cy, r, 0, 360)
            )
            segments.extend(arc_segments)

        elif cmd == "A":
            cx, cy, r, s_alpha, e_alpha = nums
            arc_segments, arc_tab_flags = (
                self._arc_segments_with_tabs(cx, cy, r, s_alpha, e_alpha)
            )
            segments.extend(arc_segments)

        elif cmd == "P":
            points = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
            n = len(points)
            for i in range(n):
                p1, p2 = points[i], points[(i + 1) % n]
                segments.append((p1[0], p1[1], p2[0], p2[1]))

        elif cmd == "M":
            points = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
            # Khong noi diem cuoi ve diem dau (khac voi P)
            for i in range(len(points) - 1):
                p1, p2 = points[i], points[i + 1]
                segments.append((p1[0], p1[1], p2[0], p2[1]))

        if cmd in ("C", "A"):
            tab_flags = arc_tab_flags
        else:
            tab_flags = [False] * len(segments)

        return segments, tab_flags

    def _shapes_to_segments(self):
        segments = []
        for cmd, shape_segments in self.shapes:
            segments.extend(shape_segments)
        return segments

    def _segment_key(self, segment):
        x1, y1, x2, y2 = segment
        # Lam tron de tranh floating point
        p1, p2 = (round(x1, 6), round(y1, 6)), (round(x2, 6), round(y2, 6))
        # A->B va B->A la cung segment
        return (p1, p2) if p1 <= p2 else (p2, p1)

    def _remove_duplicate_segments(self, segments):
        result, seen = [], set()
        for segment in segments:
            key = self._segment_key(segment)
            if key in seen:
                continue
            seen.add(key)
            result.append(segment)
        return result

    def _merge_collinear_overlaps(self, segments):
        # Gop cac doan cung phuong (collinear) bi chong lan thanh 1
        # doan duy nhat, tranh cat lap cung mot vi tri.
        if not segments:
            return segments

        EPS = 1e-6
        groups, order = {}, []

        for x1, y1, x2, y2 in segments:
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 1e-9:
                continue

            ux, uy = dx / length, dy / length
            # Canonical hoa huong, tranh (ux,uy) va (-ux,-uy) bi
            # tach thanh 2 nhom khac nhau tren cung 1 duong thang
            if ux < -EPS or (abs(ux) <= EPS and uy < 0):
                ux, uy = -ux, -uy

            # He so vuong goc, phan biet cac duong song song nhau
            c = round(x1 * uy - y1 * ux, 6)
            key = (round(ux, 6), round(uy, 6), c)

            if key not in groups:
                groups[key] = {"origin": (x1, y1), "dir": (ux, uy),
                               "intervals": []}
                order.append(key)

            origin = groups[key]["origin"]
            gux, guy = groups[key]["dir"]
            t1 = (x1 - origin[0]) * gux + (y1 - origin[1]) * guy
            t2 = (x2 - origin[0]) * gux + (y2 - origin[1]) * guy
            groups[key]["intervals"].append((min(t1, t2), max(t1, t2)))

        result = []
        for key in order:
            group = groups[key]
            intervals = sorted(group["intervals"])

            merged = []
            for t1, t2 in intervals:
                if merged and t1 <= merged[-1][1] + EPS:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], t2))
                else:
                    merged.append((t1, t2))

            ox, oy = group["origin"]
            ux, uy = group["dir"]
            for t1, t2 in merged:
                if t2 - t1 < 1e-9:
                    continue
                result.append((ox + ux * t1, oy + uy * t1,
                               ox + ux * t2, oy + uy * t2))

        return result

    def _distance_sq(self, p1, p2):
        dx, dy = p1[0] - p2[0], p1[1] - p2[1]
        return dx * dx + dy * dy

    def _optimize_segments_greedy(self, segments):
        if not segments:
            return []

        remaining = segments.copy()
        result = []
        current = (0.0, 0.0)  # Diem bat dau

        while remaining:
            best_index, best_distance, best_reversed = None, float("inf"), False

            for i, segment in enumerate(remaining):
                x1, y1, x2, y2 = segment
                d1 = self._distance_sq(current, (x1, y1))
                d2 = self._distance_sq(current, (x2, y2))

                if d1 < best_distance:
                    best_distance, best_index, best_reversed = d1, i, False
                if d2 < best_distance:
                    best_distance, best_index, best_reversed = d2, i, True

            segment = remaining.pop(best_index)
            x1, y1, x2, y2 = segment

            if best_reversed:
                segment = (x2, y2, x1, y1)

            result.append(segment)
            current = (segment[2], segment[3])

        return result

    def generate_gcode(self):

        self.preview()

        speed_x = float(self.speed_x_var.get())
        speed_y = float(self.speed_y_var.get())
        power = float(self.power_var.get())

        speed_tab_enabled = self.SPEED_TAB_ENABLED
        speed_tab_threshold = self.SPEED_TAB_THRESHOLD
        speed_tab_distance = self.SPEED_TAB_DISTANCE
        speed_tab_length = self.SPEED_TAB_LENGTH
        speed_tab_feed = self.SPEED_TAB_FEED

        short_slow_enabled = self.SHORT_SLOW_ENABLED
        short_slow_threshold = self.SHORT_SLOW_THRESHOLD
        short_slow_percent = self.SHORT_SLOW_PERCENT

        forced_tab_keys = getattr(self, "_forced_tab_keys", set())

        lines = ["G21", "G90"]

        # B1: tat ca shape -> line segments
        segments = self._shapes_to_segments()
        segments = self._remove_duplicate_segments(segments)

        # Gop cac doan chong lan tren cung 1 duong thang, tranh cat
        # lap lai nhung vi tri da cat
        segments = self._merge_collinear_overlaps(segments)

        # B2: greedy tim duong di
        segments = self._optimize_segments_greedy(segments)

        # Xuat G-code
        current = None
        laser_on = False

        for x1, y1, x2, y2 in segments:
            end = (x2, y2)

            # Neu segment moi bat dau dung tai vi tri hien tai thi
            # co the tiep tuc cat
            connected = (
                current is not None
                and abs(current[0] - x1) < 1e-6
                and abs(current[1] - y1) < 1e-6
            )

            if not connected:
                if laser_on:
                    lines.append("M5")
                    laser_on = False
                lines.append(f"G0 X{x1:.3f} Y{y1:.3f}")
                lines.append(f"M3 S{power}")
                laser_on = True

            elif not laser_on:
                lines.append(f"G0 X{x1:.3f} Y{y1:.3f}")
                lines.append(f"M3 S{power}")
                laser_on = True

            # Cat segment
            dx, dy = x2 - x1, y2 - y1
            length = (dx ** 2 + dy ** 2) ** 0.5

            # Doan bi ep buoc la tab (vd tab hinh tron lon, da chia
            # san dung do dai): cat nguyen ca doan voi speed_tab_
            # feed, bo qua moi logic feed khac vi ban than no da la
            # 1 doan tab hoan chinh roi.
            if self._segment_key((x1, y1, x2, y2)) in forced_tab_keys:
                lines.append(f"G1 X{x2:.3f} Y{y2:.3f} F{speed_tab_feed:.3f}")
                current = end
                continue

            if length > 1e-9:
                ux, uy = abs(dx) / length, abs(dy) / length
                EPS = 1e-6

                if uy <= EPS:
                    feed = speed_x  # Doan ngang thuan tuy
                elif ux <= EPS:
                    feed = speed_y  # Doan doc thuan tuy
                else:
                    # Doan cheo: dung min(speed_x, speed_y) truc
                    # tiep, tranh cong thuc phan tich truc cu lam
                    # doan cheo bi cat nhanh hon (khong xuyen het)
                    feed = min(speed_x, speed_y)
            else:
                feed = speed_x

            # Giam toc cho doan ngan (vd mong nho), tranh cat khong
            # dut het vat lieu. Khong anh huong nhieu den tong thoi
            # gian vi cac doan nay von da rat ngan.
            if short_slow_enabled and length < short_slow_threshold:
                feed = feed * short_slow_percent / 100

            # Speed tab: doan giua di nhanh (V3) de khong cat xuyen,
            # cu moi speed_tab_distance mm tren doan dai hon nguong
            # se co 1 tab, moi tab dai speed_tab_length mm
            tab_centers = (
                self._speed_tab_centers(length, speed_tab_threshold,
                                         speed_tab_distance)
                if speed_tab_enabled and speed_tab_length > 0
                else []
            )

            if tab_centers:
                half_tab = speed_tab_length / 2
                cursor = 0.0

                for center in tab_centers:
                    tab_start = max(cursor, center - half_tab)
                    tab_end = min(length, center + half_tab)
                    if tab_end <= tab_start:
                        continue

                    if tab_start > cursor:
                        px = x1 + dx * (tab_start / length)
                        py = y1 + dy * (tab_start / length)
                        lines.append(f"G1 X{px:.3f} Y{py:.3f} F{feed:.3f}")

                    px2 = x1 + dx * (tab_end / length)
                    py2 = y1 + dy * (tab_end / length)
                    lines.append(
                        f"G1 X{px2:.3f} Y{py2:.3f} F{speed_tab_feed:.3f}"
                    )
                    cursor = tab_end

                lines.append(f"G1 X{x2:.3f} Y{y2:.3f} F{feed:.3f}")
            else:
                lines.append(f"G1 X{x2:.3f} Y{y2:.3f} F{feed:.3f}")

            current = end

        if laser_on:
            lines.append("M5")

        with open("cut_plan.gcode", "w") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("Done", "Generated cut_plan.gcode")

    def generate_bounds_gcode(self):

        # B1: dam bao self.shapes khop noi dung text hien tai, roi
        # tim min/max x, y tren toan bo segment cua tat ca cac hinh
        self.preview()

        segments = self._shapes_to_segments()
        if not segments:
            messagebox.showerror(
                "Error", "Khong co hinh nao de tinh vung hoat dong"
            )
            return

        xs, ys = [], []
        for x1, y1, x2, y2 in segments:
            xs.extend([x1, x2])
            ys.extend([y1, y2])

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # B2: generate gcode ve dau + (2 doan thang, moi doan dai
        # BOUNDS_MARK_LENGTH mm) tai 4 goc vung hoat dong, cong
        # suat va toc do chi du de tao vet cat nhe, khong cat sau
        half = self.BOUNDS_MARK_LENGTH / 2
        power = self.BOUNDS_MARK_POWER
        feed = self.BOUNDS_MARK_FEED

        corners = [(min_x, min_y), (max_x, min_y),
                   (min_x, max_y), (max_x, max_y)]

        lines = ["G21", "G90"]

        for cx, cy in corners:
            # Doan ngang cua dau +
            lines.append(f"G0 X{cx - half:.3f} Y{cy:.3f}")
            lines.append(f"M3 S{power}")
            lines.append(f"G1 X{cx + half:.3f} Y{cy:.3f} F{feed}")
            lines.append("M5")

            # Doan doc cua dau +
            lines.append(f"G0 X{cx:.3f} Y{cy - half:.3f}")
            lines.append(f"M3 S{power}")
            lines.append(f"G1 X{cx:.3f} Y{cy + half:.3f} F{feed}")
            lines.append("M5")

        with open("bounds_plan.gcode", "w") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("Done", "Generated bounds_plan.gcode")