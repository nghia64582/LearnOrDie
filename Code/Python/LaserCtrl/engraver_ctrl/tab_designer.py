import tkinter as tk
from tkinter import ttk, messagebox
import math

from engraver_ctrl.paths import CUT_PLAN_GCODE_PATH
from engraver_ctrl.collision import Collider
from common.ui import (
    ui_font, mono_font, canvas_font, make_button, SIZE_SM,
    JM_HIGHLIGHT, JF_HIGHLIGHT,
)
from engraver_ctrl.dsl_highlight import polygons_from_joint_segments
from engraver_ctrl.dsl_card_panel import CardPanel
from engraver_ctrl.dsl_joint import (
    THICKNESS, DEFAULT_TEETH_LENGTH,
    apply_joints, parse_joint_file, collect_preview_warnings,
    world_mark_corners, world_mark_center, pair_color, group_marks,
    insert_j_line, next_joint_name, add_local_coords,
)


class DesignerTab(ttk.Frame):

    GRID_MM = 10

    # Speed tab: doan thang dai hon nguong, phan giua di nhanh (V3)
    # de khong cat xuyen het vat lieu
    SPEED_TAB_ENABLED = True
    SPEED_TAB_THRESHOLD = 20  # mm
    SPEED_TAB_DISTANCE = 20  # mm, khoang cach giua 2 tab lien tiep
    SPEED_TAB_LENGTH = 0.5  # mm
    SPEED_TAB_FEED = 350  # mm/min (V3)

    # Arc tab: cung (ke ca hinh tron, coi la cung 0-360 do) co ban
    # kinh > nguong nay se duoc chen tab theo do dai cung (dung
    # chung SPEED_TAB_* o tren), vi cac doan thang xap xi cung
    # thuong qua ngan de tu kich hoat tab theo do dai doan thang
    # thong thuong
    ARC_TAB_DIAMETER_THRESHOLD = 10  # mm

    # Short segment slowdown: doan ngan hon nguong se cat cham lai,
    # tranh cat khong dut het vat lieu
    SHORT_SLOW_ENABLED = True
    SHORT_SLOW_THRESHOLD = 15  # mm
    SHORT_SLOW_PERCENT = 60  # %

    # Font cho label cua tung lop ADD ve tren canvas (shared UI family)
    ADD_LABEL_FONT = None  # resolved in __init__ via canvas_font()

    # Bounds mark: ve dau + tai 4 goc vung hoat dong (min/max x, y)
    # de kiem tra pham vi cat truoc khi chay that
    BOUNDS_MARK_LENGTH = 4  # mm, do dai moi doan cua dau +
    BOUNDS_MARK_POWER = 200
    BOUNDS_MARK_FEED = 600  # mm/min

    # Toc do di chuyen khong cat (G0), dung de uoc luong thoi gian
    # chay khi khong co tham so F (chi G1 moi co F)
    GCODE_RAPID_FEED = 6000  # mm/min

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.font = getattr(app, "font", None) or ui_font(SIZE_SM)
        self.ADD_LABEL_FONT = canvas_font()
        self.shapes = []
        self.canvas_width = 1000
        self.canvas_height = 700
        # Trang thai view: zoom = 1 la vua khit (Fit) toan bo hinh
        self.zoom = 1.0
        self.ZOOM_MIN = 1.0
        self.ZOOM_MAX = 20.0
        self._add_labels = []
        self._syncing_slider = False
        self._resize_job = None
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.view_left, self.view_bottom = -10.0, -10.0
        self.view_right, self.view_top = 100.0, 100.0
        # Drag & drop component (khoi ADD ... END)
        self.shape_adds = []      # moi shape -> tuple dong ADD (ngoai->trong)
        self.add_blocks = {}      # dong ADD -> {dx, dy, label, cum}
        self.selected_add = None  # dong (1-based) cua ADD dang chon
        self._drag = None
        self.joint_marks = []
        self.joint_warnings = []
        self._mark_mode = False
        self._mark_drag = None
        self.build_gui()

    def build_gui(self):

        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        right_frame = tk.Frame(self)
        right_frame.pack(side="right", fill="both", expand=True)

        # --- Help button ---
        top_btn_frame = tk.Frame(left_frame)
        top_btn_frame.pack(fill="x")
        make_button(top_btn_frame, "Help", command=self.show_help).pack(side="left")

        # --- Shapes: card list (default) or raw DSL ---
        tk.Label(left_frame, text="Shapes", font=self.font).pack(anchor="w")
        mode_row = ttk.Frame(left_frame)
        mode_row.pack(fill="x", pady=(0, 2))
        self.view_mode_var = tk.StringVar(value="cards")
        ttk.Radiobutton(
            mode_row, text="Cards", value="cards",
            variable=self.view_mode_var, command=self._on_view_mode,
        ).pack(side="left")
        ttk.Radiobutton(
            mode_row, text="Raw DSL", value="raw",
            variable=self.view_mode_var, command=self._on_view_mode,
        ).pack(side="left", padx=(4, 8))
        self.add_card_btn = make_button(
            mode_row, "Add card", command=self._on_add_card,
        )
        self.add_card_btn.pack(side="left")

        editor = ttk.Frame(left_frame)
        # fill=x only — do not expand vertically or geometry will undo height=14
        editor.pack(fill="x", pady=(0, 2))
        self.text_input = tk.Text(
            editor, width=40, height=14, font=mono_font(SIZE_SM), undo=True,
            wrap="none",
        )
        self.text_scroll = ttk.Scrollbar(
            editor, orient="vertical", command=self.text_input.yview,
        )
        self.text_input.configure(yscrollcommand=self.text_scroll.set)
        self.text_input.grid(row=0, column=0, sticky="nsew")
        self.text_scroll.grid(row=0, column=1, sticky="ns")
        editor.columnconfigure(0, weight=1)
        editor.rowconfigure(0, weight=1)

        self.card_panel = CardPanel(
            editor, font=self.font,
            on_commit=self._on_cards_commit,
            on_preview=self.preview_keep_scroll,
            on_ctrl_return=lambda: self.preview(),
        )
        self._last_dsl = None

        sample = ("C 50 50 30\nR 20 30 40 50\nRC 120 100 50 30\n"
                   "LV 10 10 100\nLH 50 50 80\nL 10 10 100 100\n")
        self.text_input.insert("1.0", sample)
        self.text_input.bind("<Control-Return>", lambda e: self.preview())
        self._load_cards_from_current_text(wrap=True)
        self._show_card_widgets()

        # --- View / Zoom ---
        view_frame = tk.LabelFrame(left_frame, text="View", font=self.font)
        view_frame.pack(fill="x", pady=5)
        make_button(view_frame, "Fit", command=self.fit_view).grid(row=0, column=0, padx=2)
        tk.Label(view_frame, text="Zoom").grid(row=0, column=1)
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_scale = tk.Scale(view_frame, from_=self.ZOOM_MIN,
                                   to=self.ZOOM_MAX, resolution=0.1,
                                   orient="horizontal", length=200,
                                   variable=self.zoom_var,
                                   command=self._on_zoom_slider)
        self.zoom_scale.grid(row=0, column=2, sticky="we")
        self.no_overlap_var = tk.BooleanVar(value=True)
        self.no_cross_x_var = tk.BooleanVar(value=True)
        self.no_cross_y_var = tk.BooleanVar(value=True)
        chk = tk.Frame(view_frame)
        chk.grid(row=1, column=0, columnspan=3, sticky="w")
        for txt, var in (("No overlap", self.no_overlap_var),
                         ("No cross X axis", self.no_cross_x_var),
                         ("No cross Y axis", self.no_cross_y_var)):
            tk.Checkbutton(chk, text=txt, variable=var).pack(side="left")
        # Do dai co dinh + font mono de label khong lam panel co gian
        self.drag_status_var = tk.StringVar(value="")
        tk.Label(view_frame, textvariable=self.drag_status_var,
                 font=mono_font(SIZE_SM), width=40, anchor="w")\
            .grid(row=2, column=0, columnspan=3, sticky="w")

        # --- Joints (J marks -> JM/JF) ---
        joint_frame = tk.LabelFrame(left_frame, text="Joints", font=self.font)
        joint_frame.pack(fill="x", pady=5)
        tk.Label(
            joint_frame,
            text=f"Thickness {THICKNESS:g} mm, tooth {DEFAULT_TEETH_LENGTH:g} mm",
            fg="gray",
        ).pack(anchor="w")
        jbtn = tk.Frame(joint_frame)
        jbtn.pack(fill="x", pady=(2, 0))
        make_button(jbtn, "Apply joints", command=self.apply_joints)\
            .pack(side="left", padx=2)
        self.mark_mode_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            jbtn, text="Mark joint", variable=self.mark_mode_var,
            command=self._toggle_mark_mode,
        ).pack(side="left", padx=2)
        self.joint_status_var = tk.StringVar(value="")
        tk.Label(
            joint_frame, textvariable=self.joint_status_var,
            font=self.font, wraplength=300, justify="left", fg="#8a4b08",
        ).pack(anchor="w", pady=(2, 0))

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
        make_button(btn_frame, "Preview (Ctrl+Enter)", command=self.preview)\
            .pack(side="left", padx=2)
        make_button(btn_frame, "Generate GCODE", command=self.generate_gcode)\
            .pack(side="left", padx=2)
        make_button(btn_frame, "Ve vung hoat dong", command=self.generate_bounds_gcode)\
            .pack(side="left", padx=2)

        # --- Thoi gian uoc luong ---
        self.gcode_time_var = tk.StringVar(value="")
        tk.Label(left_frame, textvariable=self.gcode_time_var,
                 font=self.font).pack(anchor="w", pady=(0, 5))

        # --- Canvas ---
        self.canvas = tk.Canvas(right_frame, bg="white",
                                 width=self.canvas_width,
                                 height=self.canvas_height,
                                 highlightthickness=0)
        self.hbar = tk.Scrollbar(right_frame, orient="horizontal",
                                 command=self.canvas.xview)
        self.vbar = tk.Scrollbar(right_frame, orient="vertical",
                                 command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hbar.set,
                              yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="we")
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)
        self.canvas.bind("<ButtonPress-2>",
                         lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B2-Motion>",
                         lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<ButtonPress-1>", self._on_drag_press)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_release)
        self.canvas.bind("<Escape>", self._on_drag_cancel)
        self.canvas.bind("<Control-z>", self._on_undo)
        self.canvas.bind("<Control-Z>", self._on_undo)


        self.preview()

    def get_dsl(self):
        """Current document DSL (flushes card edits when in card mode)."""
        return self._dsl_text()

    @property
    def card_mode(self):
        return getattr(self, "view_mode_var", None) is not None and \
            self.view_mode_var.get() == "cards"

    def set_view_mode(self, mode):
        """Switch the Shapes panel between 'cards' and 'raw'."""
        self.view_mode_var.set("cards" if mode == "cards" else "raw")
        self._on_view_mode()

    def _on_add_card(self):
        if self.card_mode:
            self.card_panel.add_card()

    def _on_view_mode(self):
        if self.view_mode_var.get() == "cards":
            self._enter_card_mode()
        else:
            self._enter_raw_mode()

    def _norm_dsl(self, text):
        return (text or "").replace("\r\n", "\n").replace("\r", "\n").strip("\n") + "\n"

    def _set_text_input(self, text, undo=True):
        if text and not text.endswith("\n"):
            text = text + "\n"
        current = self.text_input.get("1.0", "end")
        if self._norm_dsl(current) == self._norm_dsl(text):
            return
        if undo:
            self.text_input.configure(autoseparators=False)
            self.text_input.edit_separator()
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", text)
        if undo:
            self.text_input.edit_separator()
            self.text_input.configure(autoseparators=True)
        self._last_dsl = self._norm_dsl(text)

    def _commit_cards_to_text(self):
        assembled = self.card_panel.assemble()
        self.card_panel.dirty = False
        self._set_text_input(assembled)
        return self.text_input.get("1.0", "end")

    def _load_cards_from_current_text(self, wrap=True):
        text = self.text_input.get("1.0", "end")
        self.card_panel.load_text(text)
        if wrap:
            assembled = self.card_panel.assemble()
            if assembled and self._norm_dsl(assembled) != self._norm_dsl(text):
                self._set_text_input(assembled)
        self.card_panel.dirty = False
        self._last_dsl = self._norm_dsl(self.text_input.get("1.0", "end"))

    def _reload_cards_from_text(self, keep_expand=True):
        if not hasattr(self, "card_panel"):
            return
        text = self.text_input.get("1.0", "end")
        self.card_panel.load_text(text, keep_expand=keep_expand)
        self.card_panel.dirty = False
        self._last_dsl = self._norm_dsl(text)

    def _on_cards_commit(self):
        assembled = self.card_panel.assemble()
        self.card_panel.dirty = False
        self._set_text_input(assembled)

    def _dsl_text(self):
        if not hasattr(self, "card_panel") or not self.card_mode:
            return self.text_input.get("1.0", "end")
        if self.card_panel.dirty:
            return self._commit_cards_to_text()
        current = self.text_input.get("1.0", "end")
        if self._last_dsl is None or self._norm_dsl(current) != self._norm_dsl(self._last_dsl):
            self._reload_cards_from_text()
        return self.text_input.get("1.0", "end")

    def _show_card_widgets(self):
        self.text_input.grid_remove()
        self.text_scroll.grid_remove()
        self.card_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
        try:
            self.add_card_btn.configure(state="normal")
        except tk.TclError:
            pass

    def _show_raw_widgets(self):
        self.card_panel.grid_remove()
        self.text_input.grid(row=0, column=0, sticky="nsew")
        self.text_scroll.grid(row=0, column=1, sticky="ns")
        try:
            self.add_card_btn.configure(state="disabled")
        except tk.TclError:
            pass

    def _enter_card_mode(self):
        if getattr(self.card_panel, "dirty", False):
            self._commit_cards_to_text()
        else:
            self._load_cards_from_current_text(wrap=True)
        self._show_card_widgets()
        if getattr(self, "canvas", None):
            self.preview_keep_scroll()

    def _enter_raw_mode(self):
        if getattr(self.card_panel, "dirty", False):
            self._commit_cards_to_text()
        else:
            # Keep text_input as the assembled document so a cards->raw
            # round trip does not drop the loose-command wrap.
            assembled = self.card_panel.assemble()
            if assembled:
                self._set_text_input(assembled)
        self._show_raw_widgets()

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

            JF x y width height teeth_length first_d
            Mong am: cac lo chu nhat tren dai (x, y, width, height).
            Huong tu dong: canh dai hon la truc doc dai, canh ngan
            la do day. Lo dai teeth_length, cach nhau teeth_length,
            lo dau bat dau cach dau dai first_d. Lo cuoi bi le
            (vuot qua cuoi dai) se bi bo. Chi cat cac lo.

            JM x y width height teeth_length first_d out|in
            Mong duong: duong zigzag (ho, giong M) chay het dai,
            rang trung vi tri voi lo cua JF (cung teeth_length,
            first_d). Do cao rang = do day dai.
            out (+): rang nho ve phia x+width / y+height.
            in  (-): rang nho ve phia x / y (goc cua manh).
            Vd: JF 10 0 3 100 10 0  va  JM 17 0 3 100 10 0 out

            J x y width height NAME [M|F]
            Joint mark (not cut). Place two J with the same NAME inside
            ADD blocks to pair an edge of one piece with a region of
            another. Apply joints expands them to JM/JF (the original
            J lines are commented). Optional M or F forces male/female.
            ROTATE around a J is not supported yet.

            Cards / Raw DSL
            The Shapes panel lists each top-level ADD as a card, or shows
            the full raw DSL. Commands outside any ADD are wrapped into a
            card (named loose, loose_2, ...) when converting to cards.
            Nested ADD stays inside the parent card as text. Add card
            places a new piece at (xmax, 0) or (0, ymax), whichever
            origin is closer to O(0,0). Duplicate uses the same rule
            with the copy's bounding-box centre.

            FIRST
            Danh dau hinh NGAY SAU dong nay se duoc cat truoc tien.
            Nhieu hinh duoc danh dau FIRST se cat theo dung thu tu
            xuat hien trong file. Cac hinh con lai van toi uu
            duong di nhu thuong (greedy), nhung bat dau tu diem
            cuoi cung cua nhom uu tien.

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

            # Vi du FIRST: cat hinh tron nho nay truoc tien
            FIRST
            C 5 5 3

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

    # ------------------------------------------------------------------
    # View transform (world mm -> canvas px). Y huong len, goc O(0,0)
    # trong toa do may. Moi ham ve deu di qua to_canvas().
    # ------------------------------------------------------------------
    @staticmethod
    def compute_extent(points, margin_ratio=0.10, min_size=10.0):
        # Bounding box cua moi diem + goc O(0,0), them margin ~10%
        # moi phia (theo canh lon hon) de luon thay goc va 1 phan
        # goc phan tu am (x<0, y<0)
        xs = [0.0] + [p[0] for p in points]
        ys = [0.0] + [p[1] for p in points]
        left, right = min(xs), max(xs)
        bottom, top = min(ys), max(ys)
        size = max(right - left, top - bottom, min_size)
        m = size * margin_ratio
        return left - m, bottom - m, right + m, top + m

    @staticmethod
    def compute_transform(extent, view_w, view_h, zoom):
        # Tra ve (scale px/mm, offset_x, offset_y, content_w, content_h).
        # zoom = 1: hinh vua khit vung nhin, ti le deu 2 truc, can giua.
        left, bottom, right, top = extent
        ww, wh = right - left, top - bottom
        base = min(view_w / ww, view_h / wh)
        scale = base * zoom
        cw = max(ww * scale, view_w)
        ch = max(wh * scale, view_h)
        ox = (cw - ww * scale) / 2
        oy = (ch - wh * scale) / 2
        return scale, ox, oy, cw, ch

    def to_canvas(self, x, y):
        px = self.offset_x + (x - self.view_left) * self.scale
        py = self.offset_y + (self.view_top - y) * self.scale
        return px, py

    def to_world(self, px, py):
        x = (px - self.offset_x) / self.scale + self.view_left
        y = self.view_top - (py - self.offset_y) / self.scale
        return x, y

    def _visible_size(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            w, h = self.canvas_width, self.canvas_height
        return w, h

    def _update_extent(self):
        pts = []
        for _cmd, segs in self.shapes:
            for x1, y1, x2, y2 in segs:
                pts.append((x1, y1))
                pts.append((x2, y2))
        for x, y, _l in self._add_labels:
            pts.append((x, y))
        for mark in getattr(self, "joint_marks", []):
            if mark.in_rotate or mark.add_line is None:
                continue
            for x, y in world_mark_corners(mark):
                pts.append((x, y))
        (self.view_left, self.view_bottom,
         self.view_right, self.view_top) = self.compute_extent(pts)
        self.view_width = self.view_right - self.view_left
        self.view_height = self.view_top - self.view_bottom

    def render(self, anchor=None):
        # anchor = (screen_x, screen_y, world_x, world_y): giu diem
        # world nay dung yen duoi con tro sau khi zoom
        vw, vh = self._visible_size()
        (self.scale, self.offset_x, self.offset_y,
         cw, ch) = self.compute_transform(
            (self.view_left, self.view_bottom,
             self.view_right, self.view_top), vw, vh, self.zoom)
        self.canvas_width, self.canvas_height = cw, ch
        self.canvas.configure(scrollregion=(0, 0, cw, ch))

        self.draw_grid()
        self._draw_joint_highlights()
        for i, (x, y, label) in enumerate(self._add_labels):
            line = (self._add_label_lines[i]
                    if i < len(self._add_label_lines) else None)
            self._draw_add_label(x, y, label, tag=f"addlbl{line}")
        for i, (cmd, segments) in enumerate(self.shapes):
            self.draw_shape(cmd, segments, tag=f"shape{i}")
        self._draw_joint_marks()
        self._draw_speed_tab_marks()
        self._draw_selection()
        # Dang keo ma bi ve lai (resize/zoom) -> dat lai block vao vi
        # tri dang keo de preview khong bi nhay ve cho cu
        d = getattr(self, "_drag", None)
        if d and d.get("off") and d.get("tags"):
            ox, oy = d["off"]
            for t in d["tags"]:
                self.canvas.move(t, ox * self.scale, -oy * self.scale)
            if d.get("blocked"):
                self.canvas.itemconfigure("selbox", outline="red")

        if anchor is not None:
            sx, sy, wx, wy = anchor
            px, py = self.to_canvas(wx, wy)
            self.canvas.xview_moveto(max(0.0, (px - sx) / cw))
            self.canvas.yview_moveto(max(0.0, (py - sy) / ch))

    def set_zoom(self, zoom, screen_x=None, screen_y=None):
        zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, zoom))
        if screen_x is None:
            vw, vh = self._visible_size()
            screen_x, screen_y = vw / 2, vh / 2
        wx, wy = self.to_world(self.canvas.canvasx(screen_x),
                               self.canvas.canvasy(screen_y))
        self.zoom = zoom
        self._syncing_slider = True
        self.zoom_var.set(round(zoom, 1))
        self._syncing_slider = False
        self.render(anchor=(screen_x, screen_y, wx, wy))

    def fit_view(self):
        self.zoom = 1.0
        self._syncing_slider = True
        self.zoom_var.set(1.0)
        self._syncing_slider = False
        self.render()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def _on_zoom_slider(self, _value):
        if self._syncing_slider:
            return
        z = float(self.zoom_var.get())
        if abs(z - self.zoom) > 1e-9:
            self.set_zoom(z)

    def _on_mouse_wheel(self, event):
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            factor = 1.2
        else:
            factor = 1 / 1.2
        self.set_zoom(self.zoom * factor, event.x, event.y)
        return "break"

    def _on_canvas_resize(self, _event):
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(60, self._resize_render)

    def _resize_render(self):
        self._resize_job = None
        self.render()

    def _grid_step(self):
        # Buoc luoi "dep" nho nhat >= GRID_MM, cach nhau >= ~30px
        for step in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000):
            if step >= self.GRID_MM / 10 and step * self.scale >= 30:
                return step
        return 10000

    def draw_grid(self):
        self.canvas.delete("all")
        step = self._grid_step()

        x = math.floor(self.view_left / step) * step
        while x <= self.view_right:
            px1, py1 = self.to_canvas(x, self.view_bottom)
            px2, py2 = self.to_canvas(x, self.view_top)
            self.canvas.create_line(px1, py1, px2, py2, fill="#dddddd")
            self.canvas.create_text(px1 + 2, py1 - 12,
                                     text=f"{x:g}", font=canvas_font(),
                                     anchor="nw")
            x += step

        y = math.floor(self.view_bottom / step) * step
        while y <= self.view_top:
            px1, py1 = self.to_canvas(self.view_left, y)
            px2, py2 = self.to_canvas(self.view_right, y)
            self.canvas.create_line(px1, py1, px2, py2, fill="#dddddd")
            self.canvas.create_text(px1 + 2, py1, text=f"{y:g}",
                                     font=canvas_font(), anchor="nw")
            y += step

        if self.view_bottom <= 0 <= self.view_top:
            px1, py1 = self.to_canvas(self.view_left, 0)
            px2, py2 = self.to_canvas(self.view_right, 0)
            self.canvas.create_line(px1, py1, px2, py2, fill="red", width=2)

        if self.view_left <= 0 <= self.view_right:
            px1, py1 = self.to_canvas(0, self.view_bottom)
            px2, py2 = self.to_canvas(0, self.view_top)
            self.canvas.create_line(px1, py1, px2, py2, fill="blue", width=2)

        ox, oy = self.to_canvas(0, 0)
        self.canvas.create_oval(ox - 4, oy - 4, ox + 4, oy + 4,
                                 outline="black", width=2)
        self.canvas.create_text(ox - 4, oy + 4, text="O(0,0)",
                                 font=canvas_font(bold=True), anchor="ne")

    def preview(self):
        try:
            self.shapes = []
            self._add_labels = []
            self._add_label_lines = []
            self.shape_adds = []
            self.add_blocks = {}

            # Key cua cac doan bi ep buoc la tab (vd tab hinh tron
            # lon), dung khi xuat gcode de biet doan nao phai cat
            # voi SPEED_TAB_FEED bat ke do dai cua no
            self._forced_tab_keys = set()

            # Key -> (thu tu uu tien, thu tu doan trong hinh) cua
            # cac doan thuoc hinh duoc danh dau "FIRST" (dong FIRST
            # ap dung cho hinh ke tiep, cat truoc theo dung thu tu
            # xuat hien trong file)
            self._priority_keys = {}

            text = self._dsl_text()

            # Stack chung cho ADD va ROTATE: moi lan ADD/ROTATE day
            # them 1 lop (dx, dy, angle, label), moi lan END chi bo
            # lop cuoi cung (giong dong ngoac). Delta/goc hien hanh
            # = tong tat ca cac lop dang con trong stack.
            delta_stack = []
            known_cmds = {"C", "R", "RC", "LH", "LV", "L", "A", "P", "M",
                          "JF", "JM"}

            # "FIRST" danh dau hinh KE TIEP se duoc cat truoc; cac
            # hinh duoc danh dau nhu vay cat theo dung thu tu xuat
            # hien trong file (priority_counter tang dan)
            next_is_priority = False
            priority_counter = 0

            # Duyet theo so dong that (1-based) cua Text widget de
            # map tung hinh ve dong ADD chua no (phuc vu keo tha)
            for lineno, line in enumerate(text.splitlines(), start=1):
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                cmd = parts[0]

                if cmd == "FIRST":
                    next_is_priority = True
                    continue

                if cmd == "ADD":
                    if len(parts) < 3:
                        continue
                    try:
                        dx, dy = float(parts[1]), float(parts[2])
                    except ValueError:
                        continue
                    label = " ".join(parts[3:])
                    delta_stack.append((dx, dy, 0.0, label, lineno))
                    cum_x = sum(d[0] for d in delta_stack)
                    cum_y = sum(d[1] for d in delta_stack)
                    self._add_labels.append((cum_x, cum_y, label))
                    self._add_label_lines.append(lineno)
                    self.add_blocks[lineno] = {
                        "dx": dx, "dy": dy, "label": label,
                        "cum": (cum_x, cum_y)}
                    continue

                if cmd == "ROTATE":
                    if len(parts) < 2:
                        continue
                    try:
                        angle = float(parts[1])
                    except ValueError:
                        continue
                    delta_stack.append((0.0, 0.0, angle, None, None))
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

                # JM co token huong (out/in/+/-) o cuoi, khong phai so
                # -> tach ra truoc, doi thanh +1 (out) / -1 (in)
                num_parts = parts[1:]
                jm_dir = None
                if cmd == "JM":
                    if len(num_parts) != 7:
                        continue
                    jm_dir = {"out": 1.0, "+": 1.0,
                              "in": -1.0, "-": -1.0}.get(
                                  num_parts[-1].lower())
                    if jm_dir is None:
                        continue
                    num_parts = num_parts[:-1]

                try:
                    nums = list(map(float, num_parts))
                except ValueError:
                    continue

                if cmd == "JF" and len(nums) != 6:
                    continue
                if jm_dir is not None:
                    nums.append(jm_dir)

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

                # Neu hinh nay duoc danh dau bang dong FIRST ngay
                # truoc do, ghi nhan thu tu uu tien cho tung doan
                # cua no (giu dung thu tu doan trong hinh)
                if next_is_priority:
                    for idx, seg in enumerate(segments):
                        self._priority_keys[self._segment_key(seg)] = (
                            priority_counter, idx
                        )
                    priority_counter += 1
                    next_is_priority = False

                self.shapes.append((cmd, segments))
                self.shape_adds.append(tuple(
                    d[4] for d in delta_stack if d[4] is not None))

            self._refresh_joint_marks(text)

            if self.selected_add not in self.add_blocks:
                self.selected_add = None
            # Tinh lai khung nhin theo hinh, ve lai (giu muc zoom)
            self._update_extent()
            self.render()
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

    def _draw_add_label(self, x, y, label, tag=None):
        # Cham danh dau + label cho lop ADD, de nguoi dung de hinh
        # dung lop delta nay ap dung tu dau tren canvas
        px, py = self.to_canvas(x, y)
        self.canvas.create_oval(px - 3, py - 3, px + 3, py + 3,
                                 fill="red", outline="", tags=tag)
        if label:
            self.canvas.create_text(px + 5, py - 5, text=label,
                                     font=self.ADD_LABEL_FONT,
                                     anchor="sw", fill="red", tags=tag)

    def _draw_joint_highlights(self):
        # Preview-only fills under G-code strokes. Same shape{i} tag so
        # drag moves the fill with the block. Does not affect generate_gcode.
        colors = {"JM": JM_HIGHLIGHT, "JF": JF_HIGHLIGHT}
        for i, (cmd, segments) in enumerate(self.shapes):
            fill = colors.get(cmd)
            if not fill:
                continue
            tag = f"shape{i}"
            for poly in polygons_from_joint_segments(cmd, segments):
                coords = []
                for x, y in poly:
                    coords.extend(self.to_canvas(x, y))
                if len(coords) < 6:
                    continue
                self.canvas.create_polygon(
                    *coords, fill=fill, outline="",
                    tags=(tag, "jmjf_hl"),
                )
        self._draw_joint_legend()

    def _draw_joint_legend(self):
        if not any(cmd in ("JM", "JF") for cmd, _segs in self.shapes):
            return
        # Viewport-fixed (uses visible canvas origin), not world coordinates.
        x = self.canvas.canvasx(8)
        y = self.canvas.canvasy(8)
        items = (("JM", JM_HIGHLIGHT), ("JF", JF_HIGHLIGHT))
        for i, (label, color) in enumerate(items):
            bx = x + i * 54
            self.canvas.create_rectangle(
                bx, y, bx + 12, y + 12, fill=color, outline="#888888",
                tags="jmjf_legend",
            )
            self.canvas.create_text(
                bx + 16, y + 6, text=label, anchor="w",
                font=canvas_font(), fill="#333333", tags="jmjf_legend",
            )

    def draw_shape(self, cmd, segments, tag=None):
        colors = {"C": "black", "A": "black", "R": "green",
                  "RC": "green", "P": "purple", "M": "orange",
                  "JF": "red", "JM": "blue"}
        color = colors.get(cmd, "black")

        for x1, y1, x2, y2 in segments:
            px1, py1 = self.to_canvas(x1, y1)
            px2, py2 = self.to_canvas(x2, y2)
            self.canvas.create_line(px1, py1, px2, py2,
                                     fill=color, width=2, tags=tag)

    # ------------------------------------------------------------------
    # Drag & drop component (phase 1: keo tha thu cong, chua co
    # kiem tra giao cat / snap)
    #
    # Quy tac chon: click trai vao 1 hinh -> chon ADD TRONG CUNG chua
    # hinh do. Shift+click hoac Alt+click vao hinh dang thuoc khoi dang
    # chon -> leo len ADD cha (het cha thi quay vong ve trong cung).
    # Click vao hinh thuoc khoi dang chon (khong giu Shift/Alt) -> giu
    # nguyen khoi dang chon, de keo duoc khoi cha sau khi leo len.
    # Hinh nam ngoai moi ADD va vung trong -> bo chon, khong keo.
    #
    # Toa do: diem world = R(tong goc) * p + tong(dx, dy) cua MOI lop
    # trong stack (dx, dy cua ADD khong bi xoay boi ROTATE cha), nen
    # delta keo tren canvas cong thang vao x y cua dong ADD.
    # ------------------------------------------------------------------
    def _block_shape_indices(self, line):
        return [i for i, adds in enumerate(self.shape_adds) if line in adds]

    def _block_child_lines(self, line):
        # Dong ADD con (ke ca chinh no) nam trong khoi
        lines = {line}
        for adds in self.shape_adds:
            if line in adds:
                lines.update(adds[adds.index(line):])
        return lines

    def _block_bbox(self, line):
        xs, ys = [], []
        for i in self._block_shape_indices(line):
            for x1, y1, x2, y2 in self.shapes[i][1]:
                xs += [x1, x2]
                ys += [y1, y2]
        if not xs:
            cx, cy = self.add_blocks[line]["cum"]
            return cx, cy, cx, cy
        return min(xs), min(ys), max(xs), max(ys)

    def _draw_selection(self):
        line = self.selected_add
        if line is None or line not in self.add_blocks:
            return
        x1, y1, x2, y2 = self._block_bbox(line)
        px1, py1 = self.to_canvas(x1, y2)
        px2, py2 = self.to_canvas(x2, y1)
        pad = 4
        self.canvas.create_rectangle(px1 - pad, py1 - pad, px2 + pad,
                                     py2 + pad, outline="#0078d7",
                                     dash=(4, 3), width=2,
                                     tags=("selection", "selbox"))
        blk = self.add_blocks[line]
        self.canvas.create_text(px1 - pad, py1 - pad - 2, anchor="sw",
                                text=f"ADD {self._fmt(blk['dx'])} "
                                     f"{self._fmt(blk['dy'])} "
                                     f"{blk['label']}  (line {line})",
                                fill="#0078d7", font=canvas_font(bold=True),
                                tags="selection")

    def _set_status(self, line, x, y, note=""):
        self.drag_status_var.set(
            f"ADD L{line:<4d} x={x:8.2f} y={y:8.2f} {note:<8}")

    @staticmethod
    def _fmt(v):
        s = f"{round(v, 2):.2f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s

    def _shape_at(self, px, py, r=5):
        items = self.canvas.find_overlapping(px - r, py - r, px + r, py + r)
        for item in reversed(items):
            for t in self.canvas.gettags(item):
                if t.startswith("shape"):
                    return int(t[5:])
        return None

    def _refresh_joint_marks(self, text=None):
        if text is None:
            text = self._dsl_text()
        marks, outlines, warnings = parse_joint_file(text)
        self.joint_marks = marks
        self.joint_warnings = collect_preview_warnings(
            marks, outlines, warnings,
        )
        self._set_joint_status()

    def _set_joint_status(self, extra=""):
        parts = []
        if extra:
            parts.append(extra)
        for w in getattr(self, "joint_warnings", []):
            tag = "Error" if w.level == "error" else "Warning"
            parts.append(f"{tag}: {w.message}")
        n = len([m for m in getattr(self, "joint_marks", [])
                 if not m.in_rotate and m.add_line is not None])
        if not parts and n:
            parts.append(f"{n} joint mark(s). Pair names must match.")
        self.joint_status_var.set("\n".join(parts))

    def _draw_joint_marks(self):
        marks = [m for m in getattr(self, "joint_marks", [])
                 if not m.in_rotate and m.add_line is not None]
        if not marks:
            return
        groups = group_marks(marks)
        # Stable colour by first appearance order
        name_order = []
        for m in marks:
            if m.name not in name_order:
                name_order.append(m.name)
        for m in marks:
            color = pair_color(m.name, name_order.index(m.name))
            corners = world_mark_corners(m)
            # corners are BL, BR, TR, TL in world; canvas y is flipped
            pts = []
            for x, y in corners:
                pts.extend(self.to_canvas(x, y))
            tags = ("jmark", f"jmark{m.add_line}")
            self.canvas.create_polygon(
                *pts, fill="", outline=color, width=2, dash=(6, 3),
                tags=tags,
            )
            cx, cy = world_mark_center(m)
            px, py = self.to_canvas(cx, cy)
            self.canvas.create_text(
                px, py, text=m.name, fill=color,
                font=canvas_font(bold=True), tags=tags,
            )
        # Connector between the two marks of a complete pair
        for name, items in groups.items():
            if len(items) != 2:
                continue
            color = pair_color(name, name_order.index(name))
            c1 = world_mark_center(items[0])
            c2 = world_mark_center(items[1])
            x1, y1 = self.to_canvas(*c1)
            x2, y2 = self.to_canvas(*c2)
            tags = ("jmark", f"jmark{items[0].add_line}",
                    f"jmark{items[1].add_line}")
            self.canvas.create_line(
                x1, y1, x2, y2, fill=color, width=2, dash=(4, 3),
                tags=tags,
            )
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            r = 6
            self.canvas.create_oval(
                mx - r, my - r, mx + r, my + r,
                fill="white", outline=color, width=2, tags=tags,
            )
            self.canvas.create_text(
                mx, my, text="J", fill=color,
                font=canvas_font(bold=True), tags=tags,
            )

    def apply_joints(self):
        text = self._dsl_text()
        result = apply_joints(text)
        self.joint_warnings = result.warnings
        extra = []
        if result.applied:
            extra.append(
                f"Applied {result.applied} joint pair(s). "
                "Original J lines were commented."
            )
        elif not result.warnings:
            extra.append("No joint pairs to apply.")
        if result.skipped and result.applied == 0:
            extra.append(f"{result.skipped} pair(s) skipped.")
        if result.text != text:
            self._set_text_input(result.text)
            if self.card_mode:
                self._reload_cards_from_text()
        self.preview_keep_scroll()
        # preview refreshes warnings; keep the apply summary on top
        self._set_joint_status("\n".join(extra))
        errors = [w for w in result.warnings if w.level == "error"]
        if errors and not result.applied:
            messagebox.showerror(
                "Apply joints",
                "\n".join(w.message for w in errors[:6]),
            )

    def _toggle_mark_mode(self):
        self._mark_mode = bool(self.mark_mode_var.get())
        self._mark_drag = None
        if self._mark_mode:
            self.canvas.configure(cursor="crosshair")
            self.drag_status_var.set("Mark joint: drag a rectangle on a piece")
        else:
            self.canvas.configure(cursor="")
            if self.selected_add is None:
                self.drag_status_var.set("")

    def _on_mark_press(self, event, px, py):
        wx, wy = self.to_world(px, py)
        self._mark_drag = {
            "x0": wx, "y0": wy, "x1": wx, "y1": wy, "px": px, "py": py,
        }
        self.canvas.delete("jmark_rubber")

    def _on_mark_motion(self, event):
        d = self._mark_drag
        if d is None:
            return
        px, py = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        wx, wy = self.to_world(px, py)
        d["x1"], d["y1"] = wx, wy
        self.canvas.delete("jmark_rubber")
        x0, y0 = self.to_canvas(d["x0"], d["y0"])
        x1, y1 = self.to_canvas(wx, wy)
        self.canvas.create_rectangle(
            x0, y0, x1, y1, outline="#0f766e", dash=(4, 3), width=2,
            tags="jmark_rubber",
        )

    def _on_mark_release(self, event):
        d = self._mark_drag
        self._mark_drag = None
        self.canvas.delete("jmark_rubber")
        if d is None:
            return
        px, py = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        wx, wy = self.to_world(px, py)
        x0, y0, x1, y1 = d["x0"], d["y0"], wx, wy
        if abs(x1 - x0) < 0.2 or abs(y1 - y0) < 0.2:
            self.drag_status_var.set("Mark joint: drag was too small")
            return
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        add_line = self._add_at_world(cx, cy)
        if add_line is None or add_line not in self.add_blocks:
            self.drag_status_var.set("Mark joint: drag on a piece (ADD block)")
            self._set_joint_status("Mark joint: drag the rectangle on a piece.")
            return
        blk = self.add_blocks[add_line]
        cumx, cumy = blk["cum"]
        lx, ly, lw, lh = add_local_coords((x0, y0, x1, y1), cumx, cumy)
        text = self._dsl_text()
        marks, _outlines, _w = parse_joint_file(text)
        name = next_joint_name(marks)
        new_text = insert_j_line(text, add_line, lx, ly, lw, lh, name)
        if new_text == text:
            self._set_joint_status("Could not find the END of that ADD block.")
            return
        self._set_text_input(new_text)
        if self.card_mode:
            self._reload_cards_from_text()
        self.preview_keep_scroll()
        self.drag_status_var.set(
            f"Marked J {self._fmt(lx)} {self._fmt(ly)} "
            f"{self._fmt(lw)} {self._fmt(lh)} {name}"
        )

    def _add_at_world(self, wx, wy):
        best, best_depth = None, -1
        for i, (_cmd, segs) in enumerate(self.shapes):
            if not segs:
                continue
            xs, ys = [], []
            for x1, y1, x2, y2 in segs:
                xs.extend((x1, x2))
                ys.extend((y1, y2))
            if not xs:
                continue
            if min(xs) - 0.5 <= wx <= max(xs) + 0.5 and \
               min(ys) - 0.5 <= wy <= max(ys) + 0.5:
                adds = self.shape_adds[i] if i < len(self.shape_adds) else ()
                if adds and len(adds) > best_depth:
                    best, best_depth = adds[-1], len(adds)
        if best is None and self.selected_add in getattr(self, "add_blocks", {}):
            return self.selected_add
        return best

    def _on_drag_press(self, event):
        self.canvas.focus_set()
        if self.card_mode and getattr(self.card_panel, "dirty", False):
            self._dsl_text()
            self.preview_keep_scroll()
        px, py = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if getattr(self, "_mark_mode", False):
            self._on_mark_press(event, px, py)
            return
        idx = self._shape_at(px, py)
        self._drag = None
        if idx is None or not self.shape_adds[idx]:
            if self.selected_add is not None:
                self.selected_add = None
                self.drag_status_var.set("")
                self.render_keep_scroll()
            return
        adds = self.shape_adds[idx]
        walk_up = bool(event.state & 0x0001) or bool(event.state & 0x0008) \
            or bool(event.state & 0x20000)
        if self.selected_add in adds:
            if walk_up:
                k = adds.index(self.selected_add)
                line = adds[k - 1] if k > 0 else adds[-1]
            else:
                line = self.selected_add
        else:
            line = adds[-1]
        changed = line != self.selected_add
        self.selected_add = line
        blk = self.add_blocks[line]
        self._drag = {
            "line": line, "start_world": self.to_world(px, py),
            "start_px": (px, py), "last_px": (px, py),
            "dx0": blk["dx"], "dy0": blk["dy"], "moved": False,
            "tags": [f"shape{i}" for i in self._block_shape_indices(line)]
                    + [f"addlbl{l}" for l in self._block_child_lines(line)]
                    + [f"jmark{l}" for l in self._block_child_lines(line)]
                    + ["selection"],
        }
        if self.card_mode:
            self.card_panel.select_by_add_line(line)
        if changed:
            self.render_keep_scroll()
        # Tinh lai diem bat dau SAU khi ve lai (scale co the doi)
        self._drag["start_world"] = self.to_world(px, py)
        # Chuan bi kiem tra giao cat: block keo vs MOI hinh con lai
        inside = set(self._block_shape_indices(line))
        self._drag["collider"] = Collider(
            [(i, self.shapes[i][1]) for i in inside],
            [(i, segs) for i, (_c, segs) in enumerate(self.shapes)
             if i not in inside],
            no_overlap=self.no_overlap_var.get(),
            no_cross_x=self.no_cross_x_var.get(),
            no_cross_y=self.no_cross_y_var.get())
        # Neu vi tri ban dau da giao thi cho keo tu do den khi hop le
        self._drag["enforce"] = not self._drag["collider"].collides(0, 0)
        self._drag["off"] = (0.0, 0.0)
        self._set_status(line, blk["dx"], blk["dy"])

    def _on_drag_motion(self, event):
        if getattr(self, "_mark_drag", None):
            self._on_mark_motion(event)
            return
        d = self._drag
        if d is None:
            return
        px, py = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if abs(px - d["start_px"][0]) + abs(py - d["start_px"][1]) > 1:
            d["moved"] = True
        wx, wy = self.to_world(px, py)
        sx, sy = d["start_world"]
        cand = (wx - sx, wy - sy)
        col = d["collider"]
        blocked = False
        if col.active:
            if d["enforce"]:
                off, blocked = col.resolve(d["off"], cand)
            else:
                off = cand
                if not col.collides(*off):
                    d["enforce"] = True
        else:
            off = cand
        # Di chuyen item tren canvas theo offset moi (re, khong ve lai)
        ox, oy = d["off"]
        dpx = (off[0] - ox) * self.scale
        dpy = -(off[1] - oy) * self.scale
        for t in d["tags"]:
            self.canvas.move(t, dpx, dpy)
        d["off"] = off
        d["blocked"] = blocked
        d["new"] = (d["dx0"] + off[0], d["dy0"] + off[1])
        self.canvas.itemconfigure(
            "selbox", outline="red" if blocked else "#0078d7")
        self._set_status(d["line"], d["new"][0], d["new"][1],
                         "BLOCKED" if blocked else "drag")

    def _on_drag_release(self, event):
        if getattr(self, "_mark_drag", None):
            self._on_mark_release(event)
            return
        d = self._drag
        self._drag = None
        if d is None or not d["moved"] or "new" not in d:
            return
        x, y = self._safe_round(d)
        self._write_add_xy(d["line"], x, y)
        self.preview_keep_scroll()
        blk = self.add_blocks.get(d["line"])
        if blk:
            self._set_status(d["line"], blk["dx"], blk["dy"])

    def _safe_round(self, d):
        # Lam tron 0.01mm; neu lam tron gay giao cat thi thu cac to hop
        # floor/ceil, chon cai hop le gan nhat
        x, y = d["new"]
        rx, ry = round(x, 2), round(y, 2)
        if not (d["collider"].active and d["enforce"]):
            return rx, ry
        col = d["collider"]
        opts = [(rx, ry)] + [(math.floor(x * 100 + fx) / 100,
                              math.floor(y * 100 + fy) / 100)
                             for fx in (0, 1) for fy in (0, 1)]
        opts.sort(key=lambda p: math.hypot(p[0] - x, p[1] - y))
        for px_, py_ in opts:
            if not col.collides(px_ - d["dx0"], py_ - d["dy0"]):
                return px_, py_
        return x, y

    def _on_drag_cancel(self, _event=None):
        if self._mark_drag is not None:
            self._mark_drag = None
            self.canvas.delete("jmark_rubber")
            self.drag_status_var.set("Mark joint cancelled")
            return
        if self._drag is None:
            return
        self._drag = None
        self.drag_status_var.set("Drag cancelled")
        self.render_keep_scroll()

    def _write_add_xy(self, line, x, y):
        # Chi thay 2 token x y cua dung dong ADD, giu nguyen indent,
        # label va phan con lai cua dong
        import re
        txt = self.text_input.get(f"{line}.0", f"{line}.end")
        m = re.match(r"(\s*ADD\s+)(\S+)(\s+)(\S+)(.*)$", txt)
        if not m:
            return
        new = (m.group(1) + self._fmt(x) + m.group(3) + self._fmt(y)
               + m.group(5))
        # Gop delete + insert thanh 1 buoc undo
        self.text_input.configure(autoseparators=False)
        self.text_input.edit_separator()
        self.text_input.delete(f"{line}.0", f"{line}.end")
        self.text_input.insert(f"{line}.0", new)
        self.text_input.edit_separator()
        self.text_input.configure(autoseparators=True)
        if self.card_mode:
            self._reload_cards_from_text()
        self._last_dsl = self._norm_dsl(self.text_input.get("1.0", "end"))

    def _on_undo(self, _event=None):
        try:
            self.text_input.edit_undo()
        except tk.TclError:
            return "break"
        if self.card_mode:
            self._reload_cards_from_text()
        self._last_dsl = self._norm_dsl(self.text_input.get("1.0", "end"))
        self.preview_keep_scroll()
        return "break"

    def render_keep_scroll(self):
        xv, yv = self.canvas.xview()[0], self.canvas.yview()[0]
        self.render()
        self.canvas.xview_moveto(xv)
        self.canvas.yview_moveto(yv)

    def preview_keep_scroll(self):
        xv, yv = self.canvas.xview()[0], self.canvas.yview()[0]
        self.preview()
        self.canvas.xview_moveto(xv)
        self.canvas.yview_moveto(yv)

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

        elif cmd in ("JF", "JM"):
            segments.extend(self._joint_segments(cmd, nums))

        if cmd in ("C", "A"):
            tab_flags = arc_tab_flags
        else:
            tab_flags = [False] * len(segments)

        return segments, tab_flags

    def _joint_segments(self, cmd, nums):
        """
        Sinh segment cho mong am (JF) / mong duong (JM).
        nums JF: x y w h teeth first_d
        nums JM: x y w h teeth first_d dir (+1 out, -1 in)
        Tham so sai -> tra ve [] (bo qua hinh).
        """
        if cmd == "JF" and len(nums) != 6:
            return []
        if cmd == "JM" and len(nums) != 7:
            return []
        x, y, w, h, teeth, first_d = nums[:6]
        if w <= 0 or h <= 0 or teeth <= 0 or first_d < 0:
            return []

        along_x = w >= h
        length = w if along_x else h
        thick = h if along_x else w

        # Vi tri (start, end) cac rang theo truc doc dai, bo rang le
        teeth_pos = []
        t = first_d
        while t + teeth <= length + 1e-9:
            teeth_pos.append((t, t + teeth))
            t += 2 * teeth

        # Doi toa do (u doc dai, v ngang do day) -> (x, y)
        def pt(u, v):
            return (x + u, y + v) if along_x else (x + v, y + u)

        segments = []
        if cmd == "JF":
            for a, b in teeth_pos:
                # x (doc) / y (ngang) la truc doi xung cua lo
                hv = thick / 2
                corners = [pt(a, -hv), pt(b, -hv), pt(b, hv), pt(a, hv)]
                for i in range(4):
                    p1, p2 = corners[i], corners[(i + 1) % 4]
                    segments.append((p1[0], p1[1], p2[0], p2[1]))
            return segments

        # JM: out -> nen o v=0, rang o v=thick; in -> nguoc lai
        base, top = (0.0, thick) if nums[6] > 0 else (thick, 0.0)
        points = [(0.0, base)]
        for a, b in teeth_pos:
            if a > points[-1][0] + 1e-9:
                points.append((a, base))
            points.append((a, top))
            points.append((b, top))
            points.append((b, base))
        if length > points[-1][0] + 1e-9:
            points.append((length, base))
        xy = [pt(u, v) for u, v in points]
        for i in range(len(xy) - 1):
            p1, p2 = xy[i], xy[i + 1]
            if p1 != p2:
                segments.append((p1[0], p1[1], p2[0], p2[1]))
        return segments

    def _shapes_to_segments(self):
        segments = []
        for cmd, shape_segments in self.shapes:
            segments.extend(shape_segments)
        return segments

    def _shapes_to_paths(self):
        """
        Tach shapes thanh cac path:
        - C/A: giu nguyen toan bo cac segment theo thu tu sinh ra.
        - Cac shape khac: moi segment la 1 path rieng de greedy toi uu.
        """
        paths = []

        for cmd, shape_segments in self.shapes:
            if not shape_segments:
                continue

            if cmd in ("C", "A"):
                # Circle/arc la 1 path lien mach.
                paths.append(shape_segments)
            else:
                # Cac segment khac van cho greedy tu do.
                paths.extend([[seg] for seg in shape_segments])

        return paths

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

    def _optimize_segments_greedy(self, segments, start=(0.0, 0.0)):
        if not segments:
            return []

        remaining = segments.copy()
        result = []
        current = start

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

    def _optimize_paths_greedy(self, paths, start=(0.0, 0.0)):
        """
        Greedy theo PATH thay vi theo tung segment.

        C/A duoc giu lien mach:
            S1 -> S2 -> S3 -> ... -> Sn

        Co the dao chieu ca path neu dau kia gan current hon,
        nhung khong bao gio tach/interleave cac segment ben trong path.
        """
        if not paths:
            return []

        remaining = [path[:] for path in paths]
        result = []
        current = start

        while remaining:
            best_index = None
            best_distance = float("inf")
            best_reversed = False

            for i, path in enumerate(remaining):
                first = path[0]
                last = path[-1]

                d1 = self._distance_sq(
                    current, (first[0], first[1])
                )
                d2 = self._distance_sq(
                    current, (last[2], last[3])
                )

                if d1 < best_distance:
                    best_distance = d1
                    best_index = i
                    best_reversed = False

                if d2 < best_distance:
                    best_distance = d2
                    best_index = i
                    best_reversed = True

            path = remaining.pop(best_index)

            if best_reversed:
                # Dao ca path:
                # A->B, B->C, C->D
                # =>
                # D->C, C->B, B->A
                path = [
                    (x2, y2, x1, y1)
                    for x1, y1, x2, y2 in reversed(path)
                ]

            result.extend(path)
            current = (path[-1][2], path[-1][3])

        return result

    def _estimate_gcode_time(self, lines):
        # Uoc luong thoi gian chay (phut), dua tren tung dong G0/G1
        # da xuat: delta_time = khoang cach giua toa do truoc/sau,
        # chia cho van toc (G0 dung GCODE_RAPID_FEED mac dinh, G1
        # dung dung tham so F ghi trong chinh dong lenh do).
        total_minutes = 0.0
        x, y = 0.0, 0.0

        for line in lines:
            line = line.strip()
            if not (line.startswith("G0 ") or line.startswith("G1 ")):
                continue

            nx, ny, feed = None, None, None
            for token in line.split()[1:]:
                if token.startswith("X"):
                    nx = float(token[1:])
                elif token.startswith("Y"):
                    ny = float(token[1:])
                elif token.startswith("F"):
                    feed = float(token[1:])

            if nx is None or ny is None:
                continue

            if feed is None:
                feed = self.GCODE_RAPID_FEED  # G0 khong co F

            dist = math.hypot(nx - x, ny - y)
            if feed > 0:
                total_minutes += dist / feed

            x, y = nx, ny

        return total_minutes

    def _format_time_estimate(self, total_minutes):
        total_seconds = total_minutes * 60
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"Thoi gian uoc luong: {minutes} phut {seconds:.1f} giay"

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
        priority_keys = getattr(self, "_priority_keys", {})

        lines = ["G21", "G90"]

                # B1: Tach shape thanh path.
        #
        # C/A = 1 path lien mach, khong duoc greedy tung segment.
        # Cac shape khac = cac segment doc lap, van greedy nhu cu.
        paths = self._shapes_to_paths()

        circle_paths = []
        normal_segments = []

        for path in paths:
            if len(path) > 1:
                # C/A
                circle_paths.append(path)
            else:
                normal_segments.extend(path)

        # Cac segment thong thuong van dung logic dedupe + merge cu.
        normal_segments = self._remove_duplicate_segments(
            normal_segments
        )
        normal_segments = self._merge_collinear_overlaps(
            normal_segments
        )

        # FIRST:
        # - Segment thuong van uu tien tung segment.
        # - Neu C/A duoc FIRST, uu tien ca path va giu nguyen
        #   thu tu segment ben trong.
        priority_segments = []
        priority_paths = []
        normal_paths = []

        for path in circle_paths:
            is_priority = any(
                self._segment_key(seg) in priority_keys
                for seg in path
            )

            if is_priority:
                priority_paths.append(path)
            else:
                normal_paths.append(path)

        # Sap xep FIRST circle theo thu tu priority nho nhat.
        priority_paths.sort(
            key=lambda path: min(
                priority_keys[self._segment_key(seg)]
                for seg in path
                if self._segment_key(seg) in priority_keys
            )
        )

        # Segment thuong FIRST van giu behavior cu.
        for seg in normal_segments:
            key = self._segment_key(seg)
            if key in priority_keys:
                priority_segments.append(seg)

        normal_segments = [
            seg for seg in normal_segments
            if self._segment_key(seg) not in priority_keys
        ]

        priority_segments.sort(
            key=lambda seg: priority_keys[self._segment_key(seg)]
        )

        # FIRST circle + FIRST segment duoc cat truoc.
        priority_output = priority_segments[:]

        for path in priority_paths:
            priority_output.extend(path)

        start_point = (
            (priority_output[-1][2], priority_output[-1][3])
            if priority_output else (0.0, 0.0)
        )

        # Gom cac path con lai:
        # - circle/arc = 1 path
        # - segment thuong = 1 path
        normal_paths = normal_paths + [
            [seg] for seg in normal_segments
        ]

        # Greedy theo PATH.
        normal_output = self._optimize_paths_greedy(
            normal_paths,
            start_point
        )

        segments = priority_output + normal_output

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

        with open(CUT_PLAN_GCODE_PATH, "w") as f:
            f.write("\n".join(lines))

        time_text = self._format_time_estimate(
            self._estimate_gcode_time(lines)
        )
        self.gcode_time_var.set(time_text)

        messagebox.showinfo(
            "Done", f"Generated cut_plan.gcode\n{time_text}"
        )

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

        time_text = self._format_time_estimate(
            self._estimate_gcode_time(lines)
        )
        self.gcode_time_var.set(time_text)

        messagebox.showinfo(
            "Done", f"Generated bounds_plan.gcode\n{time_text}"
        )