"""
Canvas hien thi anh co zoom (lan chuot) va keo (chuot phai / giua),
dung chung cho scan_app va strip_packer.
"""
import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk


class ImageView(tk.Canvas):

    def __init__(self, parent, **kw):
        kw.setdefault("bg", "#303030")
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self.img = None          # anh BGR dang hien thi
        self.scale = 1.0         # pixel canvas / pixel anh
        self.ox = 0.0            # vi tri goc anh tren canvas
        self.oy = 0.0
        self._photo = None
        self._pan_start = None
        self.on_redraw = None    # callback ve them (handle, ...) sau khi ve anh
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<MouseWheel>", self._on_wheel)          # Windows / mac
        self.bind("<Button-4>", lambda e: self._zoom_at(e.x, e.y, 1.25))
        self.bind("<Button-5>", lambda e: self._zoom_at(e.x, e.y, 0.8))
        for b in ("<ButtonPress-2>", "<ButtonPress-3>"):
            self.bind(b, self._pan_begin)
        for b in ("<B2-Motion>", "<B3-Motion>"):
            self.bind(b, self._pan_move)

    # ---- toa do ----
    def img_to_canvas(self, x, y):
        return self.ox + x * self.scale, self.oy + y * self.scale

    def canvas_to_img(self, cx, cy):
        return (cx - self.ox) / self.scale, (cy - self.oy) / self.scale

    # ---- anh ----
    def set_image(self, img, fit=False):
        changed = (self.img is None or img is None
                   or self.img.shape[:2] != img.shape[:2])
        self.img = img
        if fit or changed:
            self.fit()
        else:
            self.redraw()

    def fit(self):
        if self.img is None:
            self.redraw()
            return
        cw = max(self.winfo_width(), 50)
        ch = max(self.winfo_height(), 50)
        ih, iw = self.img.shape[:2]
        self.scale = min(cw / iw, ch / ih) * 0.96
        self.ox = (cw - iw * self.scale) / 2
        self.oy = (ch - ih * self.scale) / 2
        self.redraw()

    def redraw(self):
        self.delete("all")
        if self.img is not None:
            cw = max(self.winfo_width(), 1)
            ch = max(self.winfo_height(), 1)
            ih, iw = self.img.shape[:2]
            # Chi cat phan anh dang nhin thay de ve nhanh khi zoom lon
            x0, y0 = self.canvas_to_img(0, 0)
            x1, y1 = self.canvas_to_img(cw, ch)
            x0 = int(max(0, np.floor(x0)))
            y0 = int(max(0, np.floor(y0)))
            x1 = int(min(iw, np.ceil(x1)))
            y1 = int(min(ih, np.ceil(y1)))
            if x1 > x0 and y1 > y0:
                crop = self.img[y0:y1, x0:x1]
                tw = max(1, int(round((x1 - x0) * self.scale)))
                th = max(1, int(round((y1 - y0) * self.scale)))
                interp = cv2.INTER_NEAREST if self.scale > 1 else cv2.INTER_AREA
                disp = cv2.resize(crop, (tw, th), interpolation=interp)
                if disp.ndim == 2:
                    disp = cv2.cvtColor(disp, cv2.COLOR_GRAY2RGB)
                else:
                    disp = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
                self._photo = ImageTk.PhotoImage(Image.fromarray(disp))
                px, py = self.img_to_canvas(x0, y0)
                self.create_image(px, py, image=self._photo, anchor="nw")
        if self.on_redraw:
            self.on_redraw()

    # ---- zoom / pan ----
    def _on_wheel(self, e):
        self._zoom_at(e.x, e.y, 1.25 if e.delta > 0 else 0.8)

    def _zoom_at(self, cx, cy, f):
        if self.img is None:
            return
        new = min(max(self.scale * f, 0.05), 40)
        f = new / self.scale
        self.ox = cx - (cx - self.ox) * f
        self.oy = cy - (cy - self.oy) * f
        self.scale = new
        self.redraw()

    def _pan_begin(self, e):
        self._pan_start = (e.x, e.y, self.ox, self.oy)

    def _pan_move(self, e):
        if self._pan_start is None:
            return
        sx, sy, ox, oy = self._pan_start
        self.ox = ox + e.x - sx
        self.oy = oy + e.y - sy
        self.redraw()


class Magnifier(tk.Canvas):
    """Kinh lup: phong to vung quanh con tro de dat goc / to chinh xac."""

    def __init__(self, parent, size=180, zoom=5, **kw):
        super().__init__(parent, width=size, height=size, bg="black",
                         highlightthickness=1, highlightbackground="#888",
                         **kw)
        self.size = size
        self.zoom = zoom
        self._photo = None

    def show(self, img, x, y, radius_px=None):
        self.delete("all")
        if img is None:
            return
        half = self.size // (2 * self.zoom)
        ih, iw = img.shape[:2]
        xi, yi = int(round(x)), int(round(y))
        pad = cv2.copyMakeBorder(img, half, half, half, half,
                                 cv2.BORDER_CONSTANT, value=0)
        crop = pad[yi:yi + 2 * half + 1, xi:xi + 2 * half + 1]
        if crop.size == 0:
            return
        disp = cv2.resize(crop, (self.size, self.size),
                          interpolation=cv2.INTER_NEAREST)
        if disp.ndim == 2:
            disp = cv2.cvtColor(disp, cv2.COLOR_GRAY2RGB)
        else:
            disp = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        self._photo = ImageTk.PhotoImage(Image.fromarray(disp))
        self.create_image(0, 0, image=self._photo, anchor="nw")
        c = self.size / 2
        self.create_line(c, 0, c, self.size, fill="#00ff00")
        self.create_line(0, c, self.size, c, fill="#00ff00")
        if radius_px:
            r = radius_px * self.size / (2 * half + 1)
            self.create_oval(c - r, c - r, c + r, c + r, outline="yellow")
