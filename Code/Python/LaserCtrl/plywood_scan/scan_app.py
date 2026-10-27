"""
Tool 1: So hoa tam plywood con lai tu anh chup -> file mask nhi phan.

Chay:  python scan_app.py  [duong_dan_anh]

Cac buoc (wizard):
    1. Mo anh (hoac mo mask da luu de sua tiep)
    2. Nhap kich thuoc that cua tam (mm) va do phan giai (mm / pixel)
    3. Chon 4 goc tam (co goi y tu dong, keo tha, kinh lup) -> nan phoi canh
    4. Kiem tra bang luoi mm (doi chieu luoi 1cm cua tham cat), xoay huong
    5. Tao mask: phan doan tu dong + nguong + lam sach + co to tay sua loi
    6. Khoang an toan (margin) cho mep chay / kerf
    7. Luu PNG (255 = go, 0 = da cat) + JSON

Toa do: goc 4 (duoi-trai) cua tam = goc (0, 0) cua DSL, y huong len.
"""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cv2
import numpy as np

import scan_core as sc
from image_view import ImageView, Magnifier

FONT = ("Times New Roman", 11)
FONT_B = ("Times New Roman", 11, "bold")

STEPS = [
    "1. Mo anh",
    "2. Kich thuoc tam",
    "3. Chon 4 goc",
    "4. Kiem tra luoi",
    "5. Tao mask",
    "6. Khoang an toan",
    "7. Luu file",
]

CORNER_NAMES = ["1 tren-trai", "2 tren-phai", "3 duoi-phai",
                "4 duoi-trai (0,0)"]
CORNER_COLORS = ["#ff3030", "#30ff30", "#3090ff", "#ffff00"]

METHODS = [("combo", "Ket hop (it bao hoa + sang)"),
           ("sat", "Do bao hoa HSV (nguoc)"),
           ("light", "Do sang L"),
           ("lab_b", "Lab b* (vang)"),
           ("kmeans", "K-means 2 nhom"),
           ("saved", "Mask da luu (giu nguyen)")]


