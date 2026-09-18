#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ xếp hình cắt - Xếp dải (CP-SAT)
====================================
Công cụ desktop (Tkinter) sinh DSL cắt (RC / R) từ danh sách mảnh chữ nhật,
tối thiểu chiều rộng cần dùng cho một chiều cao tấm cố định, cho phép xoay 90 độ.

Yêu cầu: pip install ortools

Chạy: python rect_nesting_app.py
"""

import ctypes
import sys


def _enable_dpi_awareness():
    """Bật DPI awareness trên Windows để chữ không bị mờ (font blur) khi
    màn hình chạy tỉ lệ scale > 100%. Không có tác dụng (và không lỗi)
    trên macOS/Linux."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_enable_dpi_awareness()

import math
import os
import threading
import queue
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox

from ortools.sat.python import cp_model

# --------------------------------------------------------------------------
# Theme - Light mode
# --------------------------------------------------------------------------
BG = "#f3f5f7"
PANEL = "#ffffff"
PANEL_ALT = "#eef1f5"
BORDER = "#d7dee5"
BORDER_STRONG = "#b7c2cc"
TEXT = "#1b232c"
TEXT_DIM = "#5b6774"
ACCENT = "#d9590c"
ACCENT_ON = "#ffffff"
ACCENT_2 = "#0f8f83"
DANGER = "#b91c1c"
DANGER_SOFT = "#fdeceb"
SUCCESS = "#15803d"
CANVAS_BG = "#fbfcfd"
GRID_LINE = "#e2e8ee"

PALETTE = ["#d9590c", "#0f8f83", "#7c3aed", "#be185d",
           "#a16207", "#1d4ed8", "#15803d", "#c2410c"]


def pick_font(candidates, size, weight="normal"):
    """Chọn font 'custom' dễ nhìn: dò qua danh sách ưu tiên các font chữ
    rõ, hỗ trợ tốt tiếng Việt có dấu, còn lại rơi về font hệ thống."""
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return tkfont.Font(family=name, size=size, weight=weight)
    return tkfont.Font(size=size, weight=weight)


UI_FONT_CANDIDATES = ["Segoe UI", "Calibri", "Helvetica Neue", "Noto Sans",
                       "Ubuntu", "Arial", "Verdana"]
MONO_FONT_CANDIDATES = ["Cascadia Mono", "Consolas", "Menlo", "Noto Sans Mono",
                         "DejaVu Sans Mono", "Courier New"]

# --------------------------------------------------------------------------
# Packing core (CP-SAT)
# --------------------------------------------------------------------------
SCALE = 2  # đơn vị làm việc = 0.5mm -> số nguyên


def snap(v):
    return round(v * 2) / 2


def fmt_num(v):
    r = snap(v)
    return str(int(r)) if float(r).is_integer() else f"{r:.1f}"


