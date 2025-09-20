import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import math
import os
import uuid
import subprocess

# ==== Cấu hình chuyển đổi đơn vị ====
# 1 inch = 25.4 mm, 96 px/inch => px/mm
PX_PER_MM = 96.0 / 25.4

# Độ dày nét khi xuất SVG (mm)
SVG_STROKE_MM = 0.1

class SVGCutterApp:
    def __init__(self, master):
        self.master = master
        master.title("SVG Laser Cutter Editor")
        master.geometry("1000x700")

        # Danh sách shape: mỗi phần tử {'type': 'line|circle|polygon', 'properties': {...}}
        # MỌI TỌA ĐỘ & KÍCH THƯỚC ĐỀU TÍNH THEO mm (x tăng sang phải, y tăng LÊN trên)
        self.shapes = []

        self._create_widgets()
        self.redraw_canvas()

    # ---------- Helpers: hệ tọa độ & vẽ preview ----------
    def _canvas_origin(self):
        """Trả về (ox, oy) là vị trí gốc (0,0) trên canvas (pixel)."""
        gap = 30  # chừa mép hiển thị
        cw = max(self.canvas.winfo_width(), 1)
        ch = max(self.canvas.winfo_height(), 1)
        return gap, ch - gap  # sát góc dưới-trái

    def mm_to_px(self, mm):
        return mm * PX_PER_MM

    def to_canvas_xy(self, x_mm, y_mm):
        """Chuyển (x,y) mm (y hướng lên) -> (X,Y) px (y hướng xuống) để vẽ trên Tkinter."""
        ox, oy = self._canvas_origin()
        X = ox + self.mm_to_px(x_mm)
        Y = oy - self.mm_to_px(y_mm)
        return X, Y

    def redraw_canvas(self, event=None):
        """Vẽ lại toàn bộ preview theo hệ trục mới."""
        self.canvas.delete("all")
        cw = max(self.canvas.winfo_width(), 1)
        ch = max(self.canvas.winfo_height(), 1)
        ox, oy = self._canvas_origin()

        # Khung viền
        self.canvas.create_rectangle(10, 10, cw - 10, ch - 10, outline="#ccc")

        # Vẽ trục tọa độ
        self.canvas.create_line(ox, 10, ox, ch - 10, fill="#666", width=2)     # trục y
        self.canvas.create_line(10, oy, cw - 10, oy, fill="#666", width=2)     # trục x
        self.canvas.create_text(ox + 12, oy - 12, text="(0,0)", fill="#333", anchor="sw")

        # Vẽ lưới theo mm (nhẹ: 1mm, trung: 10mm, đậm: 50mm)
        # Tính phạm vi lưới có thể hiển thị về mm
        max_x_mm = (cw - (ox + 10)) / PX_PER_MM  # bên phải từ gốc
        max_y_mm = (oy - 10) / PX_PER_MM         # bên trên từ gốc

        # Dọc (các đường x = const)
        step_mm = 1
        x_mm = 0
        while x_mm <= max_x_mm:
            X, _ = self.to_canvas_xy(x_mm, 0)
            if x_mm % 50 == 0:
                w = 2; color = "#000"
            elif x_mm % 10 == 0:
                w = 1; color = "#444"
            else:
                w = 1; color = "#e6e6e6"
            self.canvas.create_line(X, 10, X, ch - 10, fill=color, width=w)
            x_mm += step_mm

        # Ngang (các đường y = const)
        y_mm = 0
        while y_mm <= max_y_mm:
            _, Y = self.to_canvas_xy(0, y_mm)
            if y_mm % 50 == 0:
                w = 2; color = "#000"
            elif y_mm % 10 == 0:
                w = 1; color = "#444"
            else:
                w = 1; color = "#e6e6e6"
            self.canvas.create_line(10, Y, cw - 10, Y, fill=color, width=w)
            y_mm += step_mm

        # Vẽ các shape (dùng mm -> px)
        for shape_data in self.shapes:
            t = shape_data['type']
            p = shape_data['properties']
            if t == "line":
                X1, Y1 = self.to_canvas_xy(p['x1'], p['y1'])
                X2, Y2 = self.to_canvas_xy(p['x2'], p['y2'])
                self.canvas.create_line(X1, Y1, X2, Y2, fill="black", width=4)
            elif t == "circle":
                cx, cy, r = p['cx'], p['cy'], p['r']
                rpx = self.mm_to_px(r)
                Cx, Cy = self.to_canvas_xy(cx, cy)
                self.canvas.create_oval(Cx - rpx, Cy - rpx, Cx + rpx, Cy + rpx, outline="black", width=2)
            elif t == "polygon":
                pts = []
                for x, y in p['points']:
                    X, Y = self.to_canvas_xy(x, y)
                    pts.extend([X, Y])
                self.canvas.create_polygon(pts, outline="black", fill="", width=2)

    # ---------- UI ----------
    def _create_widgets(self):
        control_frame = ttk.Frame(self.master, padding="10", relief=tk.RAISED, borderwidth=1)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control_frame, text="Shapes (mm)", font=("Inter", 12, "bold")).pack(pady=5)

        self.shape_listbox = tk.Listbox(control_frame, height=20, width=40, font=("Inter", 10), selectmode=tk.SINGLE)
        self.shape_listbox.pack(pady=5, fill=tk.BOTH, expand=True)
        self.shape_listbox.bind("<<ListboxSelect>>", self._on_shape_select)

        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=10, fill=tk.X)
        ttk.Button(button_frame, text="Add Shape", command=self._add_shape_dialog).pack(side=tk.LEFT, expand=True, padx=2, ipadx=5, ipady=5)
        ttk.Button(button_frame, text="Edit Shape", command=self._edit_selected_shape).pack(side=tk.LEFT, expand=True, padx=2, ipadx=5, ipady=5)
        ttk.Button(button_frame, text="Remove Shape", command=self._remove_selected_shape).pack(side=tk.LEFT, expand=True, padx=2, ipadx=5)

        ttk.Button(control_frame, text="Save SVG", command=self._save_svg).pack(pady=10, fill=tk.X, ipadx=5, ipady=5)
        ttk.Button(control_frame, text="Run LaserGRBL", command=self._run_laser_grbl).pack(pady=10, fill=tk.X, ipadx=5, ipady=5)  # 👈 thêm nút

        canvas_frame = ttk.Frame(self.master, padding="10", relief=tk.SUNKEN, borderwidth=1)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="white", relief=tk.GROOVE, borderwidth=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.redraw_canvas)
        self.master.bind("<Return>", lambda e: self._add_shape_dialog())


    def _on_shape_select(self, event):
        pass

    # ---------- Add / Edit ----------
    def _add_shape_dialog(self):
        dialog = tk.Toplevel(self.master)
        dialog.title("Add Shape")
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.focus_force()

        shape_type_var = tk.StringVar(value="line")

        ttk.Radiobutton(dialog, text="Line", variable=shape_type_var, value="line",
                        command=lambda: self._show_shape_inputs(dialog, shape_type_var.get())).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Radiobutton(dialog, text="Circle", variable=shape_type_var, value="circle",
                        command=lambda: self._show_shape_inputs(dialog, shape_type_var.get())).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Radiobutton(dialog, text="Polygon", variable=shape_type_var, value="polygon",
                        command=lambda: self._show_shape_inputs(dialog, shape_type_var.get())).pack(anchor=tk.W, padx=10, pady=5)

        input_frame = ttk.Frame(dialog)
        input_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        dialog.input_frame = input_frame

        self._show_shape_inputs(dialog, "line")

        def add_shape_action():
            try:
                shape_type = shape_type_var.get()
                shape_data = {"type": shape_type}
                shape_name = ""

                if shape_type == "line":
                    x1 = float(dialog.entries["x1"].get())
                    y1 = float(dialog.entries["y1"].get())
                    x2 = float(dialog.entries["x2"].get())
                    y2 = float(dialog.entries["y2"].get())
                    shape_data.update({"properties": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}})
                    shape_name = f"Line ({x1},{y1})-({x2},{y2})"
                elif shape_type == "circle":
                    cx = float(dialog.entries["cx"].get())
                    cy = float(dialog.entries["cy"].get())
                    r = float(dialog.entries["r"].get())
                    if r <= 0:
                        raise ValueError("Radius must be greater than 0.")
                    shape_data.update({"properties": {"cx": cx, "cy": cy, "r": r}})
                    shape_name = f"Circle ({cx},{cy}) R={r}"
                elif shape_type == "polygon":
                    points_str = dialog.entries["points"].get()
                    parts = points_str.split(',')
                    if len(parts) % 2 != 0 or len(parts) < 6:
                        raise ValueError("Polygon points must be x,y,... and >= 3 points.")
                    pts = []
                    for i in range(0, len(parts), 2):
                        pts.append((float(parts[i]), float(parts[i+1])))
                    shape_data.update({"properties": {"points": pts}})
                    shape_name = f"Polygon with {len(pts)} points"

                self.shapes.append(shape_data)
                self.shape_listbox.insert(tk.END, shape_name)
                self.redraw_canvas()
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid input: {e}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=dialog)

        dialog.bind("<Return>", lambda e: add_shape_action())

        ttk.Button(dialog, text="Add", command=add_shape_action).pack(pady=10, ipadx=5, ipady=5)
        self.master.wait_window(dialog)

    def _show_shape_inputs(self, dialog, shape_type):
        for w in dialog.input_frame.winfo_children():
            w.destroy()
        dialog.entries = {}

        if shape_type == "line":
            ttk.Label(dialog.input_frame, text="Point 1 (x, y) [mm]:").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["x1"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["x1"].grid(row=0, column=1, padx=5, pady=2)
            dialog.entries["y1"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["y1"].grid(row=0, column=2, padx=5, pady=2)
            ttk.Label(dialog.input_frame, text="Point 2 (x, y) [mm]:").grid(row=1, column=0, sticky=tk.W, pady=2)
            dialog.entries["x2"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["x2"].grid(row=1, column=1, padx=5, pady=2)
            dialog.entries["y2"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["y2"].grid(row=1, column=2, padx=5, pady=2)
            dialog.entries["x1"].focus_set()
        elif shape_type == "circle":
            ttk.Label(dialog.input_frame, text="Center (cx, cy) [mm]:").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["cx"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["cx"].grid(row=0, column=1, padx=5, pady=2)
            dialog.entries["cy"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["cy"].grid(row=0, column=2, padx=5, pady=2)
            ttk.Label(dialog.input_frame, text="Radius (r) [mm]:").grid(row=1, column=0, sticky=tk.W, pady=2)
            dialog.entries["r"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["r"].grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky=tk.EW)
        elif shape_type == "polygon":
            ttk.Label(dialog.input_frame, text="Points (x1,y1,x2,y2,...) [mm]:").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["points"] = ttk.Entry(dialog.input_frame, width=50); dialog.entries["points"].grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky=tk.EW)

    def _edit_selected_shape(self):
        sel = self.shape_listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a shape to edit.")
            return
        index = sel[0]
        sd = self.shapes[index]

        dialog = tk.Toplevel(self.master)
        dialog.title(f"Edit {sd['type'].capitalize()}")
        dialog.transient(self.master)
        dialog.grab_set()

        input_frame = ttk.Frame(dialog)
        input_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        dialog.entries = {}

        p = sd["properties"]
        if sd["type"] == "line":
            ttk.Label(input_frame, text="Point 1 (x, y) [mm]:").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["x1"] = ttk.Entry(input_frame, width=15); dialog.entries["x1"].grid(row=0, column=1, padx=5, pady=2); dialog.entries["x1"].insert(0, str(p["x1"]))
            dialog.entries["y1"] = ttk.Entry(input_frame, width=15); dialog.entries["y1"].grid(row=0, column=2, padx=5, pady=2); dialog.entries["y1"].insert(0, str(p["y1"]))
            ttk.Label(input_frame, text="Point 2 (x, y) [mm]:").grid(row=1, column=0, sticky=tk.W, pady=2)
            dialog.entries["x2"] = ttk.Entry(input_frame, width=15); dialog.entries["x2"].grid(row=1, column=1, padx=5, pady=2); dialog.entries["x2"].insert(0, str(p["x2"]))
            dialog.entries["y2"] = ttk.Entry(input_frame, width=15); dialog.entries["y2"].grid(row=1, column=2, padx=5, pady=2); dialog.entries["y2"].insert(0, str(p["y2"]))
        elif sd["type"] == "circle":
            ttk.Label(input_frame, text="Center (cx, cy) [mm]:").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["cx"] = ttk.Entry(input_frame, width=15); dialog.entries["cx"].grid(row=0, column=1, padx=5, pady=2); dialog.entries["cx"].insert(0, str(p["cx"]))
            dialog.entries["cy"] = ttk.Entry(input_frame, width=15); dialog.entries["cy"].grid(row=0, column=2, padx=5, pady=2); dialog.entries["cy"].insert(0, str(p["cy"]))
            ttk.Label(input_frame, text="Radius (r) [mm]:").grid(row=1, column=0, sticky=tk.W, pady=2)
            dialog.entries["r"] = ttk.Entry(input_frame, width=15); dialog.entries["r"].grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky=tk.EW); dialog.entries["r"].insert(0, str(p["r"]))
        elif sd["type"] == "polygon":
            ttk.Label(input_frame, text="Points (x1,y1,x2,y2,...) [mm]:").grid(row=0, column=0, sticky=tk.W, pady=2)
            points_str = ",".join(f"{x},{y}" for x, y in p["points"])
            dialog.entries["points"] = ttk.Entry(input_frame, width=50); dialog.entries["points"].grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky=tk.EW); dialog.entries["points"].insert(0, points_str)

        def update_shape_action():
            try:
                new_props = {}
                name = ""
                if sd["type"] == "line":
                    x1 = float(dialog.entries["x1"].get())
                    y1 = float(dialog.entries["y1"].get())
                    x2 = float(dialog.entries["x2"].get())
                    y2 = float(dialog.entries["y2"].get())
                    new_props = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                    name = f"Line ({x1},{y1})-({x2},{y2})"
                elif sd["type"] == "circle":
                    cx = float(dialog.entries["cx"].get())
                    cy = float(dialog.entries["cy"].get())
                    r = float(dialog.entries["r"].get())
                    if r <= 0:
                        raise ValueError("Radius must be greater than 0.")
                    new_props = {"cx": cx, "cy": cy, "r": r}
                    name = f"Circle ({cx},{cy}) R={r}"
                elif sd["type"] == "polygon":
                    parts = dialog.entries["points"].get().split(',')
                    if len(parts) % 2 != 0 or len(parts) < 6:
                        raise ValueError("Polygon points must be x,y,... and >= 3 points.")
                    pts = []
                    for i in range(0, len(parts), 2):
                        pts.append((float(parts[i]), float(parts[i+1])))
                    new_props = {"points": pts}
                    name = f"Polygon with {len(pts)} points"

                self.shapes[index]["properties"] = new_props
                self.shape_listbox.delete(index)
                self.shape_listbox.insert(index, name)
                self.redraw_canvas()
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid input: {e}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=dialog)

        ttk.Button(dialog, text="Update", command=update_shape_action).pack(pady=10, ipadx=5, ipady=5)
        self.master.wait_window(dialog)

    def _remove_selected_shape(self):
        sel = self.shape_listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a shape to remove.")
            return
        if messagebox.askyesno("Confirm Removal", "Are you sure you want to remove the selected shape?"):
            idx = sel[0]
            self.shapes.pop(idx)
            self.shape_listbox.delete(idx)
            self.redraw_canvas()

    # ---------- SVG export ----------
    def _compute_bounds_mm(self):
        """Tính bounding box (minx, miny, maxx, maxy) tính theo mm của toàn bộ shapes."""
        if not self.shapes:
            return None
        minx = miny = float("inf")
        maxx = maxy = float("-inf")

        for s in self.shapes:
            t = s['type']
            p = s['properties']
            if t == "line":
                xs = [p['x1'], p['x2']]
                ys = [p['y1'], p['y2']]
            elif t == "circle":
                xs = [p['cx'] - p['r'], p['cx'] + p['r']]
                ys = [p['cy'] - p['r'], p['cy'] + p['r']]
            elif t == "polygon":
                xs = [pt[0] for pt in p['points']]
                ys = [pt[1] for pt in p['points']]
            else:
                continue

            minx = min(minx, *xs); maxx = max(maxx, *xs)
            miny = min(miny, *ys); maxy = max(maxy, *ys)

        # Tính thêm nửa bề rộng nét để không bị cắt mất nét
        pad = SVG_STROKE_MM / 2.0
        return (minx - pad, miny - pad, maxx + pad, maxy + pad)

    def _save_svg(self):
        """Xuất SVG: đơn vị mm, gói gọn bounding box, y hướng LÊN."""
        if not self.shapes:
            messagebox.showwarning("Empty", "No shapes to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")],
            title="Save SVG As"
        )
        if not file_path:
            return

        try:
            bounds = self._compute_bounds_mm()
            if bounds is None:
                messagebox.showwarning("Empty", "No shapes to export.")
                return
            minx, miny, maxx, maxy = bounds
            width = max(0.0, maxx - minx)
            height = max(0.0, maxy - miny)

            if width == 0 or height == 0:
                messagebox.showwarning("Zero Size", "Bounding box is zero size.")
                return

            # Header: width/height theo mm và viewBox theo cùng trị số => 1 unit = 1 mm
            svg = []
            svg.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
            svg.append(
                f'<svg width="{width:.4f}mm" height="{height:.4f}mm" '
                f'viewBox="0 0 {width:.4f} {height:.4f}" '
                f'xmlns="http://www.w3.org/2000/svg" '
                f'version="1.1">'
            )

            # Dùng nhóm lật trục y để tọa độ y dương hướng lên (gốc tại bottom-left của viewBox)
            # Thứ tự áp dụng: translate(-minx,-miny) -> scale(1,-1) -> translate(0,height)
            svg.append(f'  <g transform="translate(0,{height:.6f}) scale(1,-1) translate({-minx:.6f},{-miny:.6f})">')

            # Xuất các shapes (đơn vị mm, không fill)
            if SVG_STROKE_MM <= 0:
                stroke_attr = ''
            else:
                stroke_attr = f' stroke="black" stroke-width="{SVG_STROKE_MM:.4f}" fill="none"'

            for s in self.shapes:
                t = s['type']; p = s['properties']
                if t == "line":
                    svg.append(
                        f'    <line x1="{p["x1"]:.6f}" y1="{p["y1"]:.6f}" '
                        f'x2="{p["x2"]:.6f}" y2="{p["y2"]:.6f}"{stroke_attr} />'
                    )
                elif t == "circle":
                    svg.append(
                        f'    <circle cx="{p["cx"]:.6f}" cy="{p["cy"]:.6f}" r="{p["r"]:.6f}"{stroke_attr} />'
                    )
                elif t == "polygon":
                    pts = " ".join(f'{x:.6f},{y:.6f}' for x, y in p['points'])
                    svg.append(f'    <polygon points="{pts}"{stroke_attr} />')

            svg.append("  </g>")
            svg.append("</svg>")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(svg))

            messagebox.showinfo("Save SVG", f"SVG saved successfully to {file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save SVG: {e}")

    def _save_svg_to_path(self, file_path):
        """Lưu SVG ra file_path, tái sử dụng logic từ _save_svg."""
        bounds = self._compute_bounds_mm()
        if bounds is None:
            raise RuntimeError("No shapes to export.")
        minx, miny, maxx, maxy = bounds
        width = max(0.0, maxx - minx)
        height = max(0.0, maxy - miny)
        if width == 0 or height == 0:
            raise RuntimeError("Bounding box is zero size.")

        svg = []
        svg.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
        svg.append(
            f'<svg width="{width:.4f}mm" height="{height:.4f}mm" '
            f'viewBox="0 0 {width:.4f} {height:.4f}" '
            f'xmlns="http://www.w3.org/2000/svg" version="1.1">'
        )
        svg.append(f'  <g transform="translate(0,{height:.6f}) scale(1,-1) translate({-minx:.6f},{-miny:.6f})">')

        stroke_attr = f' stroke="black" stroke-width="{SVG_STROKE_MM:.4f}" fill="none"' if SVG_STROKE_MM > 0 else ""

        for s in self.shapes:
            t = s['type']; p = s['properties']
            if t == "line":
                svg.append(
                    f'    <line x1="{p["x1"]:.6f}" y1="{p["y1"]:.6f}" '
                    f'x2="{p["x2"]:.6f}" y2="{p["y2"]:.6f}"{stroke_attr} />'
                )
            elif t == "circle":
                svg.append(
                    f'    <circle cx="{p["cx"]:.6f}" cy="{p["cy"]:.6f}" r="{p["r"]:.6f}"{stroke_attr} />'
                )
            elif t == "polygon":
                pts = " ".join(f'{x:.6f},{y:.6f}' for x, y in p['points'])
                svg.append(f'    <polygon points="{pts}"{stroke_attr} />')

        svg.append("  </g>")
        svg.append("</svg>")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(svg))

    def _run_laser_grbl(self):
        """Lưu file svg tạm và mở bằng LaserGRBL.exe."""
        if not self.shapes:
            messagebox.showwarning("Empty", "No shapes to export.")
            return

        # Chọn folder xuất
        folder = filedialog.askdirectory(title="Select folder to save temporary SVG")
        if not folder:
            return

        # Tạo file ngẫu nhiên
        file_path = os.path.join(folder, f"{uuid.uuid4().hex}.svg")
        try:
            self._save_svg_to_path(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save SVG: {e}")
            return

        # Đường dẫn LaserGRBL
        laser_path = r"C:\Program Files (x86)\LaserGRBL\LaserGRBL.exe"
        if not os.path.exists(laser_path):
            messagebox.showerror("Error", f"LaserGRBL not found at {laser_path}")
            return

        try:
            subprocess.Popen([laser_path, file_path])  # mở file bằng LaserGRBL
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run LaserGRBL: {e}")

# ---------- Main ----------
if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")
    app = SVGCutterApp(root)
    root.mainloop()