class ScanApp(ttk.Frame):

    def __init__(self, parent, image_path=None):
        super().__init__(parent)
        self.root = parent
        self.step = 0
        # Du lieu
        self.src = None
        self.src_path = ""
        self.corners = []              # list [x, y] trong anh goc
        self.warped = None
        self.auto = None               # mask tu dong (truoc khi to tay)
        self.loaded_mask = None        # mask nap tu file (phuong phap "saved")
        self.edits = None              # int8: +1 giu go, -1 cat
        self.undo_stack = []
        self.raw = None                # auto + edits
        self.final = None              # raw sau khi co margin
        self.score = None
        self._drag_idx = None
        self._painting = False
        self._last_paint = None
        self._pending = None
        self.last_saved = None

        self.v_w = tk.StringVar(value="300")
        self.v_h = tk.StringVar(value="450")
        self.v_res = tk.StringVar(value="0.5")
        self.v_grid = tk.BooleanVar(value=True)
        self.v_grid_step = tk.StringVar(value="10")
        self.v_mat_pitch = tk.StringVar(value="10")
        self.v_method = tk.StringVar(value=METHODS[0][1])
        self.v_thr = tk.IntVar(value=128)
        self.v_open = tk.StringVar(value="0.5")
        self.v_close = tk.StringVar(value="0")
        self.v_min_wood = tk.StringVar(value="4")
        self.v_min_hole = tk.StringVar(value="4")
        self.v_border = tk.StringVar(value="0")
        self.v_alpha = tk.DoubleVar(value=0.45)
        self.v_brush_mode = tk.StringVar(value="view")
        self.v_brush = tk.StringVar(value="3")
        self.v_margin = tk.StringVar(value="1.0")
        self.v_show_src = tk.BooleanVar(value=True)
        self.v_status = tk.StringVar(value="")

        self.build_gui()
        self.show_step(0)
        if image_path:
            self.root.after(100, lambda: self.open_image(image_path))

    # ------------------------------------------------------------------
    # GUI
    # ------------------------------------------------------------------
    def build_gui(self):
        left = tk.Frame(self, width=330)
        left.pack(side="left", fill="y", padx=5, pady=5)
        left.pack_propagate(False)

        self.step_labels = []
        steps_box = tk.Frame(left)
        steps_box.pack(fill="x")
        for s in STEPS:
            lb = tk.Label(steps_box, text=s, font=FONT, anchor="w")
            lb.pack(fill="x")
            self.step_labels.append(lb)
        ttk.Separator(left).pack(fill="x", pady=4)

        self.step_area = tk.Frame(left)
        self.step_area.pack(fill="both", expand=True)

        nav = tk.Frame(left)
        nav.pack(fill="x", pady=4)
        self.btn_back = tk.Button(nav, text="< Quay lai", font=FONT,
                                  command=self.prev_step)
        self.btn_back.pack(side="left")
        self.btn_next = tk.Button(nav, text="Tiep theo >", font=FONT_B,
                                  command=self.next_step)
        self.btn_next.pack(side="right")

        self.magnifier = Magnifier(left, size=180, zoom=5)
        self.magnifier.pack(pady=4)
        tk.Label(left, textvariable=self.v_status, font=("Arial", 9),
                 justify="left", anchor="w", wraplength=310,
                 fg="#333").pack(fill="x")

        right = tk.Frame(self)
        right.pack(side="right", fill="both", expand=True)
        self.view = ImageView(right, width=900, height=750)
        self.view.pack(fill="both", expand=True)
        self.view.on_redraw = self.draw_overlay
        tk.Label(right, font=("Arial", 9), fg="#555",
                 text="Lan chuot: zoom | chuot phai / giua keo: di chuyen | "
                      "double-click chuot phai: vua man hinh").pack(fill="x")
        self.view.bind("<ButtonPress-1>", self.on_press)
        self.view.bind("<B1-Motion>", self.on_drag)
        self.view.bind("<ButtonRelease-1>", self.on_release)
        self.view.bind("<Motion>", self.on_motion)
        self.view.bind("<Double-Button-3>", lambda e: self.view.fit())
        self.root.bind("<Control-z>", lambda e: self.undo())

        self.frames = [self._build_step_open(), self._build_step_size(),
                       self._build_step_corners(), self._build_step_check(),
                       self._build_step_mask(), self._build_step_margin(),
                       self._build_step_save()]

    def _frame(self):
        return tk.Frame(self.step_area)

    def _row(self, parent, label, var, width=8, unit=""):
        r = tk.Frame(parent)
        r.pack(fill="x", pady=1)
        tk.Label(r, text=label, font=FONT, width=16, anchor="w").pack(side="left")
        e = tk.Entry(r, textvariable=var, width=width, font=FONT)
        e.pack(side="left")
        if unit:
            tk.Label(r, text=unit, font=FONT).pack(side="left")
        return e

    def _note(self, parent, text):
        tk.Label(parent, text=text, font=("Arial", 9), justify="left",
                 wraplength=310, anchor="w", fg="#444").pack(fill="x", pady=3)

    def _build_step_open(self):
        f = self._frame()
        tk.Button(f, text="Chon anh tam go...", font=FONT,
                  command=self.ask_open_image).pack(fill="x", pady=2)
        tk.Button(f, text="Mo mask da luu (sua tiep)...", font=FONT,
                  command=self.ask_load_mask).pack(fill="x", pady=2)
        self.lb_src = tk.Label(f, text="Chua co anh", font=FONT,
                               wraplength=310, justify="left")
        self.lb_src.pack(fill="x", pady=4)
        self._note(f, "Meo chup anh: chup thang tu tren xuong, du sang, "
                      "khong bong do, tam go phang. Nen dat tam len nen "
                      "khac mau (vd tham cat xanh) de tach go de hon.")
        return f

    def _build_step_size(self):
        f = self._frame()
        self._row(f, "Chieu rong W", self.v_w, unit="mm")
        self._row(f, "Chieu cao H", self.v_h, unit="mm")
        r = tk.Frame(f)
        r.pack(fill="x", pady=1)
        tk.Label(r, text="Do phan giai", font=FONT, width=16,
                 anchor="w").pack(side="left")
        ttk.Combobox(r, textvariable=self.v_res, width=6,
                     values=["0.2", "0.25", "0.5", "1.0"]).pack(side="left")
        tk.Label(r, text="mm/pixel", font=FONT).pack(side="left")
        self._note(f, "W = canh tu goc 1 sang goc 2 (canh tren), H = canh tu "
                      "goc 1 xuong goc 4 (canh trai). Do bang thuoc cho "
                      "chinh xac. 0.5 mm/px la du cho thanh rong 10mm; "
                      "chon nho hon neu can chinh xac hon (cham hon).")
        return f

    def _build_step_corners(self):
        f = self._frame()
        tk.Button(f, text="Tu dong tim 4 goc", font=FONT,
                  command=self.auto_corners).pack(fill="x", pady=2)
        tk.Button(f, text="Xoa cac goc, click lai", font=FONT,
                  command=self.clear_corners).pack(fill="x", pady=2)
        tk.Button(f, text="Doi thu tu goc (xoay 90 do)", font=FONT,
                  command=lambda: self.rotate_order(1)).pack(fill="x", pady=2)
        self.lb_corners = tk.Label(f, text="", font=("Courier", 9),
                                   justify="left", anchor="w")
        self.lb_corners.pack(fill="x", pady=4)
        self._note(f, "Click lan luot 4 goc: 1 tren-trai, 2 tren-phai, "
                      "3 duoi-phai, 4 duoi-trai. Goc 4 la goc (0,0) cua DSL. "
                      "Keo cac cham mau de chinh; dung kinh lup ben duoi "
                      "va zoom de dat dung dinh goc tam (mat tren tam). "
                      "Neu tam co canh cong, dat goc dung o dinh goc that.")
        return f

    def _build_step_check(self):
        f = self._frame()
        tk.Checkbutton(f, text="Hien luoi mm", variable=self.v_grid,
                       font=FONT, command=self.refresh_view).pack(anchor="w")
        self._row(f, "Buoc luoi", self.v_grid_step, unit="mm")
        tk.Button(f, text="Ve lai luoi", font=FONT,
                  command=self.refresh_view).pack(fill="x", pady=2)
        r = tk.Frame(f)
        r.pack(fill="x", pady=2)
        tk.Button(r, text="Xoay trai 90", font=FONT,
                  command=lambda: self.rotate_result(1)).pack(side="left",
                                                              expand=True,
                                                              fill="x")
        tk.Button(r, text="Xoay phai 90", font=FONT,
                  command=lambda: self.rotate_result(3)).pack(side="left",
                                                              expand=True,
                                                              fill="x")
        ttk.Separator(f).pack(fill="x", pady=4)
        tk.Label(f, text="Kiem tra kich thuoc bang luoi tham:",
                 font=FONT_B, anchor="w").pack(fill="x")
        self._row(f, "O luoi tham", self.v_mat_pitch, unit="mm")
        tk.Button(f, text="Do luoi tham qua cac lo", font=FONT,
                  command=self.measure_grid).pack(fill="x", pady=2)
        self.lb_grid = tk.Label(f, text="", font=FONT, justify="left",
                                wraplength=310, anchor="w")
        self.lb_grid.pack(fill="x")
        self.btn_apply_size = tk.Button(f, text="Dung kich thuoc goi y",
                                        font=FONT, state="disabled",
                                        command=self.apply_suggested_size)
        self.btn_apply_size.pack(fill="x", pady=2)
        self._note(f, "Luoi tim = luoi mm theo kich thuoc da nhap, goc (0,0) "
                      "o duoi-trai. Neu luoi tim lech dan so voi luoi 1cm cua "
                      "tham nhin qua lo => kich thuoc nhap sai hoac goc dat "
                      "lech. Tham nam thap hon mat go 1 do day van nen sai "
                      "so vai %.")
        self._suggest = None
        return f

    def _build_step_mask(self):
        f = self._frame()
        r = tk.Frame(f)
        r.pack(fill="x")
        tk.Label(r, text="Phuong phap", font=FONT).pack(side="left")
        cb = ttk.Combobox(r, textvariable=self.v_method, state="readonly",
                          width=26, values=[m[1] for m in METHODS])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.recompute_auto(True))
        r = tk.Frame(f)
        r.pack(fill="x")
        tk.Label(r, text="Nguong", font=FONT).pack(side="left")
        tk.Scale(r, from_=0, to=255, orient="horizontal", variable=self.v_thr,
                 length=200, command=lambda v: self.schedule(
                     lambda: self.recompute_auto(False))).pack(side="left")
        tk.Button(r, text="Otsu", font=FONT,
                  command=lambda: self.recompute_auto(True)).pack(side="left")
        self._row(f, "Mo (bo nhieu)", self.v_open, unit="mm")
        self._row(f, "Dong (lap ke)", self.v_close, unit="mm")
        self._row(f, "Bo dom go <", self.v_min_wood, unit="mm2")
        self._row(f, "Bo lo nho <", self.v_min_hole, unit="mm2")
        self._row(f, "Cat vien mep", self.v_border, unit="mm")
        tk.Button(f, text="Ap dung", font=FONT,
                  command=lambda: self.recompute_auto(False)).pack(fill="x")
        r = tk.Frame(f)
        r.pack(fill="x")
        tk.Label(r, text="Do dam lop phu", font=FONT).pack(side="left")
        tk.Scale(r, from_=0, to=1, resolution=0.05, orient="horizontal",
                 variable=self.v_alpha, length=150,
                 command=lambda v: self.schedule(self.refresh_view)
                 ).pack(side="left")
        ttk.Separator(f).pack(fill="x", pady=3)
        tk.Label(f, text="Co to tay (sua loi):", font=FONT_B,
                 anchor="w").pack(fill="x")
        r = tk.Frame(f)
        r.pack(fill="x")
        for val, txt in (("view", "Xem"), ("keep", "To GO (giu)"),
                         ("cut", "To CAT")):
            tk.Radiobutton(r, text=txt, value=val, font=FONT,
                           variable=self.v_brush_mode).pack(side="left")
        self._row(f, "Co co", self.v_brush, unit="mm")
        r = tk.Frame(f)
        r.pack(fill="x", pady=2)
        tk.Button(r, text="Hoan tac (Ctrl+Z)", font=FONT,
                  command=self.undo).pack(side="left", expand=True, fill="x")
        tk.Button(r, text="Xoa net to", font=FONT,
                  command=self.clear_edits).pack(side="left", expand=True,
                                                 fill="x")
        tk.Checkbutton(f, text="Hien anh goc (bo chon = chi hien mask)",
                       variable=self.v_show_src, font=FONT,
                       command=self.refresh_view).pack(anchor="w")
        self._note(f, "Do = da cat. Kiem tra ky cac duong cat manh (vet cat "
                      "chua tach roi) va bong trong lo, dung co 'To CAT' de "
                      "ve them.")
        return f

    def _build_step_margin(self):
        f = self._frame()
        self._row(f, "Khoang an toan", self.v_margin, unit="mm")
        tk.Button(f, text="Xem truoc", font=FONT,
                  command=self.recompute_final).pack(fill="x", pady=2)
        self.lb_stats = tk.Label(f, text="", font=FONT, justify="left",
                                 anchor="w", wraplength=310)
        self.lb_stats.pack(fill="x", pady=4)
        self._note(f, "Vung go sat mep lo / mep tam bi co vao mot khoang nay "
                      "(mau cam) vi mep chay, gion, va sai so dat lai tam "
                      "tren may. Goi y 1-2 mm.")
        return f

    def _build_step_save(self):
        f = self._frame()
        tk.Button(f, text="Luu mask (PNG + JSON)...", font=FONT_B,
                  command=self.save).pack(fill="x", pady=2)
        tk.Button(f, text="Mo trong Strip Packer", font=FONT,
                  command=self.open_packer).pack(fill="x", pady=2)
        self.lb_saved = tk.Label(f, text="", font=FONT, justify="left",
                                 wraplength=310, anchor="w")
        self.lb_saved.pack(fill="x", pady=4)
        self._note(f, "Se ghi: <ten>.png (mask cuoi, 255 = go, 0 = cat), "
                      "<ten>.json (kich thuoc, mm/px, margin), <ten>_raw.png "
                      "(mask truoc margin) va <ten>_warped.png (anh da nan) "
                      "de mo lai sua tiep.")
        return f

    # ------------------------------------------------------------------
    # Dieu huong buoc
    # ------------------------------------------------------------------
    def show_step(self, i):
        self.step = i
        for k, lb in enumerate(self.step_labels):
            lb.config(fg="#0050c0" if k == i else ("#000" if k < i else "#888"),
                      font=FONT_B if k == i else FONT)
        for fr in self.frames:
            fr.pack_forget()
        self.frames[i].pack(fill="both", expand=True)
        self.btn_back.config(state="normal" if i > 0 else "disabled")
        self.btn_next.config(state="normal" if i < len(STEPS) - 1
                             else "disabled")
        self.refresh_view(fit=True)

    def next_step(self):
        try:
            ok = self._leave_step(self.step)
        except Exception as ex:  # thong bao loi nhap lieu
            messagebox.showerror("Loi", str(ex))
            return
        if ok:
            self.show_step(min(self.step + 1, len(STEPS) - 1))

    def prev_step(self):
        if self.step == 4 and self.loaded_mask is not None and self.src is None:
            # Mask nap tu file: khong co anh goc de quay lai chon goc
            self.show_step(0)
            return
        self.show_step(max(0, self.step - 1))

    def _leave_step(self, i):
        if i == 0:
            if self.src is None and self.warped is None:
                messagebox.showwarning("Thieu anh", "Hay chon anh truoc.")
                return False
            if self.src is None:      # mask da luu: nhay thang toi buoc mask
                self.show_step(3)
                return True
        if i == 1:
            self.get_size()
            if self.corners == [] and self.src is not None:
                self.auto_corners(silent=True)
        if i == 2:
            if len(self.corners) != 4:
                messagebox.showwarning("Thieu goc", "Can dung 4 goc.")
                return False
            self.do_warp()
        if i == 3:
            if self.auto is None or self.auto.shape != self.warped.shape[:2]:
                self.recompute_auto(True)
        if i == 4:
            self.recompute_final()
        return True

    # ------------------------------------------------------------------
    # Tham so
    # ------------------------------------------------------------------
    def get_size(self):
        try:
            w = float(self.v_w.get())
            h = float(self.v_h.get())
            res = float(self.v_res.get())
        except ValueError:
            raise ValueError("Kich thuoc / do phan giai phai la so")
        if w <= 0 or h <= 0 or res <= 0:
            raise ValueError("Kich thuoc phai > 0")
        if (w / res) * (h / res) > 40e6:
            raise ValueError("Anh qua lon, hay tang mm/pixel")
        return w, h, res

    def _f(self, var, default=0.0):
        try:
            return float(var.get())
        except ValueError:
            return default

    def method_key(self):
        name = self.v_method.get()
        for k, t in METHODS:
            if t == name:
                return k
        return "combo"

    # ------------------------------------------------------------------
    # Buoc 1: mo anh / mo mask
    # ------------------------------------------------------------------
    def ask_open_image(self):
        p = filedialog.askopenfilename(
            title="Chon anh tam go",
            filetypes=[("Anh", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"),
                       ("Tat ca", "*.*")])
        if p:
            self.open_image(p)

    def open_image(self, path):
        try:
            img = sc.imread_unicode(path)
        except Exception as ex:
            messagebox.showerror("Loi", str(ex))
            return
        self.src = img
        self.src_path = path
        self.corners = []
        self.warped = self.auto = self.raw = self.final = None
        self.loaded_mask = None
        self.edits = None
        self.undo_stack = []
        if self.method_key() == "saved":
            self.v_method.set(METHODS[0][1])
        self.lb_src.config(text="%s\n%d x %d px" % (
            os.path.basename(path), img.shape[1], img.shape[0]))
        self.refresh_view(fit=True)

    def ask_load_mask(self):
        p = filedialog.askopenfilename(
            title="Mo mask da luu",
            filetypes=[("Mask JSON / PNG", "*.json *.png"), ("Tat ca", "*.*")])
        if p:
            self.load_mask(p)

    def load_mask(self, path):
        try:
            mask, meta, folder = sc.load_mask_file(path)
        except Exception as ex:
            messagebox.showerror("Loi", str(ex))
            return
        raw = mask
        if meta.get("raw_mask_file") and os.path.exists(
                os.path.join(folder, meta["raw_mask_file"])):
            raw = sc.imread_unicode(os.path.join(folder, meta["raw_mask_file"]),
                                    cv2.IMREAD_GRAYSCALE)
            raw = ((raw > 127) * 255).astype(np.uint8)
        warped = None
        if meta.get("warped_file") and os.path.exists(
                os.path.join(folder, meta["warped_file"])):
            warped = sc.imread_unicode(os.path.join(folder,
                                                    meta["warped_file"]))
        if warped is None or warped.shape[:2] != raw.shape:
            warped = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
        self.v_w.set("%g" % meta["width_mm"])
        self.v_h.set("%g" % meta["height_mm"])
        self.v_res.set("%g" % meta["mm_per_px"])
        self.v_margin.set("%g" % meta.get("margin_mm", 1.0))
        self.src = None
        self.src_path = meta.get("source", "")
        self.corners = []
        self.warped = warped
        self.loaded_mask = raw
        self.auto = raw.copy()
        self.edits = np.zeros(raw.shape, np.int8)
        self.undo_stack = []
        self.v_method.set(METHODS[-1][1])
        self.lb_src.config(text="Mask: %s\n%g x %g mm, %g mm/px" % (
            os.path.basename(path), meta["width_mm"], meta["height_mm"],
            meta["mm_per_px"]))
        self.update_raw()
        self.show_step(4)

    # ------------------------------------------------------------------
    # Buoc 3: goc
    # ------------------------------------------------------------------
    def auto_corners(self, silent=False):
        if self.src is None:
            return
        c = sc.detect_sheet_corners(self.src)
        if c is None:
            if not silent:
                messagebox.showinfo("Khong tim thay",
                                    "Khong tu tim duoc goc, hay click tay.")
            return
        self.corners = [list(map(float, p)) for p in c]
        self.refresh_view()

    def clear_corners(self):
        self.corners = []
        self.refresh_view()

    def rotate_order(self, times):
        if len(self.corners) == 4:
            self.corners = [list(p) for p in
                            sc.rotate_corners(self.corners, times)]
            self.refresh_view()

    def do_warp(self):
        w, h, res = self.get_size()
        self.warped = sc.warp_sheet(self.src, self.corners, w, h, res)
        self.auto = self.raw = self.final = None
        self.edits = np.zeros(self.warped.shape[:2], np.int8)
        self.undo_stack = []

    def rotate_result(self, times):
        # Xoay tam: doi thu tu goc va hoan doi W/H, nan lai
        if self.src is None or len(self.corners) != 4:
            return
        self.corners = [list(p) for p in sc.rotate_corners(self.corners, times)]
        w, h = self.v_w.get(), self.v_h.get()
        self.v_w.set(h)
        self.v_h.set(w)
        self.do_warp()
        self.refresh_view(fit=True)

    # ------------------------------------------------------------------
    # Buoc 4: kiem tra luoi
    # ------------------------------------------------------------------
    def measure_grid(self):
        if self.warped is None:
            return
        w, h, res = self.get_size()
        m, _ = sc.auto_mask(self.warped, res)
        px, py = sc.estimate_grid_period_mm(self.warped, m, res)
        pitch = self._f(self.v_mat_pitch, 10.0)
        if not px or not py:
            self.lb_grid.config(text="Khong do duoc (it lo / luoi mo).")
            return
        sw, sh = w * pitch / px, h * pitch / py
        self._suggest = (sw, sh)
        self.lb_grid.config(text=(
            "Chu ky luoi do duoc: x = %.2f mm, y = %.2f mm\n"
            "(theo kich thuoc dang nhap %g x %g)\n"
            "=> neu o luoi tham = %g mm thi tam ~ %.0f x %.0f mm"
            % (px, py, w, h, pitch, sw, sh)))
        self.btn_apply_size.config(state="normal")

    def apply_suggested_size(self):
        if not self._suggest:
            return
        self.v_w.set("%.0f" % self._suggest[0])
        self.v_h.set("%.0f" % self._suggest[1])
        self.do_warp()
        self.measure_grid()
        self.refresh_view(fit=True)

    # ------------------------------------------------------------------
    # Buoc 5: mask
    # ------------------------------------------------------------------
    def schedule(self, fn, delay=150):
        if self._pending:
            self.root.after_cancel(self._pending)
        self._pending = self.root.after(delay, fn)

    def recompute_auto(self, use_otsu):
        self._pending = None
        if self.warped is None:
            return
        _, _, res = self.get_size()
        key = self.method_key()
        if key == "saved":
            if self.loaded_mask is None:
                messagebox.showinfo("Chu y", "Chua nap mask nao tu file.")
                self.v_method.set(METHODS[0][1])
                key = "combo"
            else:
                base = self.loaded_mask.copy()
        if key == "kmeans":
            base = sc.kmeans_mask(self.warped)
        elif key != "saved":
            self.score = sc.wood_score(self.warped, key,
                                       blur_px=max(1, sc.mm_to_px(1.0, res)))
            if use_otsu:
                self.v_thr.set(sc.otsu_threshold(self.score))
            base = ((self.score > self.v_thr.get()) * 255).astype(np.uint8)
        if key != "saved":
            base = sc.cleanup_mask(base, res, self._f(self.v_open),
                                   self._f(self.v_close),
                                   self._f(self.v_min_wood),
                                   self._f(self.v_min_hole))
        self.auto = sc.cut_border(base, self._f(self.v_border), res)
        if self.edits is None or self.edits.shape != self.auto.shape:
            self.edits = np.zeros(self.auto.shape, np.int8)
        self.update_raw()
        self.refresh_view()

    def update_raw(self):
        if self.auto is None:
            return
        self.raw = sc.apply_edits(self.auto, self.edits)
        self.final = None

    def undo(self):
        if self.undo_stack:
            self.edits = self.undo_stack.pop()
            self.update_raw()
            self.refresh_view()

    def clear_edits(self):
        if self.edits is not None:
            self.undo_stack.append(self.edits.copy())
            self.edits[:] = 0
            self.update_raw()
            self.refresh_view()

    def paint(self, x, y):
        if self.edits is None:
            return
        _, _, res = self.get_size()
        r = max(1, int(round(self._f(self.v_brush, 3) / 2 / res)))
        val = 1 if self.v_brush_mode.get() == "keep" else -1
        e = self.edits.astype(np.int16)
        cv2.circle(e, (int(round(x)), int(round(y))), r, val, -1)
        if self._last_paint is not None:
            cv2.line(e, self._last_paint, (int(round(x)), int(round(y))),
                     val, 2 * r)
        self.edits = e.astype(np.int8)
        self._last_paint = (int(round(x)), int(round(y)))
        self.update_raw()
        self.schedule(self.refresh_view, 30)

    # ------------------------------------------------------------------
    # Buoc 6: margin
    # ------------------------------------------------------------------
    def recompute_final(self):
        if self.raw is None:
            self.recompute_auto(True)
        _, _, res = self.get_size()
        margin = self._f(self.v_margin, 0)
        self.final = sc.erode_margin(self.raw, margin, res)
        area = (self.final > 0).sum() * res * res
        total = self.final.size * res * res
        self.lb_stats.config(text="Go dung duoc: %.0f cm2 / %.0f cm2 (%.1f%%)"
                             % (area / 100, total / 100, 100 * area / total))
        self.refresh_view()

    # ------------------------------------------------------------------
    # Buoc 7: luu
    # ------------------------------------------------------------------
    def save(self):
        if self.raw is None:
            messagebox.showwarning("Chua co mask", "Hay tao mask truoc.")
            return
        if self.final is None:
            self.recompute_final()
        init = "plywood_mask.png"
        if self.src_path:
            init = os.path.splitext(os.path.basename(self.src_path))[0] + \
                "_mask.png"
        p = filedialog.asksaveasfilename(title="Luu mask",
                                         defaultextension=".png",
                                         initialfile=init,
                                         filetypes=[("PNG", "*.png")])
        if not p:
            return
        w, h, res = self.get_size()
        png, js = sc.save_mask_file(
            p, self.final, w, h, res, self._f(self.v_margin, 0),
            source=self.src_path, raw_mask=self.raw, warped=self.warped,
            corners=self.corners if len(self.corners) == 4 else None,
            extra={"method": self.method_key(),
                   "threshold": int(self.v_thr.get())})
        self.last_saved = js
        self.lb_saved.config(text="Da luu:\n%s\n%s" % (png, js))

    def open_packer(self):
        if not self.last_saved:
            messagebox.showinfo("Chua luu", "Hay luu mask truoc.")
            return
        here = os.path.dirname(os.path.abspath(__file__))
        subprocess.Popen([sys.executable, os.path.join(here, "strip_packer.py"),
                          self.last_saved])

    # ------------------------------------------------------------------
    # Hien thi
    # ------------------------------------------------------------------
    def current_image(self):
        s = self.step
        if s <= 2:
            return self.src if self.src is not None else self.warped
        if self.warped is None:
            return self.src
        try:
            _, _, res = self.get_size()
        except ValueError:
            res = 0.5
        if s == 3:
            img = self.warped
            if self.v_grid.get():
                img = sc.draw_mm_grid(img, res, self._f(self.v_grid_step, 10))
            return img
        base = self.warped if self.v_show_src.get() or s != 4 else \
            np.full_like(self.warped, 230)
        if s == 4 and self.raw is not None:
            return sc.overlay_mask(base, self.raw, self.v_alpha.get())
        if s >= 5 and self.raw is not None:
            fin = self.final if self.final is not None else self.raw
            lost = ((self.raw > 0) & (fin == 0)).astype(np.uint8)
            img = sc.overlay_mask(base, self.raw, self.v_alpha.get(),
                                  extra=lost)
            return img
        return self.warped

    def refresh_view(self, fit=False):
        self.view.set_image(self.current_image(), fit=fit)
        self.update_status()

    def draw_overlay(self):
        if self.step == 2 and self.src is not None and self.corners:
            pts = [self.view.img_to_canvas(*p) for p in self.corners]
            if len(pts) >= 2:
                flat = [v for p in pts for v in p]
                if len(pts) == 4:
                    flat += list(pts[0])
                self.view.create_line(*flat, fill="#ff00ff", width=2)
            for i, (cx, cy) in enumerate(pts):
                self.view.create_oval(cx - 7, cy - 7, cx + 7, cy + 7,
                                      outline=CORNER_COLORS[i], width=3)
                self.view.create_text(cx + 12, cy - 12, text=str(i + 1),
                                      fill=CORNER_COLORS[i],
                                      font=("Arial", 14, "bold"))
        if self.step == 3 and self.warped is not None:
            # Danh dau goc (0,0) DSL
            cx, cy = self.view.img_to_canvas(0, self.warped.shape[0])
            self.view.create_text(cx + 4, cy - 4, text="(0,0)", anchor="sw",
                                  fill="yellow", font=("Arial", 12, "bold"))

    def update_status(self):
        if self.step == 2:
            lines = []
            for i in range(4):
                if i < len(self.corners):
                    lines.append("%-18s %7.1f %7.1f" % (
                        CORNER_NAMES[i], *self.corners[i]))
                else:
                    lines.append("%-18s   (chua)" % CORNER_NAMES[i])
            self.lb_corners.config(text="\n".join(lines))

    # ------------------------------------------------------------------
    # Su kien chuot
    # ------------------------------------------------------------------
    def on_press(self, e):
        x, y = self.view.canvas_to_img(e.x, e.y)
        if self.step == 2 and self.src is not None:
            # Chon goc gan nhat neu click gan, nguoc lai them goc moi
            best, bd = None, 1e9
            for i, p in enumerate(self.corners):
                cx, cy = self.view.img_to_canvas(*p)
                d = (cx - e.x) ** 2 + (cy - e.y) ** 2
                if d < bd:
                    best, bd = i, d
            if best is not None and bd < 15 ** 2:
                self._drag_idx = best
            elif len(self.corners) < 4:
                self.corners.append([x, y])
                self._drag_idx = len(self.corners) - 1
                self.refresh_view()
        elif self.step == 4 and self.v_brush_mode.get() != "view":
            self.undo_stack.append(self.edits.copy())
            if len(self.undo_stack) > 30:
                self.undo_stack.pop(0)
            self._last_paint = None
            self._painting = True
            self.paint(x, y)

    def on_drag(self, e):
        x, y = self.view.canvas_to_img(e.x, e.y)
        if self.step == 2 and self._drag_idx is not None:
            ih, iw = self.src.shape[:2]
            self.corners[self._drag_idx] = [min(max(x, 0), iw - 1),
                                            min(max(y, 0), ih - 1)]
            self.view.redraw()
            self.update_status()
        elif self.step == 4 and self._painting:
            self.paint(x, y)
        self.on_motion(e)

    def on_release(self, e):
        self._drag_idx = None
        if self._painting:
            self._painting = False
            self.refresh_view()

    def on_motion(self, e):
        x, y = self.view.canvas_to_img(e.x, e.y)
        img = self.view.img
        if img is None:
            return
        rad = None
        if self.step == 4 and self.v_brush_mode.get() != "view":
            try:
                rad = self._f(self.v_brush, 3) / 2 / float(self.v_res.get())
            except ValueError:
                rad = None
        self.magnifier.show(img, x, y, rad)
        txt = "x=%.0f y=%.0f px" % (x, y)
        if self.step >= 3 and self.warped is not None:
            try:
                res = float(self.v_res.get())
                txt += "  |  DSL: x=%.1f y=%.1f mm" % (
                    x * res, (self.warped.shape[0] - y) * res)
            except ValueError:
                pass
        self.v_status.set(txt)


def main():
    root = tk.Tk()
    root.title("Plywood Scan - so hoa tam go con lai")
    root.geometry("1280x860")
    app = ScanApp(root, sys.argv[1] if len(sys.argv) > 1 else None)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
