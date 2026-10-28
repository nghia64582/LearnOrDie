"""
Tool 1: So hoa tam plywood con lai tu anh chup -> file mask nhi phan.

Chay:  python scan_app.py  [duong_dan_anh]

Cac buoc (wizard):
    1. Open image (hoac mo mask da luu de sua tiep)
    2. Sheet size: kich thuoc that cua tam (mm)
    3. Pick 4 corners (goi y tu dong, keo tha, kinh lup) -> do phan giai
       mm/px tinh tu dong tu do dai cac canh tu giac (pixel) va W x H (mm),
       roi nan phoi canh
    4. Check grid: luoi mm de doi chieu luoi 1cm cua tham cat, xoay huong
    5. Mask: phan doan tu dong + nguong + lam sach + co to tay sua loi
    6. Safety margin cho mep chay / kerf
    7. Save PNG (255 = go, 0 = da cat) + JSON

Toa do: goc 4 (duoi-trai) cua tam = goc (0, 0) cua DSL, y huong len.
"""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cv2
import numpy as np

import align_core as ac
import scan_core as sc
import ui_util
from ui_util import px
from image_view import ImageView, Magnifier

# Font: 1 ho font chung (ui_util), gan lai trong ScanApp.__init__
FONT, FONT_B, FONT_S, FONT_MONO, FONT_L = ui_util.fonts(11)

STEPS = [
    "1. Open image",
    "2. Sheet size",
    "3. Pick 4 corners",
    "4. Check grid",
    "5. Mask",
    "6. Safety margin",
    "7. Alignment marks",
    "8. Save",
]

STEP_ALIGN = 6
STEP_SAVE = 7

CORNER_NAMES = ["1 top-left", "2 top-right", "3 bottom-right",
                "4 bottom-left (0,0)"]
CORNER_COLORS = ["#ff3030", "#30ff30", "#3090ff", "#ffff00"]

METHODS = [("combo", "Combined (saturation + light)"),
           ("sat", "HSV saturation (inverted)"),
           ("light", "Lightness L"),
           ("lab_b", "Lab b* (yellowness)"),
           ("kmeans", "K-means, 2 clusters"),
           ("saved", "Saved mask (keep as is)")]


