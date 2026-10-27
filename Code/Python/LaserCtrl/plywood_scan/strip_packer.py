"""
Tool 2: Tinh cach cat cac thanh chu nhat (vd rong 10mm, dai 30-100mm) tu
vung go con lai (mask do scan_app tao ra), xuat lenh DSL "R x y w h".

Chay:  python strip_packer.py  [file_mask.json|png]

Dung nhu thu vien:
    from strip_packer import pack_strips, load_mask_file
    mask, meta, _ = load_mask_file("tam1_mask.json")
    res = pack_strips(mask, meta["mm_per_px"], strip_w=10, min_len=30,
                      max_len=100, gap=0.5)
    print(res["count"], res["total_length"])

Toa do DSL: goc (0, 0) = goc DUOI-TRAI cua tam (goc so 4 khi chon goc trong
scan_app), x sang phai, y huong LEN, don vi mm.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


from pack_core import (pack_strips, verify_strips, strips_to_dsl,  # noqa
                       render_result)
from scan_core import load_mask_file, imread_unicode, imwrite_unicode  # noqa
import ui_util
from ui_util import px
from image_view import ImageView

FONT = ("Times New Roman", 11)
FONT_B = ("Times New Roman", 11, "bold")


class StripPackerApp(ttk.Frame):

    def __init__(self, parent, path=None):
        super().__init__(parent)
        self.root = parent
        self.mask = None
        self.meta = None
        self.warped = None
        self.path = ""
        self.result = None

        self.v_w = tk.StringVar(value="10")
        self.v_min = tk.StringVar(value="30")
        self.v_max = tk.StringVar(value="100")
        self.v_step = tk.StringVar(value="0")
        self.v_gap = tk.StringVar(value="0.5")
        self.v_orient = tk.StringVar(value="both")
        self.v_obj = tk.StringVar(value="length")
        self.v_show_photo = tk.BooleanVar(value=True)
        self.build_gui()
        if path:
            self.root.after(100, lambda: self.load(path))

    def build_gui(self):
        left = tk.Frame(self, width=px(360))
        left.pack(side="left", fill="y", padx=5, pady=5)
        left.pack_propagate(False)

        tk.Button(left, text="Open mask (.json / .png)...", font=FONT,
                  command=self.ask_load).pack(fill="x", pady=2)
        self.lb_file = tk.Label(left, text="No mask loaded", font=FONT,
                                justify="left", wraplength=px(340), anchor="w")
        self.lb_file.pack(fill="x", pady=2)
        ttk.Separator(left).pack(fill="x", pady=4)

        def row(label, var, unit):
            r = tk.Frame(left)
            r.pack(fill="x", pady=1)
            tk.Label(r, text=label, font=FONT, width=20,
                     anchor="w").pack(side="left")
            tk.Entry(r, textvariable=var, width=8, font=FONT).pack(side="left")
            tk.Label(r, text=unit, font=FONT).pack(side="left")

        row("Strip width", self.v_w, "mm")
        row("Min length", self.v_min, "mm")
        row("Max length", self.v_max, "mm")
        row("Length step (0=free)", self.v_step, "mm")
        row("Gap / kerf", self.v_gap, "mm")

        tk.Label(left, text="Orientation:", font=FONT_B,
                 anchor="w").pack(fill="x", pady=(6, 0))
        r = tk.Frame(left)
        r.pack(fill="x")
        for v, t in (("both", "Both"), ("H", "Horizontal (X)"),
                     ("V", "Vertical (Y)")):
            tk.Radiobutton(r, text=t, value=v, variable=self.v_orient,
                           font=FONT).pack(side="left")
        tk.Label(left, text="Objective:", font=FONT_B,
                 anchor="w").pack(fill="x", pady=(6, 0))
        r = tk.Frame(left)
        r.pack(fill="x")
        for v, t in (("length", "Max total length"),
                     ("count", "Max count")):
            tk.Radiobutton(r, text=t, value=v, variable=self.v_obj,
                           font=FONT).pack(side="left")

        tk.Button(left, text="Compute", font=FONT_B,
                  command=self.run).pack(fill="x", pady=6)
        tk.Checkbutton(left, text="Show photo as background",
                       variable=self.v_show_photo, font=FONT,
                       command=self.redraw).pack(anchor="w")
        self.lb_result = tk.Label(left, text="", font=FONT, justify="left",
                                  wraplength=px(340), anchor="w")
        self.lb_result.pack(fill="x", pady=2)

        r = tk.Frame(left)
        r.pack(fill="x", pady=2)
        tk.Button(r, text="Export DSL (.txt)", font=FONT,
                  command=self.export_txt).pack(side="left", expand=True,
                                                fill="x")
        tk.Button(r, text="Copy DSL", font=FONT,
                  command=self.copy_dsl).pack(side="left", expand=True,
                                              fill="x")
        tk.Button(left, text="Save result image (.png)", font=FONT,
                  command=self.export_png).pack(fill="x", pady=2)

        self.txt = tk.Text(left, height=12, font=("Courier", 9))
        self.txt.pack(fill="both", expand=True, pady=2)
        tk.Label(left, font=("Arial", 9), fg="#444", justify="left",
                 wraplength=px(340), anchor="w",
                 text="DSL coordinates: origin (0,0) = BOTTOM-LEFT corner of "
                      "the sheet (corner 4 when picking corners), x to the "
                      "right, y up, in mm. Paste into the Designer tab to "
                      "preview / generate gcode. Place the sheet on the "
                      "machine with the same corner and orientation."
                 ).pack(fill="x")

        right = tk.Frame(self)
        right.pack(side="right", fill="both", expand=True)
        self.view = ImageView(right, width=px(850), height=px(750))
        self.view.pack(fill="both", expand=True)
        tk.Label(right, font=("Arial", 9), fg="#555",
                 text="Green = horizontal strip, blue = vertical strip, "
                      "red = cut | wheel: zoom | right drag: pan"
                 ).pack(fill="x")

    # ------------------------------------------------------------------
    def ask_load(self):
        p = filedialog.askopenfilename(
            title="Open mask", filetypes=[("Mask", "*.json *.png"),
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
        self.lb_file.config(text="%s\n%g x %g mm, %.4f mm/px, margin %g mm" % (
            os.path.basename(path), meta["width_mm"], meta["height_mm"],
            meta["mm_per_px"], meta.get("margin_mm", 0)))
        self.lb_result.config(text="")
        self.txt.delete("1.0", "end")
        self.redraw(fit=True)

    def params(self):
        try:
            return dict(strip_w=float(self.v_w.get()),
                        min_len=float(self.v_min.get()),
                        max_len=float(self.v_max.get()),
                        step=float(self.v_step.get() or 0),
                        gap=float(self.v_gap.get() or 0),
                        orient=self.v_orient.get(),
                        objective=self.v_obj.get())
        except ValueError:
            raise ValueError("Parameters must be numbers")

    def run(self):
        if self.mask is None:
            messagebox.showwarning("No mask", "Open a mask file first.")
            return
        try:
            p = self.params()
            self.root.config(cursor="watch")
            self.root.update()
            self.result = pack_strips(self.mask, self.meta["mm_per_px"], **p)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            return
        finally:
            self.root.config(cursor="")
        errs = verify_strips(self.mask, self.meta["mm_per_px"],
                             self.result["strips"], p["gap"])
        r = self.result
        nh = sum(1 for s in r["strips"] if s["orient"] == "H")
        txt = ("Strips: %d (horizontal %d, vertical %d)\nTotal length: %.1f mm\n"
               "Strategy: %s\nCheck: %s" % (
                   r["count"], nh, r["count"] - nh, r["total_length"],
                   r["strategy"], "OK" if not errs else
                   "%d ERRORS: %s" % (len(errs), errs[0])))
        self.lb_result.config(text=txt, fg="#000" if not errs else "red")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "\n".join(self.dsl_lines()))
        self.redraw()

    def dsl_lines(self):
        if not self.result:
            return []
        r = self.result
        p = r["params"]
        head = ["# strip_packer: %d strips, total %.1f mm" % (
                    r["count"], r["total_length"]),
                "# width %g mm, length %g-%g mm, gap %g mm, source: %s" % (
                    p["strip_w"], p["min_len"], p["max_len"], p["gap"],
                    os.path.basename(self.path)),
                "# origin (0,0) = bottom-left corner of the sheet, y up"]
        return head + strips_to_dsl(r["strips"])

    def render(self):
        if self.mask is None:
            return None
        strips = self.result["strips"] if self.result else []
        bg = self.warped if self.v_show_photo.get() else None
        return render_result(bg, self.mask, self.meta["mm_per_px"], strips,
                             scale=2)

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
            self.root.clipboard_append(
                "\n".join(strips_to_dsl(self.result["strips"])))

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
    ui_util.fit_geometry(root, 1250, 850)
    app = StripPackerApp(root, sys.argv[1] if len(sys.argv) > 1 else None)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