def solve_packing(instances, H, time_limit=20.0):
    """
    instances: list of dict {id, name, w, h, rotate}
    H: chiều cao tấm cố định (mm)
    Trả về dict: placements, infeasible, status, W_used
    """
    H_s = round(H * SCALE)

    feasible_items = []
    infeasible = []
    for inst in instances:
        w_s = round(inst["w"] * SCALE)
        h_s = round(inst["h"] * SCALE)
        can_normal = w_s <= H_s
        can_rot = inst["rotate"] and h_s <= H_s
        if not can_normal and not can_rot:
            infeasible.append(inst)
            continue
        feasible_items.append((inst, w_s, h_s, can_normal, can_rot))

    if not feasible_items:
        return {"placements": [], "infeasible": infeasible + [i for i in instances if i not in infeasible],
                "status": "NO_ITEMS", "W_used": 0}

    model = cp_model.CpModel()
    n = len(feasible_items)

    ub_w = sum((max(w_s, h_s) if inst["rotate"] else w_s) for inst, w_s, h_s, _, _ in feasible_items)
    ub_w = max(ub_w, 1)
    total_area = sum(w_s * h_s for _, w_s, h_s, _, _ in feasible_items)
    lb_w = max(1, math.ceil(total_area / H_s))

    x_vars, y_vars, w_vars, h_vars, rot_vars = [], [], [], [], []
    x_intervals, y_intervals = [], []

    for idx, (inst, w_s, h_s, can_normal, can_rot) in enumerate(feasible_items):
        if can_normal and can_rot and w_s != h_s:
            rot = model.NewBoolVar(f"rot_{idx}")
            w_v = model.NewIntVar(0, ub_w, f"w_{idx}")
            h_v = model.NewIntVar(0, H_s, f"h_{idx}")
            model.Add(w_v == w_s).OnlyEnforceIf(rot.Not())
            model.Add(w_v == h_s).OnlyEnforceIf(rot)
            model.Add(h_v == h_s).OnlyEnforceIf(rot.Not())
            model.Add(h_v == w_s).OnlyEnforceIf(rot)
        elif can_normal:
            rot = model.NewConstant(0)
            w_v = model.NewIntVar(w_s, w_s, f"w_{idx}")
            h_v = model.NewIntVar(h_s, h_s, f"h_{idx}")
        else:  # chỉ vừa khi xoay
            rot = model.NewConstant(1)
            w_v = model.NewIntVar(h_s, h_s, f"w_{idx}")
            h_v = model.NewIntVar(w_s, w_s, f"h_{idx}")

        x = model.NewIntVar(0, ub_w, f"x_{idx}")
        y = model.NewIntVar(0, H_s, f"y_{idx}")
        model.Add(y + h_v <= H_s)

        x_end = model.NewIntVar(0, ub_w, f"xend_{idx}")
        model.Add(x_end == x + w_v)
        y_end = model.NewIntVar(0, H_s, f"yend_{idx}")
        model.Add(y_end == y + h_v)

        x_iv = model.NewIntervalVar(x, w_v, x_end, f"xi_{idx}")
        y_iv = model.NewIntervalVar(y, h_v, y_end, f"yi_{idx}")

        x_vars.append(x); y_vars.append(y)
        w_vars.append(w_v); h_vars.append(h_v); rot_vars.append(rot)
        x_intervals.append(x_iv); y_intervals.append(y_iv)

    model.AddNoOverlap2D(x_intervals, y_intervals)

    W = model.NewIntVar(lb_w, ub_w, "W")
    for idx in range(n):
        model.Add(x_vars[idx] + w_vars[idx] <= W)
    model.Minimize(W)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = min(8, max(1, os.cpu_count() or 4))
    status = solver.Solve(model)
    status_name = solver.StatusName(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"placements": [], "infeasible": instances, "status": status_name, "W_used": 0}

    placements = []
    for idx, (inst, w_s, h_s, can_normal, can_rot) in enumerate(feasible_items):
        xv = solver.Value(x_vars[idx]) / SCALE
        yv = solver.Value(y_vars[idx]) / SCALE
        wv = solver.Value(w_vars[idx]) / SCALE
        hv = solver.Value(h_vars[idx]) / SCALE
        rotated = solver.Value(rot_vars[idx]) == 1
        placements.append({
            "id": inst["id"], "name": inst["name"],
            "x": snap(xv), "y": snap(yv), "w": snap(wv), "h": snap(hv),
            "rotated": rotated, "origW": inst["w"], "origH": inst["h"],
            "innerText": inst.get("innerText", ""),
        })

    W_used = snap(solver.Value(W) / SCALE)
    return {"placements": placements, "infeasible": infeasible, "status": status_name, "W_used": W_used}