class ScanApp(ttk.Frame):

    def __init__(self, parent, image_path=None):
        global FONT, FONT_B, FONT_S, FONT_MONO, FONT_L
        FONT, FONT_B, FONT_S, FONT_MONO, FONT_L = ui_util.init_fonts(
            parent.winfo_toplevel(), 11)
        super().__init__(parent)
        self.root = parent
        self.step = 0
        # Du lieu
        self.src = None
        self.src_path = ""
        self.corners = []              # list [x, y] trong anh goc
        self.warped = None
        self.res = None                # mm/px cua anh da nan (dang dung)
        self.res_mode = "auto"
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
        self._suggest = None
        self.last_saved = None
        self.align_pts = [None, None]    # 2 diem can chinh (mm, toa do tam)
        self._drag_pt = None

        self.v_w = tk.StringVar(value="306")
        self.v_h = tk.StringVar(value="460")
        self.v_res_override = tk.BooleanVar(value=False)
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
        self.v_res_info = tk.StringVar(value="Resolution: pick 4 corners first")
        # Can chinh
        self.v_pt_target = tk.IntVar(value=0)
        self.v_p = [[tk.StringVar(), tk.StringVar()],
                    [tk.StringVar(), tk.StringVar()]]
        self.v_cross = tk.StringVar(value="%g" % ac.ALIGN_DEFAULTS["cross_mm"])
        self.v_power = tk.StringVar(value="%d" % ac.ALIGN_DEFAULTS["power"])
        self.v_feed = tk.StringVar(value="%g" % ac.ALIGN_DEFAULTS["feed"])
        self.v_off_x = tk.StringVar(value="0")
        self.v_off_y = tk.StringVar(value="0")
        self.v_return = tk.BooleanVar(value=True)
        self.v_dist = tk.StringVar(value="")
        # Luu
        self.v_name = tk.StringVar(value="scan")
        self.v_out_root = tk.StringVar(value=sc.default_output_root())

        self.build_gui()
        self.show_step(0)
        if image_path:
            self.root.after(100, lambda: self.open_image(image_path))

    # ------------------------------------------------------------------
    # GUI
    # ------------------------------------------------------------------
    def build_gui(self):
        self.wrap = px(310)
        left = tk.Frame(self, width=px(340))
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
        self.btn_back = tk.Button(nav, text="< Back", font=FONT,
                                  command=self.prev_step)
        self.btn_back.pack(side="left")
        self.btn_next = tk.Button(nav, text="Next >", font=FONT_B,
                                  command=self.next_step)
        self.btn_next.pack(side="right")

        self.magnifier = Magnifier(left, size=px(180), zoom=5)
        self.magnifier.pack(pady=4)
        tk.Label(left, textvariable=self.v_status, font=FONT_S,
                 justify="left", anchor="w", wraplength=self.wrap,
                 fg="#333").pack(fill="x")

        right = tk.Frame(self)
        right.pack(side="right", fill="both", expand=True)
        self.view = ImageView(right, width=px(900), height=px(750))
        self.view.pack(fill="both", expand=True)
        self.view.on_redraw = self.draw_overlay
        tk.Label(right, font=FONT_S, fg="#555",
                 text="Mouse wheel: zoom | right / middle drag: pan | "
                      "double right-click: fit to window").pack(fill="x")
        self.view.bind("<ButtonPress-1>", self.on_press)
        self.view.bind("<B1-Motion>", self.on_drag)
        self.view.bind("<ButtonRelease-1>", self.on_release)
        self.view.bind("<Motion>", self.on_motion)
        self.view.bind("<Double-Button-3>", lambda e: self.view.fit())
        self.root.bind("<Control-z>", lambda e: self.undo())

        self.frames = [self._build_step_open(), self._build_step_size(),
                       self._build_step_corners(), self._build_step_check(),
                       self._build_step_mask(), self._build_step_margin(),
                       self._build_step_align(), self._build_step_save()]

    def _frame(self):
        return tk.Frame(self.step_area)

    def _row(self, parent, label, var, width=8, unit=""):
        r = tk.Frame(parent)
        r.pack(fill="x", pady=1)
        tk.Label(r, text=label, font=FONT, width=18, anchor="w").pack(side="left")
        e = tk.Entry(r, textvariable=var, width=width, font=FONT)
        e.pack(side="left")
        if unit:
            tk.Label(r, text=unit, font=FONT).pack(side="left")
        return e

    def _note(self, parent, text):
        tk.Label(parent, text=text, font=FONT_S, justify="left",
                 wraplength=self.wrap, anchor="w", fg="#444").pack(fill="x",
                                                                   pady=3)

    def _res_label(self, parent):
        tk.Label(parent, textvariable=self.v_res_info, font=FONT,
                 justify="left", anchor="w", wraplength=self.wrap,
                 fg="#004080").pack(fill="x", pady=3)

    def _build_step_open(self):
        f = self._frame()
        tk.Button(f, text="Open sheet photo...", font=FONT,
                  command=self.ask_open_image).pack(fill="x", pady=2)
        tk.Button(f, text="Open saved mask (continue editing)...", font=FONT,
                  command=self.ask_load_mask).pack(fill="x", pady=2)
        self.lb_src = tk.Label(f, text="No image loaded", font=FONT,
                               wraplength=self.wrap, justify="left")
        self.lb_src.pack(fill="x", pady=4)
        self._note(f, "Photo tips: shoot straight from above, good even "
                      "light, no hard shadows, sheet lying flat. A background "
                      "with a different colour (e.g. a green cutting mat) "
                      "makes wood detection much easier.")
        return f

    def _build_step_size(self):
        f = self._frame()
        self._row(f, "Width W", self.v_w, unit="mm")
        self._row(f, "Height H", self.v_h, unit="mm")
        self._note(f, "W = top edge (corner 1 -> corner 2), H = left edge "
                      "(corner 1 -> corner 4). Measure the sheet with a ruler; "
                      "it differs per sheet.")
        ttk.Separator(f).pack(fill="x", pady=4)
        tk.Label(f, text="Resolution (mm/px):", font=FONT_B,
                 anchor="w").pack(fill="x")
        self._note(f, "Computed automatically from the picked corners: the "
                      "pixel length of the sheet edges divided into W x H, so "
                      "the warped image keeps about the native photo "
                      "resolution.")
        tk.Checkbutton(f, text="Advanced: override mm/px manually",
                       variable=self.v_res_override, font=FONT,
                       command=self.update_res_info).pack(anchor="w")
        r = tk.Frame(f)
        r.pack(fill="x", pady=1)
        tk.Label(r, text="Manual mm/px", font=FONT, width=16,
                 anchor="w").pack(side="left")
        ttk.Combobox(r, textvariable=self.v_res, width=6,
                     values=["0.2", "0.25", "0.5", "1.0"]).pack(side="left")
        return f

    def _build_step_corners(self):
        f = self._frame()
        tk.Button(f, text="Auto-detect 4 corners", font=FONT,
                  command=self.auto_corners).pack(fill="x", pady=2)
        tk.Button(f, text="Clear corners, click again", font=FONT,
                  command=self.clear_corners).pack(fill="x", pady=2)
        tk.Button(f, text="Rotate corner order 90 deg", font=FONT,
                  command=lambda: self.rotate_order(1)).pack(fill="x", pady=2)
        self.lb_corners = tk.Label(f, text="", font=FONT_MONO,
                                   justify="left", anchor="w")
        self.lb_corners.pack(fill="x", pady=4)
        self._res_label(f)
        self._note(f, "Click the 4 corners in order: 1 top-left, 2 top-right, "
                      "3 bottom-right, 4 bottom-left. Corner 4 is the DSL "
                      "origin (0,0). Drag the coloured dots to adjust; use "
                      "the magnifier and zoom to hit the real corner of the "
                      "top face. If an edge is curved, still place the dot on "
                      "the true corner.")
        return f

    def _build_step_check(self):
        f = self._frame()
        self._res_label(f)
        tk.Checkbutton(f, text="Show mm grid", variable=self.v_grid,
                       font=FONT, command=self.refresh_view).pack(anchor="w")
        self._row(f, "Grid step", self.v_grid_step, unit="mm")
        tk.Button(f, text="Redraw grid", font=FONT,
                  command=self.refresh_view).pack(fill="x", pady=2)
        r = tk.Frame(f)
        r.pack(fill="x", pady=2)
        tk.Button(r, text="Rotate left 90", font=FONT,
                  command=lambda: self.rotate_result(1)).pack(side="left",
                                                              expand=True,
                                                              fill="x")
        tk.Button(r, text="Rotate right 90", font=FONT,
                  command=lambda: self.rotate_result(3)).pack(side="left",
                                                              expand=True,
                                                              fill="x")
        ttk.Separator(f).pack(fill="x", pady=4)
        tk.Label(f, text="Check size with the cutting-mat grid:",
                 font=FONT_B, anchor="w").pack(fill="x")
        self._row(f, "Mat grid pitch", self.v_mat_pitch, unit="mm")
        tk.Button(f, text="Measure mat grid through holes", font=FONT,
                  command=self.measure_grid).pack(fill="x", pady=2)
        self.lb_grid = tk.Label(f, text="", font=FONT, justify="left",
                                wraplength=self.wrap, anchor="w")
        self.lb_grid.pack(fill="x")
        self.btn_apply_size = tk.Button(f, text="Use suggested size",
                                        font=FONT, state="disabled",
                                        command=self.apply_suggested_size)
        self.btn_apply_size.pack(fill="x", pady=2)
        self._note(f, "Magenta grid = mm grid from the entered size, origin "
                      "(0,0) at bottom-left. If it drifts against the 1 cm "
                      "mat grid seen through the holes, the size or corners "
                      "are off. The mat lies one sheet thickness lower, so "
                      "expect an error of a few %.")
        return f

    def _build_step_mask(self):
        f = self._frame()
        r = tk.Frame(f)
        r.pack(fill="x")
        tk.Label(r, text="Method", font=FONT).pack(side="left")
        cb = ttk.Combobox(r, textvariable=self.v_method, state="readonly",
                          width=26, values=[m[1] for m in METHODS])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.recompute_auto(True))
        r = tk.Frame(f)
        r.pack(fill="x")
        tk.Label(r, text="Threshold", font=FONT).pack(side="left")
        tk.Scale(r, from_=0, to=255, orient="horizontal", variable=self.v_thr,
                 length=px(190), command=lambda v: self.schedule(
                     lambda: self.recompute_auto(False))).pack(side="left")
        tk.Button(r, text="Otsu", font=FONT,
                  command=lambda: self.recompute_auto(True)).pack(side="left")
        self._row(f, "Open (denoise)", self.v_open, unit="mm")
        self._row(f, "Close (fill gaps)", self.v_close, unit="mm")
        self._row(f, "Drop wood specks <", self.v_min_wood, unit="mm2")
        self._row(f, "Fill small holes <", self.v_min_hole, unit="mm2")
        self._row(f, "Cut border band", self.v_border, unit="mm")
        tk.Button(f, text="Apply", font=FONT,
                  command=lambda: self.recompute_auto(False)).pack(fill="x")
        r = tk.Frame(f)
        r.pack(fill="x")
        tk.Label(r, text="Overlay opacity", font=FONT).pack(side="left")
        tk.Scale(r, from_=0, to=1, resolution=0.05, orient="horizontal",
                 variable=self.v_alpha, length=px(150),
                 command=lambda v: self.schedule(self.refresh_view)
                 ).pack(side="left")
        ttk.Separator(f).pack(fill="x", pady=3)
        tk.Label(f, text="Brush (fix errors):", font=FONT_B,
                 anchor="w").pack(fill="x")
        r = tk.Frame(f)
        r.pack(fill="x")
        for val, txt in (("view", "View"), ("keep", "Paint WOOD"),
                         ("cut", "Paint CUT")):
            tk.Radiobutton(r, text=txt, value=val, font=FONT,
                           variable=self.v_brush_mode).pack(side="left")
        self._row(f, "Brush size", self.v_brush, unit="mm")
        r = tk.Frame(f)
        r.pack(fill="x", pady=2)
        tk.Button(r, text="Undo (Ctrl+Z)", font=FONT,
                  command=self.undo).pack(side="left", expand=True, fill="x")
        tk.Button(r, text="Clear strokes", font=FONT,
                  command=self.clear_edits).pack(side="left", expand=True,
                                                 fill="x")
        tk.Checkbutton(f, text="Show photo (off = mask only)",
                       variable=self.v_show_src, font=FONT,
                       command=self.refresh_view).pack(anchor="w")
        self._note(f, "Red = cut. Check shadows inside holes; use 'Paint "
                      "CUT' / 'Paint WOOD' to fix mistakes.")
        return f

    def _build_step_margin(self):
        f = self._frame()
        self._row(f, "Safety margin", self.v_margin, unit="mm")
        tk.Button(f, text="Preview", font=FONT,
                  command=self.recompute_final).pack(fill="x", pady=2)
        self.lb_stats = tk.Label(f, text="", font=FONT, justify="left",
                                 anchor="w", wraplength=self.wrap)
        self.lb_stats.pack(fill="x", pady=4)
        self._note(f, "Wood next to holes and sheet edges is shrunk by this "
                      "distance (orange) because of burnt, brittle edges, "
                      "kerf and re-placement error on the machine. 1-2 mm "
                      "is a good start.")
        return f

    def _build_step_align(self):
        f = self._frame()
        self._note(f, "Click 2 points on the sheet (your choice, e.g. near "
                      "two far-apart corners of a hole or the sheet). The "
                      "alignment gcode burns a small '+' at each point: put "
                      "the sheet on the machine, run it, nudge the sheet and "
                      "rerun until both crosses hit the marks.")
        r = tk.Frame(f)
        r.pack(fill="x")
        tk.Label(r, text="Click sets:", font=FONT).pack(side="left")
        for i in range(2):
            tk.Radiobutton(r, text="P%d" % (i + 1), value=i, font=FONT,
                           variable=self.v_pt_target).pack(side="left")
        for i in range(2):
            r = tk.Frame(f)
            r.pack(fill="x", pady=1)
            tk.Label(r, text="P%d  X" % (i + 1), font=FONT_B,
                     fg=("#d00000", "#0050d0")[i]).pack(side="left")
            for j, lab in enumerate(("X", "Y")):
                if j == 1:
                    tk.Label(r, text="Y", font=FONT_B,
                             fg=("#d00000", "#0050d0")[i]).pack(side="left")
                e = tk.Entry(r, textvariable=self.v_p[i][j], width=8,
                             font=FONT)
                e.pack(side="left")
                e.bind("<Return>", lambda ev: self.apply_point_entries())
                e.bind("<FocusOut>", lambda ev: self.apply_point_entries())
            tk.Label(r, text="mm", font=FONT).pack(side="left")
        tk.Label(f, textvariable=self.v_dist, font=FONT_B, justify="left",
                 anchor="w", wraplength=self.wrap).pack(fill="x", pady=3)
        tk.Button(f, text="Clear points", font=FONT,
                  command=self.clear_points).pack(fill="x", pady=1)
        ttk.Separator(f).pack(fill="x", pady=3)
        tk.Label(f, text="Alignment gcode:", font=FONT_B,
                 anchor="w").pack(fill="x")
        self._row(f, "Cross size", self.v_cross, unit="mm")
        self._row(f, "Power S (0-1000)", self.v_power)
        self._row(f, "Feed", self.v_feed, unit="mm/min")
        self._row(f, "Offset X", self.v_off_x, unit="mm")
        self._row(f, "Offset Y", self.v_off_y, unit="mm")
        tk.Checkbutton(f, text="Return to origin at the end",
                       variable=self.v_return, font=FONT).pack(anchor="w")
        r = tk.Frame(f)
        r.pack(fill="x", pady=2)
        tk.Button(r, text="Show gcode", font=FONT,
                  command=self.show_align_gcode).pack(side="left", expand=True,
                                                      fill="x")
        tk.Button(r, text="Send to Machine tab", font=FONT,
                  command=self.send_align_to_machine).pack(side="left",
                                                           expand=True,
                                                           fill="x")
        self._note(f, "Coordinates: sheet mm, origin (0,0) = bottom-left "
                      "corner, X right, Y up = machine coordinates + offset. "
                      "The same offset is used for the cut DSL in Strip "
                      "Packer. The gcode is saved as alignment.gcode in the "
                      "output folder at step 8.")
        return f

    def _build_step_save(self):
        f = self._frame()
        self._row(f, "Name", self.v_name, width=20)
        tk.Label(f, text="Output folder (parent):", font=FONT,
                 anchor="w").pack(fill="x")
        r = tk.Frame(f)
        r.pack(fill="x")
        tk.Entry(r, textvariable=self.v_out_root, font=FONT_S,
                 width=30).pack(side="left", fill="x", expand=True)
        tk.Button(r, text="...", font=FONT,
                  command=self.ask_out_root).pack(side="left")
        tk.Button(f, text="Save to output/<name>/", font=FONT_B,
                  command=self.save).pack(fill="x", pady=4)
        tk.Button(f, text="Open in Strip Packer", font=FONT,
                  command=self.open_packer).pack(fill="x", pady=2)
        self.lb_saved = tk.Label(f, text="", font=FONT, justify="left",
                                 wraplength=self.wrap, anchor="w")
        self.lb_saved.pack(fill="x", pady=4)
        self._note(f, "Writes into <output>/<name>/: mask.png (final mask, "
                      "255 = wood, 0 = cut), mask.json (size, mm/px, margin, "
                      "alignment points), mask_raw.png (before margin), "
                      "mask_warped.png (warped photo) and alignment.gcode. "
                      "If the folder exists you can overwrite it or save to "
                      "<name>_2.")
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
        self.update_res_info()
        self.refresh_view(fit=True)

    def next_step(self):
        try:
            ok = self._leave_step(self.step)
        except Exception as ex:  # thong bao loi nhap lieu
            messagebox.showerror("Error", str(ex))
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
                messagebox.showwarning("No image", "Open an image first.")
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
                messagebox.showwarning("Missing corners",
                                       "Exactly 4 corners are required.")
                return False
            self.do_warp()
        if i == 3:
            if self.auto is None or self.auto.shape != self.warped.shape[:2]:
                self.recompute_auto(True)
        if i == 4:
            self.recompute_final()
        if i == STEP_ALIGN:
            if self.align_pts[0] is None or self.align_pts[1] is None:
                if not messagebox.askyesno(
                        "Alignment", "Fewer than 2 alignment points are set. "
                        "Continue anyway?"):
                    return False
            self.align_params()       # kiem tra tham so gcode
        return True

    # ------------------------------------------------------------------
    # Tham so
    # ------------------------------------------------------------------
    def get_size(self):
        """Tra ve (W, H) mm."""
        try:
            w = float(self.v_w.get())
            h = float(self.v_h.get())
        except ValueError:
            raise ValueError("Width and height must be numbers")
        if w <= 0 or h <= 0:
            raise ValueError("Width and height must be > 0")
        return w, h

    def compute_res(self):
        """
        Do phan giai dung de nan: tu dong tu 4 goc (mac dinh) hoac nhap tay
        (tuy chon nang cao). Tra ve (mm_per_px, mode, rx, ry).
        """
        w, h = self.get_size()
        if self.v_res_override.get():
            try:
                r = float(self.v_res.get())
            except ValueError:
                raise ValueError("Manual mm/px must be a number")
            if r <= 0:
                raise ValueError("Manual mm/px must be > 0")
            return r, "manual", None, None
        if len(self.corners) != 4:
            raise ValueError("Pick 4 corners first to compute mm/px")
        r, rx, ry = sc.auto_resolution(self.corners, w, h)
        return r, "auto", rx, ry

    def update_res_info(self):
        try:
            r, mode, rx, ry = self.compute_res()
        except ValueError as ex:
            if self.res and self.src is None:
                self.v_res_info.set("Resolution (from file): %.4f mm/px = "
                                    "%.3f px/mm" % (self.res, 1 / self.res))
            else:
                self.v_res_info.set("Resolution: %s" % ex)
            return
        w, h = self.get_size()
        txt = "Resolution (%s): %.4f mm/px = %.3f px/mm\nWarped image: " \
              "%d x %d px" % (mode, r, 1 / r, int(round(w / r)),
                              int(round(h / r)))
        if rx and ry:
            diff = 100.0 * abs(rx - ry) / ((rx + ry) / 2)
            txt += "\nX: %.4f, Y: %.4f mm/px (diff %.1f%%)" % (rx, ry, diff)
            if diff > 3:
                txt += "\nWARNING: X/Y differ a lot - check W x H and corners"
        self.v_res_info.set(txt)

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
            title="Open sheet photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff "
                                  "*.webp"),
                       ("All files", "*.*")])
        if p:
            self.open_image(p)

    def open_image(self, path):
        try:
            img = sc.imread_unicode(path)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            return
        self.src = img
        self.src_path = path
        self.corners = []
        self.warped = self.auto = self.raw = self.final = None
        self.res = None
        self.loaded_mask = None
        self.edits = None
        self.undo_stack = []
        if self.method_key() == "saved":
            self.v_method.set(METHODS[0][1])
        self.align_pts = [None, None]
        self.v_name.set(sc.sanitize_name(
            os.path.splitext(os.path.basename(path))[0]))
        self.update_points_ui()
        self.lb_src.config(text="%s\n%d x %d px" % (
            os.path.basename(path), img.shape[1], img.shape[0]))
        self.refresh_view(fit=True)

    def ask_load_mask(self):
        p = filedialog.askopenfilename(
            title="Open saved mask", initialdir=sc.default_output_root(),
            filetypes=[("Mask JSON / PNG", "*.json *.png"),
                       ("All files", "*.*")])
        if p:
            self.load_mask(p)

    def load_mask(self, path):
        try:
            mask, meta, folder = sc.load_mask_file(path)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
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
        self.v_margin.set("%g" % meta.get("margin_mm", 1.0))
        self.res = float(meta["mm_per_px"])
        self.res_mode = meta.get("mm_per_px_mode", "auto")
        self.src = None
        self.src_path = meta.get("source", "")
        self.corners = []
        self.warped = warped
        self.loaded_mask = raw
        self.auto = raw.copy()
        self.edits = np.zeros(raw.shape, np.int8)
        self.undo_stack = []
        self.v_method.set(METHODS[-1][1])
        al = meta.get("alignment") or {}
        pts = (al.get("points_mm") or []) + [None, None]
        self.align_pts = [list(p) if p else None for p in pts[:2]]
        self.v_cross.set("%g" % al.get("cross_mm", 5.0))
        self.v_power.set("%d" % al.get("power", 100))
        self.v_feed.set("%g" % al.get("feed", 200.0))
        off = al.get("offset_mm", [0.0, 0.0])
        self.v_off_x.set("%g" % off[0])
        self.v_off_y.set("%g" % off[1])
        self.v_return.set(bool(al.get("return_home", True)))
        self.update_points_ui()
        # Thu muc dang mo => mac dinh luu de len chinh no
        self.v_out_root.set(os.path.dirname(folder))
        self.v_name.set(os.path.basename(folder))
        self.lb_src.config(text="Mask: %s\n%g x %g mm, %.4f mm/px" % (
            os.path.basename(path), meta["width_mm"], meta["height_mm"],
            self.res))
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
                messagebox.showinfo("Not found",
                                    "Could not detect the corners, please "
                                    "click them manually.")
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
        w, h = self.get_size()
        res, mode, _, _ = self.compute_res()
        if (w / res) * (h / res) > 60e6:
            raise ValueError("Warped image would be too large; increase "
                             "mm/px (advanced override)")
        self.res, self.res_mode = res, mode
        self.warped = sc.warp_sheet(self.src, self.corners, w, h, res)
        self.auto = self.raw = self.final = None
        self.edits = np.zeros(self.warped.shape[:2], np.int8)
        self.undo_stack = []
        self.update_res_info()

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
        w, h = self.get_size()
        res = self.res
        m, _ = sc.auto_mask(self.warped, res)
        gx, gy = sc.estimate_grid_period_mm(self.warped, m, res)
        pitch = self._f(self.v_mat_pitch, 10.0)
        if not gx or not gy:
            self.lb_grid.config(text="Could not measure (few holes / "
                                     "blurry grid).")
            return
        sw, sh = w * pitch / gx, h * pitch / gy
        self._suggest = (sw, sh)
        self.lb_grid.config(text=(
            "Measured grid period: x = %.2f mm, y = %.2f mm\n"
            "(using the entered size %g x %g)\n"
            "=> if the mat grid is %g mm, the sheet is ~ %.0f x %.0f mm"
            % (gx, gy, w, h, pitch, sw, sh)))
        self.btn_apply_size.config(state="normal")

    def apply_suggested_size(self):
        if not self._suggest or self.src is None:
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
        res = self.res
        key = self.method_key()
        if key == "saved":
            if self.loaded_mask is None:
                messagebox.showinfo("Note", "No mask has been loaded from "
                                            "a file.")
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
        r = max(1, int(round(self._f(self.v_brush, 3) / 2 / self.res)))
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
        res = self.res
        margin = self._f(self.v_margin, 0)
        self.final = sc.erode_margin(self.raw, margin, res)
        st = sc.wood_area_stats(self.final, res)
        rs = sc.wood_area_stats(self.raw, res)
        self.lb_stats.config(
            text="Remaining wood (before margin): %.0f mm2 = %.1f%% of sheet\n"
                 "Usable wood (after margin): %.0f mm2 = %.1f%% of sheet\n"
                 "Sheet area: %.0f mm2" % (
                     rs["wood_area_mm2"], 100 * rs["wood_ratio"],
                     st["wood_area_mm2"], 100 * st["wood_ratio"],
                     st["sheet_area_mm2"]))
        self.refresh_view()

    # ------------------------------------------------------------------
    # Buoc 7: luu
    # ------------------------------------------------------------------
    def ask_out_root(self):
        d = filedialog.askdirectory(title="Output parent folder",
                                    initialdir=self.v_out_root.get())
        if d:
            self.v_out_root.set(d)

    def save(self, ask=True):
        """Luu tat ca vao <output>/<name>/. ask=False: ghi de khong hoi."""
        if self.raw is None:
            messagebox.showwarning("No mask", "Create the mask first.")
            return None
        if self.final is None:
            self.recompute_final()
        try:
            align = self.align_params()
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))
            return None
        root = self.v_out_root.get().strip() or sc.default_output_root()
        name = sc.sanitize_name(self.v_name.get())
        self.v_name.set(name)
        folder = os.path.join(root, name)
        if ask and sc.output_dir_has_files(folder):
            ans = messagebox.askyesnocancel(
                "Folder exists",
                "%s already exists.\n\nYes = overwrite\nNo = save to a new "
                "folder (%s)\nCancel = do nothing" % (
                    folder, os.path.basename(sc.unique_dir(root, name))))
            if ans is None:
                return None
            if ans is False:
                folder = sc.unique_dir(root, name)
                self.v_name.set(os.path.basename(folder))
        os.makedirs(folder, exist_ok=True)
        w, h = self.get_size()
        extra = {"mm_per_px_mode": self.res_mode,
                 "method": self.method_key(),
                 "threshold": int(self.v_thr.get()),
                 "name": os.path.basename(folder),
                 "alignment": align}
        gpath = None
        if any(p is not None for p in align["points_mm"]):
            gpath = ac.write_alignment_gcode(folder, align)
            align["gcode_file"] = os.path.basename(gpath)
        png, js = sc.save_mask_file(
            os.path.join(folder, sc.MASK_BASENAME + ".png"), self.final, w, h,
            self.res, self._f(self.v_margin, 0), source=self.src_path,
            raw_mask=self.raw, warped=self.warped,
            corners=self.corners if len(self.corners) == 4 else None,
            extra=extra)
        self.last_saved = js
        st = sc.wood_area_stats(self.final, self.res)
        self.lb_saved.config(text="Saved to:\n%s\n\n%s\n\nWood ratio: %.1f%% "
                             "(%.0f / %.0f mm2)" % (
            folder, "\n".join(sorted(os.listdir(folder))),
            100 * st["wood_ratio"], st["wood_area_mm2"],
            st["sheet_area_mm2"]))
        return js

    def open_packer(self):
        if not self.last_saved:
            messagebox.showinfo("Not saved", "Save the mask first.")
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
        res = self.res or 0.5
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
            return sc.overlay_mask(base, self.raw, self.v_alpha.get(),
                                   extra=lost)
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
                                      font=FONT_L)
        if self.step >= STEP_ALIGN and self.warped is not None and self.res:
            self.draw_align_points()
        if self.step == 3 and self.warped is not None:
            # Danh dau goc (0,0) DSL
            cx, cy = self.view.img_to_canvas(0, self.warped.shape[0])
            self.view.create_text(cx + 4, cy - 4, text="(0,0)", anchor="sw",
                                  fill="yellow", font=FONT_B)

    def update_status(self):
        if self.step == 2:
            lines = []
            for i in range(4):
                if i < len(self.corners):
                    lines.append("%-20s %7.1f %7.1f" % (
                        CORNER_NAMES[i], *self.corners[i]))
                else:
                    lines.append("%-20s   (not set)" % CORNER_NAMES[i])
            self.lb_corners.config(text="\n".join(lines))
            self.update_res_info()

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
            if best is not None and bd < px(15) ** 2:
                self._drag_idx = best
            elif len(self.corners) < 4:
                self.corners.append([x, y])
                self._drag_idx = len(self.corners) - 1
                self.refresh_view()
        elif self.step == STEP_ALIGN and self.warped is not None:
            # Keo diem gan con tro, neu khong thi dat diem dang chon
            self._drag_pt = None
            for i, p in enumerate(self.align_pts):
                if p is None:
                    continue
                cx, cy = self.view.img_to_canvas(*self.mm_to_img(*p))
                if (cx - e.x) ** 2 + (cy - e.y) ** 2 < px(12) ** 2:
                    self._drag_pt = i
            if self._drag_pt is None:
                self._drag_pt = self.v_pt_target.get()
                self.set_point(self._drag_pt, x, y)
                # Dat xong P1 thi chuyen sang P2
                if self._drag_pt == 0 and self.align_pts[1] is None:
                    self.v_pt_target.set(1)
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
        elif self.step == STEP_ALIGN and self._drag_pt is not None:
            self.set_point(self._drag_pt, x, y)
        self.on_motion(e)

    def on_release(self, e):
        self._drag_idx = None
        self._drag_pt = None
        if self._painting:
            self._painting = False
            self.refresh_view()

    def on_motion(self, e):
        x, y = self.view.canvas_to_img(e.x, e.y)
        img = self.view.img
        if img is None:
            return
        rad = None
        if self.step == 4 and self.v_brush_mode.get() != "view" and self.res:
            rad = self._f(self.v_brush, 3) / 2 / self.res
        self.magnifier.show(img, x, y, rad)
        txt = "x=%.0f y=%.0f px" % (x, y)
        if self.step >= 3 and self.warped is not None and self.res:
            txt += "  |  DSL: x=%.1f y=%.1f mm" % (
                x * self.res, (self.warped.shape[0] - y) * self.res)
        self.v_status.set(txt)

    # ------------------------------------------------------------------
    # Buoc 7: diem can chinh
    # ------------------------------------------------------------------
    def mm_to_img(self, xm, ym):
        return xm / self.res, self.warped.shape[0] - ym / self.res

    def set_point(self, i, x_img, y_img):
        """Dat diem i tu toa do anh (pixel, so thuc) -> mm toa do tam."""
        h, w = self.warped.shape[:2]
        x_img = min(max(x_img, 0), w)
        y_img = min(max(y_img, 0), h)
        self.align_pts[i] = [round(float(x_img) * self.res, 2),
                             round(float(h - y_img) * self.res, 2)]
        self.update_points_ui()
        self.view.redraw()

    def clear_points(self):
        self.align_pts = [None, None]
        self.v_pt_target.set(0)
        self.update_points_ui()
        self.view.redraw()

    def apply_point_entries(self):
        """Nhap tay toa do diem (mm)."""
        for i in range(2):
            sx, sy = self.v_p[i][0].get().strip(), self.v_p[i][1].get().strip()
            if not sx and not sy:
                self.align_pts[i] = None
                continue
            try:
                self.align_pts[i] = [round(float(sx), 2), round(float(sy), 2)]
            except ValueError:
                pass
        self.update_points_ui()
        self.view.redraw()

    def update_points_ui(self):
        for i in range(2):
            p = self.align_pts[i]
            self.v_p[i][0].set("" if p is None else "%.2f" % p[0])
            self.v_p[i][1].set("" if p is None else "%.2f" % p[1])
        p1, p2 = self.align_pts
        if p1 is not None and p2 is not None:
            self.v_dist.set("Distance P1-P2: %.2f mm\n(dX %.2f, dY %.2f mm)"
                            % (ac.distance(p1, p2), p2[0] - p1[0],
                               p2[1] - p1[1]))
        else:
            self.v_dist.set("Distance P1-P2: set both points")

    def align_params(self):
        try:
            cross = float(self.v_cross.get())
            power = float(self.v_power.get())
            feed = float(self.v_feed.get())
            ox = float(self.v_off_x.get() or 0)
            oy = float(self.v_off_y.get() or 0)
        except ValueError:
            raise ValueError("Alignment gcode settings must be numbers")
        if cross <= 0 or feed <= 0 or not 0 <= power <= 1000:
            raise ValueError("Cross size and feed must be > 0, power 0-1000")
        w, h = self.get_size()
        for i, p in enumerate(self.align_pts):
            if p is not None and not (0 <= p[0] <= w and 0 <= p[1] <= h):
                raise ValueError("P%d (%.2f, %.2f) is outside the sheet "
                                 "(0..%g, 0..%g mm)" % (i + 1, p[0], p[1], w, h))
        # Giu dung vi tri P1 / P2 (null neu chua dat)
        return {"points_mm": [None if p is None else list(p)
                              for p in self.align_pts],
                "cross_mm": cross, "power": int(round(power)), "feed": feed,
                "offset_mm": [ox, oy], "return_home": bool(self.v_return.get()),
                "frame": "sheet mm, origin bottom-left, X right, Y up; "
                         "machine = sheet + offset_mm"}

    def align_gcode_lines(self):
        al = self.align_params()
        return ac.alignment_gcode(al["points_mm"], al["cross_mm"], al["power"],
                                  al["feed"], al["offset_mm"],
                                  al["return_home"])

    def show_align_gcode(self):
        try:
            lines = self.align_gcode_lines()
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))
            return
        top = tk.Toplevel(self.root)
        top.title("Alignment gcode")
        t = tk.Text(top, font=FONT_MONO, width=40, height=30)
        t.pack(fill="both", expand=True)
        t.insert("1.0", "\n".join(lines))

    def send_align_to_machine(self):
        try:
            lines = self.align_gcode_lines()
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))
            return
        path = ac.cut_plan_path()
        if not os.path.isdir(os.path.dirname(path)):
            messagebox.showerror("Error", "engraver_ctrl folder not found:\n"
                                 + os.path.dirname(path))
            return
        if not messagebox.askyesno(
                "Send to Machine tab",
                "Overwrite %s with the alignment gcode?\n(The Machine tab "
                "runs this file.)" % path):
            return
        with open(path, "w") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("Done", "Wrote alignment gcode to\n" + path)

    def draw_align_points(self):
        cross = self._f(self.v_cross, 5.0)
        for i, p in enumerate(self.align_pts):
            if p is None:
                continue
            col = ("#ff2020", "#2080ff")[i]
            cx, cy = self.view.img_to_canvas(*self.mm_to_img(*p))
            half = max(6, cross / 2 / self.res * self.view.scale)
            self.view.create_line(cx - half, cy, cx + half, cy, fill=col,
                                  width=2)
            self.view.create_line(cx, cy - half, cx, cy + half, fill=col,
                                  width=2)
            self.view.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, outline=col)
            # Nhan co nen toi de doc duoc tren ca vung do / go; dat ben trai
            # diem neu gan mep phai canvas
            right = cx + half + 170 < self.view.winfo_width()
            t = self.view.create_text(
                cx + half + 4 if right else cx - half - 4, cy - 4,
                anchor="sw" if right else "se", fill=col,
                font=FONT_B,
                text="P%d (%.2f, %.2f)" % (i + 1, *p))
            bb = self.view.bbox(t)
            if bb:
                r = self.view.create_rectangle(bb[0] - 2, bb[1] - 1, bb[2] + 2,
                                               bb[3] + 1, fill="#202020",
                                               outline="")
                self.view.tag_lower(r, t)
        p1, p2 = self.align_pts
        if p1 is not None and p2 is not None:
            a = self.view.img_to_canvas(*self.mm_to_img(*p1))
            b = self.view.img_to_canvas(*self.mm_to_img(*p2))
            self.view.create_line(*a, *b, fill="#ffff00", dash=(4, 3))
            t = self.view.create_text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2,
                                      fill="#ffff00",
                                      font=FONT_B,
                                      text="%.2f mm" % ac.distance(p1, p2))
            bb = self.view.bbox(t)
            if bb:
                r = self.view.create_rectangle(bb[0] - 2, bb[1] - 1, bb[2] + 2,
                                               bb[3] + 1, fill="#202020",
                                               outline="")
                self.view.tag_lower(r, t)


def main():
    ui_util.enable_dpi_awareness()      # phai goi truoc khi tao Tk
    root = tk.Tk()
    ui_util.init_scaling(root)
    root.title("Plywood Scan - digitize the remaining sheet")
    ui_util.fit_geometry(root, 1280, 860)
    app = ScanApp(root, sys.argv[1] if len(sys.argv) > 1 else None)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
