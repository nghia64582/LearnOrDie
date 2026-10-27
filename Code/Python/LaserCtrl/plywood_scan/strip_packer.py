"""
Tool 2: Xep cac thanh chu nhat (vd que rong 10mm) vao vung go con lai
(mask do scan_app tao ra), xuat DSL de dan vao tab Designer.

Chay:  python strip_packer.py  [file_mask.json|png]

Che do chinh (Required pieces): nguoi dung nhap danh sach do dai can cat,
vd "80,80,100,100" (be rong mac dinh 10mm). Tool co gang dat DUNG cac thanh
nay, bao thanh nao khong vua.
Che do phu (Auto-fill): tu lap day vung go bang cac thanh dai [min, max].

DSL xuat ra, moi thanh la mot khung toa do cuc bo:
    ADD x y <so thu tu>
    R 0 0 w h
    END
=> co the them chi tiet (JF / JM, lo...) ben trong tung thanh.

Dung nhu thu vien:
    from strip_packer import pack_pieces, load_mask_file, strips_to_dsl
    mask, meta, _ = load_mask_file("tam1_mask.json")
    res = pack_pieces(mask, meta["mm_per_px"], [80, 80, 100, 100],
                      strip_w=10, gap=0.5)
    print(res["count"], res["unplaced"])

Toa do DSL: goc (0, 0) = goc DUOI-TRAI cua tam (goc so 4 khi chon goc trong
scan_app), x sang phai, y huong LEN, don vi mm.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from pack_core import (pack_pieces, pack_strips, parse_lengths,
                       verify_strips, strips_to_dsl, parse_dsl_strips,
                       render_result)
from scan_core import (load_mask_file, imread_unicode, imwrite_unicode,
                       default_output_root)
import align_core as ac
import ui_util
from ui_util import px
from image_view import ImageView

# Ham lo ra ngoai khi import strip_packer nhu thu vien
__all__ = ["pack_pieces", "pack_strips", "parse_lengths", "verify_strips",
           "strips_to_dsl", "parse_dsl_strips", "render_result",
           "load_mask_file", "StripPackerApp"]

# Font lon hon scan_app 2pt cho de doc
FONT = ("Times New Roman", 13)
FONT_B = ("Times New Roman", 13, "bold")
FONT_S = ("Arial", 11)
FONT_MONO = ("Courier", 11)


class StripPackerApp(ttk.Frame):

    def __init__(self, parent, path=None):
        super().__init__(parent)
        self.root = parent
        self.mask = None
        self.meta = None
        self.warped = None
        self.path = ""
        self.result = None

        self.v_mode = tk.StringVar(value="pieces")
        self.v_lengths = tk.StringVar(value="80,80,100,100")
        self.v_w = tk.StringVar(value="10")
        self.v_gap = tk.StringVar(value="0.5")
        self.v_orient = tk.StringVar(value="both")
        self.v_min = tk.StringVar(value="30")
        self.v_max = tk.StringVar(value="100")
        self.v_step = tk.StringVar(value="0")
        self.v_obj = tk.StringVar(value="length")
        self.v_show_photo = tk.BooleanVar(value=True)
        self.v_labels = tk.BooleanVar(value=True)
        self._style()
        self.build_gui()
        self.update_mode()
        if path:
            self.root.after(100, lambda: self.load(path))

    def _style(self):
        st = ttk.Style(self.root)
        st.configure("TRadiobutton", font=FONT)
        st.configure("TCheckbutton", font=FONT)

    def build_gui(self):
        self.wrap = px(400)
        left = tk.Frame(self, width=px(430))
        left.pack(side="left", fill="y", padx=5, pady=5)
        left.pack_propagate(False)

        tk.Button(left, text="Open mask (.json / .png)...", font=FONT,
                  command=self.ask_load).pack(fill="x", pady=2)
        self.lb_file = tk.Label(left, text="No mask loaded", font=FONT,
                                justify="left", wraplength=self.wrap,
                                anchor="w")
        self.lb_file.pack(fill="x", pady=2)
        ttk.Separator(left).pack(fill="x", pady=4)

        r = tk.Frame(left)
        r.pack(fill="x")
        tk.Label(r, text="Mode:", font=FONT_B).pack(side="left")
        for v, t in (("pieces", "Required pieces"), ("auto", "Auto-fill")):
            tk.Radiobutton(r, text=t, value=v, variable=self.v_mode,
                           font=FONT, command=self.update_mode
                           ).pack(side="left")

        # --- che do chinh: danh sach thanh ---
        self.fr_pieces = tk.Frame(left)
        tk.Label(self.fr_pieces, text="Piece lengths (mm):", font=FONT_B,
                 anchor="w").pack(fill="x")
        e = tk.Entry(self.fr_pieces, textvariable=self.v_lengths, font=FONT)
        e.pack(fill="x")
        e.bind("<Return>", lambda ev: self.run())
        tk.Label(self.fr_pieces, font=FONT_S, fg="#444", justify="left",
                 anchor="w", wraplength=self.wrap,
                 text="Separate with commas, spaces or semicolons, e.g. "
                      "80,80,100,100. '100x3' = three pieces of 100 mm. "
                      "Piece numbers follow this order (1, 2, 3...)."
                 ).pack(fill="x")

        # --- che do phu: tu lap day ---
        self.fr_auto = tk.Frame(left)
        self._row(self.fr_auto, "Min length", self.v_min, "mm")
        self._row(self.fr_auto, "Max length", self.v_max, "mm")
        self._row(self.fr_auto, "Length step (0=free)", self.v_step, "mm")
        r = tk.Frame(self.fr_auto)
        r.pack(fill="x")
        tk.Label(r, text="Objective:", font=FONT).pack(side="left")
        for v, t in (("length", "Max total length"), ("count", "Max count")):
            tk.Radiobutton(r, text=t, value=v, variable=self.v_obj,
                           font=FONT).pack(side="left")

        self.fr_common = tk.Frame(left)
        self._row(self.fr_common, "Strip width", self.v_w, "mm")
        self._row(self.fr_common, "Gap / kerf", self.v_gap, "mm")
        r = tk.Frame(self.fr_common)
        r.pack(fill="x")
        tk.Label(r, text="Orientation:", font=FONT).pack(side="left")
        for v, t in (("both", "Both"), ("H", "Horiz. (X)"),
                     ("V", "Vert. (Y)")):
            tk.Radiobutton(r, text=t, value=v, variable=self.v_orient,
                           font=FONT).pack(side="left")
        tk.Button(self.fr_common, text="Compute", font=FONT_B,
                  command=self.run).pack(fill="x", pady=6)
        r = tk.Frame(self.fr_common)
        r.pack(fill="x")
        tk.Checkbutton(r, text="Photo background", variable=self.v_show_photo,
                       font=FONT, command=self.redraw).pack(side="left")
        tk.Checkbutton(r, text="Piece numbers", variable=self.v_labels,
                       font=FONT, command=self.redraw).pack(side="left")
        self.lb_result = tk.Label(self.fr_common, text="", font=FONT,
                                  justify="left", wraplength=self.wrap,
                                  anchor="w")
        self.lb_result.pack(fill="x", pady=2)
        self.lb_unplaced = tk.Label(self.fr_common, text="", font=FONT_B,
                                    justify="left", wraplength=self.wrap,
                                    anchor="w", fg="#c00000")
        self.lb_unplaced.pack(fill="x")
        r = tk.Frame(self.fr_common)
        r.pack(fill="x", pady=2)
        tk.Button(r, text="Export DSL (.txt)", font=FONT,
                  command=self.export_txt).pack(side="left", expand=True,
                                                fill="x")
        tk.Button(r, text="Copy DSL", font=FONT,
                  command=self.copy_dsl).pack(side="left", expand=True,
                                              fill="x")
        tk.Button(self.fr_common, text="Save result image (.png)", font=FONT,
                  command=self.export_png).pack(fill="x", pady=2)
        self.txt = tk.Text(self.fr_common, height=10, font=FONT_MONO)
        self.txt.pack(fill="both", expand=True, pady=2)
        tk.Label(self.fr_common, font=FONT_S, fg="#444", justify="left",
                 wraplength=self.wrap, anchor="w",
                 text="DSL: each piece is 'ADD x y <number>' / 'R 0 0 w h' / "
                      "'END', so you can add JF/JM or holes inside a piece "
                      "in local coordinates. Origin (0,0) = BOTTOM-LEFT "
                      "corner of the sheet (corner 4), x right, y up, mm."
                 ).pack(fill="x")

        right = tk.Frame(self)
        right.pack(side="right", fill="both", expand=True)
        self.view = ImageView(right, width=px(850), height=px(750))
        self.view.pack(fill="both", expand=True)
        tk.Label(right, font=FONT_S, fg="#555",
                 text="Green = horizontal, blue = vertical, red = cut, "
                      "number = piece, + = alignment point | wheel: zoom | "
                      "right drag: pan"
                 ).pack(fill="x")

    def _row(self, parent, label, var, unit):
        r = tk.Frame(parent)
        r.pack(fill="x", pady=1)
        tk.Label(r, text=label, font=FONT, width=20,
                 anchor="w").pack(side="left")
        tk.Entry(r, textvariable=var, width=8, font=FONT).pack(side="left")
        tk.Label(r, text=unit, font=FONT).pack(side="left")

    def update_mode(self):
        self.fr_pieces.pack_forget()
        self.fr_auto.pack_forget()
        self.fr_common.pack_forget()
        (self.fr_pieces if self.v_mode.get() == "pieces"
         else self.fr_auto).pack(fill="x", pady=4)
        self.fr_common.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def ask_load(self):
        p = filedialog.askopenfilename(
            title="Open mask", initialdir=default_output_root(), filetypes=[("Mask", "*.json *.png"),
                                         ("All files", "*.*")])
        if p:
            self.load(p)

    def load(self, path):
        try:
            mask, meta, folder = load_mask_file(path)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            return
        self.mask, self.meta, self.path = mask, meta, path
        self.warped = None
        wf = meta.get("warped_file")
        if wf and os.path.exists(os.path.join(folder, wf)):
            w = imread_unicode(os.path.join(folder, wf))
            if w.shape[:2] == mask.shape:
                self.warped = w
        self.result = None
        info = "%s\n%g x %g mm, %.4f mm/px, margin %g mm" % (
            os.path.relpath(path, os.path.dirname(os.path.dirname(
                os.path.abspath(path)))), meta["width_mm"], meta["height_mm"],
            meta["mm_per_px"], meta.get("margin_mm", 0))
        al = self.alignment()
        pts = al.get("points_mm") or []
        if any(p is not None for p in pts):
            info += "\nAlignment: " + ", ".join(
                "P%d (%.2f, %.2f)" % (i + 1, p[0], p[1])
                for i, p in enumerate(pts) if p is not None)
            if len(pts) == 2 and None not in pts:
                info += ", distance %.2f mm" % ac.distance(pts[0], pts[1])
            off = al.get("offset_mm", [0, 0])
            if off[0] or off[1]:
                info += "\nMachine offset: X %g, Y %g mm (added to DSL)" % (
                    off[0], off[1])
        else:
            info += "\nNo alignment points (set them in Plywood Scan)"
        self.lb_file.config(text=info)
        self.lb_result.config(text="")
        self.lb_unplaced.config(text="")
        self.txt.delete("1.0", "end")
        self.redraw(fit=True)

    def alignment(self):
        return (self.meta or {}).get("alignment") or {}

    def offset(self):
        off = self.alignment().get("offset_mm", [0.0, 0.0])
        return float(off[0]), float(off[1])

    def _num(self, var, name):
        try:
            return float(var.get() or 0)
        except ValueError:
            raise ValueError("%s must be a number" % name)

    def run(self):
        if self.mask is None:
            messagebox.showwarning("No mask", "Open a mask file first.")
            return
        try:
            w = self._num(self.v_w, "Strip width")
            gap = self._num(self.v_gap, "Gap")
            if w <= 0 or gap < 0:
                raise ValueError("Strip width must be > 0 and gap >= 0")
            res = self.meta["mm_per_px"]
            self.root.config(cursor="watch")
            self.lb_result.config(text="Computing...", fg="#000")
            self.root.update()
            if self.v_mode.get() == "pieces":
                lengths = parse_lengths(self.v_lengths.get())
                self.result = pack_pieces(self.mask, res, lengths, strip_w=w,
                                          gap=gap, orient=self.v_orient.get())
            else:
                self.result = pack_strips(
                    self.mask, res, strip_w=w,
                    min_len=self._num(self.v_min, "Min length"),
                    max_len=self._num(self.v_max, "Max length"),
                    step=self._num(self.v_step, "Length step"), gap=gap,
                    orient=self.v_orient.get(), objective=self.v_obj.get())
                self.result["unplaced"] = []
                self.result["requested"] = None
        except Exception as ex:
            self.lb_result.config(text="")
            messagebox.showerror("Error", str(ex))
            return
        finally:
            self.root.config(cursor="")
        r = self.result
        errs = verify_strips(self.mask, res, r["strips"], gap)
        nh = sum(1 for s in r["strips"] if s["orient"] == "H")
        if r["requested"] is not None:
            head = "Placed %d / %d pieces" % (r["count"], r["requested"])
        else:
            head = "Auto-fill: %d strips" % r["count"]
        txt = ("%s (horizontal %d, vertical %d)\nTotal length: %.1f mm\n"
               "Strategy: %s\nCheck: %s" % (
                   head, nh, r["count"] - nh, r["total_length"], r["strategy"],
                   "OK" if not errs else "%d ERRORS: %s" % (len(errs), errs[0])))
        self.lb_result.config(text=txt, fg="#000" if not errs else "red")
        if r["unplaced"]:
            self.lb_unplaced.config(
                text="Did not fit (%d): %s" % (len(r["unplaced"]), ", ".join(
                    "#%d (%g mm)" % (u["id"], u["length"])
                    for u in r["unplaced"])))
        elif r["requested"] is not None:
            self.lb_unplaced.config(text="All pieces placed.", fg="#007000")
        else:
            self.lb_unplaced.config(text="")
        if r["unplaced"]:
            self.lb_unplaced.config(fg="#c00000")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "\n".join(self.dsl_lines()))
        self.redraw()

    def dsl_lines(self):
        if not self.result:
            return []
        r = self.result
        p = r["params"]
        head = ["# strip_packer: %d strips, total %.1f mm, width %g mm, "
                "gap %g mm, source: %s" % (r["count"], r["total_length"],
                                           p["strip_w"], p["gap"],
                                           os.path.basename(self.path)),
                "# origin (0,0) = bottom-left corner of the sheet, y up; "
                "each piece: ADD x y <number> / R 0 0 w h / END"]
        ox, oy = self.offset()
        if ox or oy:
            head.append("# machine offset X %g Y %g mm added to ADD x y "
                        "(same as alignment gcode)" % (ox, oy))
        if r.get("unplaced"):
            head.append("# did not fit: " + ", ".join(
                "#%d (%g mm)" % (u["id"], u["length"]) for u in r["unplaced"]))
        return head + strips_to_dsl(r["strips"], offset=self.offset())

    def render(self):
        if self.mask is None:
            return None
        strips = self.result["strips"] if self.result else []
        bg = self.warped if self.v_show_photo.get() else None
        al = self.alignment()
        return render_result(bg, self.mask, self.meta["mm_per_px"], strips,
                             scale=2, labels=self.v_labels.get(),
                             align_points=al.get("points_mm"),
                             cross_mm=al.get("cross_mm", 5.0))

    def redraw(self, fit=False):
        self.view.set_image(self.render(), fit=fit)

    def export_txt(self):
        if not self.result:
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                         initialfile="strips_dsl.txt",
                                         filetypes=[("Text", "*.txt")])
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n".join(self.dsl_lines()) + "\n")

    def copy_dsl(self):
        if self.result:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(self.dsl_lines()))

    def export_png(self):
        img = self.render()
        if img is None:
            return
        p = filedialog.asksaveasfilename(defaultextension=".png",
                                         initialfile="strips_result.png",
                                         filetypes=[("PNG", "*.png")])
        if p:
            imwrite_unicode(p, img)


def main():
    ui_util.enable_dpi_awareness()      # phai goi truoc khi tao Tk
    root = tk.Tk()
    ui_util.init_scaling(root)
    root.title("Strip Packer - cut strips from leftover plywood")
    ui_util.fit_geometry(root, 1300, 880)
    app = StripPackerApp(root, sys.argv[1] if len(sys.argv) > 1 else None)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