def pieces_to_dsl(placements, W_used, H):
    lines = [f"# Tam: rong={fmt_num(W_used)} cao={fmt_num(H)} (mm, lam tron 0.5)"]
    for p in placements:
        inner_lines = [l.strip() for l in (p.get("innerText") or "").split("\n") if l.strip()]
        label = f"# {p['name']}" + (" (xoay 90 do)" if p["rotated"] else "")
        lines.append(label)
        if not inner_lines:
            lines.append(f"R {fmt_num(p['x'])} {fmt_num(p['y'])} {fmt_num(p['w'])} {fmt_num(p['h'])}")
            continue
        # RC neo tam: tam khung bao = goc trai-duoi + nua kich thuoc
        cx, cy = p["x"] + p["w"] / 2, p["y"] + p["h"] / 2
        lines.append(f"RC {fmt_num(cx)} {fmt_num(cy)} {fmt_num(p['w'])} {fmt_num(p['h'])}")
        for raw in inner_lines:
            if raw.startswith("#"):
                lines.append(raw)
                continue
            parts = raw.split()
            cmd = parts[0].upper()
            if cmd == "R" and len(parts) >= 5:
                # R: x,y = goc trai-duoi
                lx, ly, lw, lh = (float(v) for v in parts[1:5])
                if not p["rotated"]:
                    nx, ny, nw, nh = p["x"] + lx, p["y"] + ly, lw, lh
                else:
                    nx = p["x"] + (p["origH"] - ly - lh)
                    ny = p["y"] + lx
                    nw, nh = lh, lw
                lines.append(f"R {fmt_num(nx)} {fmt_num(ny)} {fmt_num(nw)} {fmt_num(nh)}")
            elif cmd == "RC" and len(parts) >= 5:
                # RC: x,y = tam -> phep xoay ap dung truc tiep len diem tam
                lcx, lcy, lw, lh = (float(v) for v in parts[1:5])
                if not p["rotated"]:
                    ncx, ncy, nw, nh = p["x"] + lcx, p["y"] + lcy, lw, lh
                else:
                    ncx = p["x"] + (p["origH"] - lcy)
                    ncy = p["y"] + lcx
                    nw, nh = lh, lw
                lines.append(f"RC {fmt_num(ncx)} {fmt_num(ncy)} {fmt_num(nw)} {fmt_num(nh)}")
            elif cmd == "C" and len(parts) >= 4:
                lx, ly, lr = (float(v) for v in parts[1:4])
                if not p["rotated"]:
                    nx, ny = p["x"] + lx, p["y"] + ly
                else:
                    # Xoay quanh goc trai-duoi cua manh (origW x origH),
                    # ban kinh khong doi vi phep xoay bao toan khoang cach.
                    nx = p["x"] + (p["origH"] - ly)
                    ny = p["y"] + lx
                lines.append(f"C {fmt_num(nx)} {fmt_num(ny)} {fmt_num(lr)}")
            else:
                lines.append(f'# CANH BAO: lenh "{cmd}" chua duoc tu dong xoay/dich chuyen - kiem tra tay')
                lines.append(raw)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# UI: một dòng khai báo loại mảnh
# --------------------------------------------------------------------------
class PieceRow:
    _seq = 1

    def __init__(self, parent, app, name="Mảnh", w=100, h=100, qty=1, rotate=True):
        self.app = app
        self.id = PieceRow._seq
        PieceRow._seq += 1
        self.inner_open = False

        self.card = tk.Frame(parent, bg=PANEL_ALT, highlightbackground=BORDER,
                              highlightthickness=1, bd=0)
        self.card.pack(fill="x", pady=4, padx=2)

        row1 = tk.Frame(self.card, bg=PANEL_ALT)
        row1.pack(fill="x", padx=8, pady=(8, 4))

        mono = app.font_mono_sm
        ui = app.font_ui_sm

        def labeled(parent_, text, width):
            col = tk.Frame(parent_, bg=PANEL_ALT)
            tk.Label(col, text=text, bg=PANEL_ALT, fg=TEXT_DIM, font=ui).pack(anchor="w")
            e = tk.Entry(col, width=width, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                         relief="flat", highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT, font=mono)
            e.pack(fill="x")
            return col, e

        col_name, self.e_name = labeled(row1, "Tên", 10)
        col_name.pack(side="left", padx=(0, 6))
        self.e_name.insert(0, name)

        col_w, self.e_w = labeled(row1, "Rộng (mm)", 6)
        col_w.pack(side="left", padx=6)
        self.e_w.insert(0, fmt_num(w))

        col_h, self.e_h = labeled(row1, "Cao (mm)", 6)
        col_h.pack(side="left", padx=6)
        self.e_h.insert(0, fmt_num(h))

        col_qty, self.e_qty = labeled(row1, "SL", 3)
        col_qty.pack(side="left", padx=6)
        self.e_qty.insert(0, str(qty))

        col_rot = tk.Frame(row1, bg=PANEL_ALT)
        col_rot.pack(side="left", padx=6)
        tk.Label(col_rot, text="Xoay", bg=PANEL_ALT, fg=TEXT_DIM, font=ui).pack(anchor="w")
        self.rotate_var = tk.BooleanVar(value=rotate)
        tk.Checkbutton(col_rot, variable=self.rotate_var, bg=PANEL_ALT,
                        activebackground=PANEL_ALT, highlightthickness=0,
                        selectcolor=PANEL).pack(anchor="w")

        rm_btn = tk.Button(row1, text="\u2715", command=self.remove, bg=PANEL_ALT, fg=TEXT_DIM,
                            activebackground=DANGER_SOFT, activeforeground=DANGER,
                            relief="flat", bd=0, font=ui, cursor="hand2")
        rm_btn.pack(side="right", padx=(6, 0), anchor="n")

        row2 = tk.Frame(self.card, bg=PANEL_ALT)
        row2.pack(fill="x", padx=8, pady=(0, 8))
        self.toggle_btn = tk.Button(row2, text="+ Hình bên trong (tùy chọn)",
                                     command=self.toggle_inner, bg=PANEL_ALT, fg=ACCENT_2,
                                     activebackground=PANEL_ALT, activeforeground=ACCENT_2,
                                     relief="flat", bd=0, font=ui, cursor="hand2", anchor="w")
        self.toggle_btn.pack(fill="x")

        self.inner_frame = tk.Frame(self.card, bg=PANEL_ALT)
        self.inner_text = tk.Text(self.inner_frame, height=4, bg=PANEL, fg=TEXT,
                                   insertbackground=TEXT, relief="flat",
                                   highlightthickness=1, highlightbackground=BORDER,
                                   highlightcolor=ACCENT, font=mono, wrap="none")
        self.inner_text.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(self.inner_frame,
                 text="Lệnh hỗ trợ: C x y r (tâm) | R x y w h (góc trái-dưới)\n"
                      "| RC x y w h (tâm). Toạ độ theo hệ trục riêng của mảnh,\n"
                      "gốc (0,0) ở dưới-trái, giới hạn trong Rộng x Cao ở trên.\n"
                      "Khi mảnh bị xoay 90°, các hình bên trong tự xoay theo.",
                 bg=PANEL_ALT, fg=TEXT_DIM, font=app.font_ui_xs, justify="left").pack(
            anchor="w", padx=8, pady=(0, 8))

    def toggle_inner(self):
        self.inner_open = not self.inner_open
        if self.inner_open:
            self.inner_frame.pack(fill="x")
            self.toggle_btn.config(text="- Ẩn hình bên trong")
        else:
            self.inner_frame.pack_forget()
            self.toggle_btn.config(text="+ Hình bên trong (tùy chọn)")

    def remove(self):
        self.card.destroy()
        self.app.piece_rows.remove(self)

    def get_data(self):
        try:
            w = snap(float(self.e_w.get()))
            h = snap(float(self.e_h.get()))
            qty = max(1, int(float(self.e_qty.get())))
        except ValueError:
            return None
        name = self.e_name.get().strip() or "Mảnh"
        return {
            "name": name, "w": w, "h": h, "qty": qty,
            "rotate": self.rotate_var.get(),
            "innerText": self.inner_text.get("1.0", "end").strip(),
        }


# --------------------------------------------------------------------------
# Khung cuộn cho danh sách mảnh
# --------------------------------------------------------------------------
class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg, height=None):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0,
                                 height=height if height else 300)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)

        self.inner.bind("<Configure>",
                         lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._resize_inner)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)   # Windows/Mac
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def _resize_inner(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# --------------------------------------------------------------------------
# Ứng dụng chính
# --------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Bộ xếp hình cắt - Xếp dải (CP-SAT)")
        self.root.configure(bg=BG)
        self.root.geometry("1280x820")
        self.root.minsize(980, 640)

        self.font_ui = pick_font(UI_FONT_CANDIDATES, 12)
        self.font_ui_sm = pick_font(UI_FONT_CANDIDATES, 10)
        self.font_ui_xs = pick_font(UI_FONT_CANDIDATES, 9)
        self.font_ui_bold = pick_font(UI_FONT_CANDIDATES, 13, "bold")
        self.font_mono = pick_font(MONO_FONT_CANDIDATES, 11)
        self.font_mono_sm = pick_font(MONO_FONT_CANDIDATES, 10)
        self.font_h1 = pick_font(UI_FONT_CANDIDATES, 18, "bold")

        self.piece_rows = []
        self.result_queue = queue.Queue()
        self.last_placements = []
        self.last_W = 0
        self.last_H = 0
        self.solving = False

        self._build_ui()
        self._seed_examples()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(300, self.calculate)

    def on_close(self):
        if self.solving:
            if not messagebox.askyesno(
                "Đang tính toán",
                "CP-SAT đang giải. Đóng bây giờ có thể mất kết quả đang tính. Vẫn đóng?"):
                return
        self.root.destroy()

    # ---------------- Dựng giao diện ----------------
    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(header, text="\U0001F4D0 Bộ xếp hình cắt", bg=BG, fg=TEXT,
                  font=self.font_h1).pack(side="left")
        tk.Label(header, text="  Sinh DSL (RC/R) - CP-SAT tối ưu chiều rộng, chiều cao tấm cố định",
                  bg=BG, fg=TEXT_DIM, font=self.font_ui_sm).pack(side="left", padx=(6, 0))

        sep = tk.Frame(self.root, bg=BORDER, height=1)
        sep.pack(fill="x", padx=20, pady=(0, 14))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        left = tk.Frame(body, bg=BG, width=400)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # --- Trái: cấu hình tấm ---
        cfg_panel = self._panel(left, "CẤU HÌNH TẤM CẮT")
        row = tk.Frame(cfg_panel, bg=PANEL)
        row.pack(fill="x")
        self.e_height = self._field(row, "Chiều cao tấm (mm)", "600", width=10)
        self.e_kerf = self._field(row, "Kerf (mm)", "0", width=8, disabled=True)
        self.e_timelimit = self._field(row, "Giới hạn tính (giây)", "15", width=8)

        # --- Trái: danh sách mảnh ---
        list_panel = self._panel(left, "DANH SÁCH MẢNH")
        self.scroll = ScrollableFrame(list_panel, bg=PANEL, height=340)
        self.scroll.pack(fill="both", expand=True)

        list_btns = tk.Frame(list_panel, bg=PANEL)
        list_btns.pack(fill="x", pady=(10, 0))
        add_btn = tk.Button(list_btns, text="+ Thêm mảnh", command=self.add_piece,
                             bg=PANEL, fg=ACCENT_2, activebackground=PANEL,
                             activeforeground=ACCENT_2, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER_STRONG,
                             font=self.font_ui_sm, cursor="hand2", pady=8)
        add_btn.pack(side="left", fill="x", expand=True)
        clear_btn = tk.Button(list_btns, text="Xoá tất cả", command=self.clear_all_pieces,
                               bg=PANEL, fg=DANGER, activebackground=DANGER_SOFT,
                               activeforeground=DANGER, relief="flat",
                               highlightthickness=1, highlightbackground=BORDER_STRONG,
                               font=self.font_ui_sm, cursor="hand2", pady=8)
        clear_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # --- Trái: nút tính toán ---
        calc_panel = tk.Frame(left, bg=BG)
        calc_panel.pack(fill="x", pady=(14, 0))
        self.calc_btn = tk.Button(calc_panel, text="Tính toán", command=self.calculate,
                                   bg=ACCENT, fg=ACCENT_ON, activebackground=ACCENT,
                                   activeforeground=ACCENT_ON, relief="flat",
                                   font=self.font_ui_bold, cursor="hand2", pady=10)
        self.calc_btn.pack(fill="x")
        self.status_lbl = tk.Label(calc_panel, text="", bg=BG, fg=TEXT_DIM, font=self.font_ui_sm)
        self.status_lbl.pack(fill="x", pady=(6, 0))

        # --- Phải: canvas ---
        canvas_panel = self._panel(right, "XEM TRƯỚC")
        cv_wrap = tk.Frame(canvas_panel, bg=CANVAS_BG, highlightbackground=BORDER,
                            highlightthickness=1)
        cv_wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(cv_wrap, bg=CANVAS_BG, highlightthickness=0, height=420)
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

        results = tk.Frame(canvas_panel, bg=PANEL)
        results.pack(fill="x", pady=(12, 0))
        self.stat_width = self._stat(results, "Chiều rộng cần dùng", accent=True)
        self.stat_height = self._stat(results, "Chiều cao tấm")
        self.stat_eff = self._stat(results, "Hiệu suất sử dụng")

        self.warn_lbl = tk.Label(canvas_panel, text="", bg=DANGER_SOFT, fg=DANGER,
                                  font=self.font_ui_sm, justify="left", anchor="w",
                                  wraplength=760)
        # pack khi cần

        # --- Phải: DSL xuất ra ---
        dsl_panel = self._panel(right, "DSL XUẤT RA")
        dsl_head = tk.Frame(dsl_panel, bg=PANEL)
        dsl_head.pack(fill="x")
        tk.Label(dsl_head, text="", bg=PANEL).pack(side="left", expand=True, fill="x")
        self.copy_status = tk.Label(dsl_head, text="Đã copy", bg=PANEL, fg=SUCCESS,
                                     font=self.font_ui_sm)
        copy_btn = tk.Button(dsl_head, text="Copy DSL", command=self.copy_dsl,
                              bg=PANEL_ALT, fg=TEXT, activebackground=PANEL_ALT,
                              relief="flat", highlightthickness=1,
                              highlightbackground=BORDER, font=self.font_ui_sm,
                              cursor="hand2", padx=10, pady=4)
        copy_btn.pack(side="right")
        save_btn = tk.Button(dsl_head, text="Lưu file...", command=self.save_dsl,
                              bg=PANEL_ALT, fg=TEXT, activebackground=PANEL_ALT,
                              relief="flat", highlightthickness=1,
                              highlightbackground=BORDER, font=self.font_ui_sm,
                              cursor="hand2", padx=10, pady=4)
        save_btn.pack(side="right", padx=(0, 8))

        dsl_box = tk.Frame(dsl_panel, bg=PANEL)
        dsl_box.pack(fill="both", expand=True, pady=(8, 0))
        self.dsl_text = tk.Text(dsl_box, bg=PANEL_ALT, fg=TEXT, insertbackground=TEXT,
                                 relief="flat", highlightthickness=1,
                                 highlightbackground=BORDER, font=self.font_mono_sm,
                                 height=14, wrap="none")
        dsl_scroll = tk.Scrollbar(dsl_box, orient="vertical", command=self.dsl_text.yview)
        self.dsl_text.configure(yscrollcommand=dsl_scroll.set)
        self.dsl_text.pack(side="left", fill="both", expand=True)
        dsl_scroll.pack(side="right", fill="y")

    def _panel(self, parent, title):
        panel = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=False, pady=(0, 14))
        inner = tk.Frame(panel, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=14, pady=12)
        tk.Label(inner, text=title, bg=PANEL, fg=TEXT_DIM, font=self.font_ui_sm).pack(
            anchor="w", pady=(0, 10))
        return inner

    def _field(self, parent, label, default, width=10, disabled=False):
        col = tk.Frame(parent, bg=PANEL)
        col.pack(side="left", padx=(0, 10), fill="y")
        tk.Label(col, text=label, bg=PANEL, fg=TEXT_DIM, font=self.font_ui_sm).pack(anchor="w")
        e = tk.Entry(col, width=width, bg=PANEL_ALT, fg=TEXT, insertbackground=TEXT,
                     relief="flat", highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT, font=self.font_mono_sm,
                     state="disabled" if disabled else "normal")
        if disabled:
            e.configure(disabledbackground=PANEL_ALT, disabledforeground=TEXT_DIM)
            e.configure(state="normal")
            e.insert(0, default)
            e.configure(state="disabled")
        else:
            e.insert(0, default)
        e.pack()
        return e

    def _stat(self, parent, label, accent=False):
        box = tk.Frame(parent, bg=PANEL_ALT, highlightbackground=BORDER, highlightthickness=1)
        box.pack(side="left", fill="both", expand=True, padx=4)
        inner = tk.Frame(box, bg=PANEL_ALT)
        inner.pack(padx=10, pady=8, anchor="w")
        tk.Label(inner, text=label, bg=PANEL_ALT, fg=TEXT_DIM, font=self.font_ui_xs).pack(anchor="w")
        val = tk.Label(inner, text="\u2014", bg=PANEL_ALT, fg=ACCENT if accent else TEXT,
                        font=self.font_mono)
        val.pack(anchor="w")
        return val

    # ---------------- Quản lý danh sách mảnh ----------------
    def add_piece(self, name="Mảnh", w=100, h=100, qty=1, rotate=True):
        row = PieceRow(self.scroll.inner, self, name=name, w=w, h=h, qty=qty, rotate=rotate)
        self.piece_rows.append(row)

    def clear_all_pieces(self):
        if not self.piece_rows:
            return
        if not messagebox.askyesno("Xoá tất cả", "Xoá toàn bộ danh sách mảnh?"):
            return
        for row in list(self.piece_rows):
            row.card.destroy()
        self.piece_rows.clear()

    def _seed_examples(self):
        # Giữ danh sách mặc định nhỏ để lần tính đầu tiên (tự chạy khi mở app)
        # không mất nhiều thời gian, tránh trải nghiệm mở app bị "đứng" lâu.
        self.add_piece("A", 200, 100, 2, True)
        self.add_piece("B", 120, 120, 1, False)

    # ---------------- Tính toán ----------------
    def calculate(self):
        try:
            H = snap(float(self.e_height.get()))
        except ValueError:
            messagebox.showerror("Lỗi", "Chiều cao tấm không hợp lệ.")
            return
        try:
            time_limit = max(1.0, float(self.e_timelimit.get()))
        except ValueError:
            time_limit = 15.0

        if H <= 0:
            messagebox.showerror("Lỗi", "Chiều cao tấm phải lớn hơn 0.")
            return

        defs = [r.get_data() for r in self.piece_rows]
        defs = [d for d in defs if d and d["w"] > 0 and d["h"] > 0]
        if not defs:
            messagebox.showwarning("Chưa có mảnh", "Vui lòng thêm ít nhất một mảnh hợp lệ.")
            return

        instances = []
        seq = 1
        for d in defs:
            for k in range(d["qty"]):
                instances.append({
                    "id": f"i{seq}",
                    "name": f"{d['name']}-{k+1}" if d["qty"] > 1 else d["name"],
                    "w": d["w"], "h": d["h"], "rotate": d["rotate"],
                    "innerText": d["innerText"],
                })
                seq += 1

        self.solving = True
        self.calc_btn.config(state="disabled", text="Đang tính...")
        self.status_lbl.config(text="CP-SAT đang giải, vui lòng đợi...")

        def worker():
            result = solve_packing(instances, H, time_limit=time_limit)
            self.result_queue.put((result, H))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(150, self._poll_result)

    def _poll_result(self):
        try:
            result, H = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(150, self._poll_result)
            return

        self.solving = False
        self.calc_btn.config(state="normal", text="Tính toán")
        self.last_placements = result["placements"]
        self.last_W = result["W_used"]
        self.last_H = H

        self.status_lbl.config(text=f"Trạng thái solver: {result['status']}")

        self.stat_width.config(text=f"{fmt_num(result['W_used'])} mm")
        self.stat_height.config(text=f"{fmt_num(H)} mm")
        area = sum(p["w"] * p["h"] for p in result["placements"])
        eff = (area / (result["W_used"] * H) * 100) if result["W_used"] > 0 else 0
        self.stat_eff.config(text=f"{eff:.1f}%")

        if result["infeasible"]:
            names = ", ".join(f"{it['name']} ({fmt_num(it['w'])}x{fmt_num(it['h'])})"
                               for it in result["infeasible"])
            self.warn_lbl.config(text=f"Không xếp được (không vừa chiều cao tấm dù đã thử xoay, "
                                       f"hoặc solver hết thời gian): {names}")
            self.warn_lbl.pack(fill="x", pady=(10, 0))
        else:
            self.warn_lbl.pack_forget()

        dsl = pieces_to_dsl(result["placements"], result["W_used"], H)
        self.dsl_text.delete("1.0", "end")
        self.dsl_text.insert("1.0", dsl)

        self.redraw()

    # ---------------- Vẽ canvas ----------------
    def redraw(self):
        self.canvas.delete("all")
        if not self.last_placements or self.last_W <= 0:
            return
        W = max(self.canvas.winfo_width(), 100)
        Hpx = max(self.canvas.winfo_height(), 100)
        pad = 20
        avail_w, avail_h = W - 2 * pad, Hpx - 2 * pad
        sheet_w, sheet_h = max(self.last_W, 1), max(self.last_H, 1)
        scale = min(avail_w / sheet_w, avail_h / sheet_h)
        draw_w, draw_h = sheet_w * scale, sheet_h * scale
        ox = pad + (avail_w - draw_w) / 2
        oy = pad + (avail_h - draw_h) / 2

        def to_canvas(x, y):
            return ox + x * scale, oy + draw_h - y * scale

        grid_step = 50
        while sheet_w / grid_step > 24 or sheet_h / grid_step > 24:
            grid_step *= 2
        gx = 0
        while gx <= sheet_w + 1e-6:
            x1, y1 = to_canvas(gx, 0)
            x2, y2 = to_canvas(gx, sheet_h)
            self.canvas.create_line(x1, y1, x2, y2, fill=GRID_LINE)
            gx += grid_step
        gy = 0
        while gy <= sheet_h + 1e-6:
            x1, y1 = to_canvas(0, gy)
            x2, y2 = to_canvas(sheet_w, gy)
            self.canvas.create_line(x1, y1, x2, y2, fill=GRID_LINE)
            gy += grid_step

        sx, sy = to_canvas(0, sheet_h)
        self.canvas.create_rectangle(sx, sy, sx + draw_w, sy + draw_h,
                                      outline=BORDER_STRONG, width=1.5)

        # Chỉ viền, không tô nền, để chữ nhãn/kích thước không bị giảm
        # độ tương phản bởi màu tô của mảnh.
        for i, p in enumerate(self.last_placements):
            color = PALETTE[i % len(PALETTE)]
            px, py = to_canvas(p["x"], p["y"] + p["h"])
            pw, ph = p["w"] * scale, p["h"] * scale
            self.canvas.create_rectangle(px, py, px + pw, py + ph, outline=color, width=1.8)
            label = p["name"] + (" \u21bb" if p["rotated"] else "")
            if pw > 34 and ph > 16:
                self.canvas.create_text(px + 5, py + 10, text=label, fill=TEXT,
                                         font=self.font_ui_xs, anchor="w")
                if ph > 30:
                    dims = f"{fmt_num(p['w'])}x{fmt_num(p['h'])}"
                    self.canvas.create_text(px + 5, py + 24, text=dims, fill=TEXT_DIM,
                                             font=self.font_mono_sm, anchor="w")

    # ---------------- Copy / Lưu ----------------
    def copy_dsl(self):
        text = self.dsl_text.get("1.0", "end").strip()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        self.copy_status.pack(side="right", padx=(0, 10))
        self.root.after(1400, self.copy_status.pack_forget)

    def save_dsl(self):
        text = self.dsl_text.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("Chưa có dữ liệu", "Hãy tính toán trước khi lưu.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text/DSL", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()