from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional, Sequence, Tuple

from common.ui import (
    SIZE_MD,
    SIZE_SM,
    attach_scrollbars,
    canvas_font,
    make_button,
    ui_font,
)
from engraver_ctrl.cut_plan_builder import (
    CUT_EXTRA_MARGIN,
    CutPlan,
    Part,
    arch_polyline,
    piece_polygon,
    build_cut_plan,
    format_hole_field,
    format_parts_text,
    parse_hole_field,
    parse_parts_text,
)
from engraver_ctrl.extended_cut_export import export_gcode_extended
from engraver_ctrl.paths import CUT_PLAN_GCODE_PATH


# Soft fills for preview geometry (controls stay neutral).
PIECE_COLORS = (
    "#cfe8ff",
    "#ffe0b3",
    "#d4f0d4",
    "#f5c6d0",
    "#e4d4f5",
    "#fff3b0",
    "#c9efe5",
    "#f8d5c0",
)
WASTE_FILL = "#f4f4f4"
CUT_COLOR = "#cc0000"
AXIS_COLOR = "#222222"
GRID_COLOR = "#d8d8d8"
GRID_MAJOR = "#b8b8b8"
STICK_OUTLINE = "#5a4030"
HOLE_COLOR = "#7a1028"

HELP_POPUP_SIZE = "520x360"

HELP_TEXT = """\
Small parts — Help

Stock and cut parameters
  Stock Length (mm): total stick length, including both semicircular
    factory ends (default 114).
  Width (mm): stick width; also the diameter of those factory ends
    (default 10).
  Gap (mm): space between neighbouring sticks in the jig (default 5).
  Hole Radius (mm): radius of holes cut on a piece (default 1.5).
  Feedrate (mm/min): cutting feed (default 250).
  Power (0-1000): laser power (default 1000).

Text mode
  One piece per line:
    length, round_bottom, round_top[, hole1, hole2, ...]
  round_bottom / round_top are 0 or 1.
  Holes are millimetres from the bottom of the piece.
  Blank lines and # comments are ignored.
  Example:  50, 1, 0, 10, 30

Cards mode
  Each card is one piece, shown on a single row:
    #n   Len   Bot   Top   Holes   ✕
  Len is the piece length in mm.
  Bot / Top tick a convex rounded cap at that end of the piece.
  Holes are comma- or space-separated, measured from the bottom
    of the piece.
  Add piece appends a card; ✕ removes one.
  Switching between Text and Cards keeps the same data.

Packing
  Packing uses First/Best Fit Decreasing (and an exact solver when
  OR-Tools is available). Kerf is ignored — enter lengths already
  adjusted if needed. Usable length is the full stock length L
  (including both semicircles). Leftover waste is kept as one block;
  a piece with a rounded end is placed at a stick tip when that does
  not use an extra stick. A rounded end is a convex cap whose apex
  sits on that end; the arc replaces the straight cut there, except
  at the factory stick tips (Y=0 and Y=L).
"""


def stadium_slice_polygon(
    x_left: float,
    width: float,
    stock_length: float,
    y0: float,
    y1: float,
    n: int = 20,
) -> List[Tuple[float, float]]:
    """World-coordinate polygon for a y-slice of a stadium stick."""
    r = width / 2.0
    cx = x_left + r
    y0 = max(0.0, min(stock_length, y0))
    y1 = max(0.0, min(stock_length, y1))
    if y1 <= y0 + 1e-12:
        return []

    def half_w(y: float) -> float:
        if y < r:
            d = r * r - (y - r) ** 2
            return math.sqrt(max(0.0, d))
        if y > stock_length - r:
            cy = stock_length - r
            d = r * r - (y - cy) ** 2
            return math.sqrt(max(0.0, d))
        return r

    def add_range(ys, a, b, steps):
        if b <= a + 1e-12:
            ys.append(a)
            return
        for i in range(steps + 1):
            ys.append(a + (b - a) * i / steps)

    ys: List[float] = []
    # Sample rounded caps densely so the ends look like semicircles,
    # not triangles, even when a piece is much longer than W.
    cap1_a, cap1_b = 0.0, min(r, stock_length)
    cap2_a, cap2_b = max(0.0, stock_length - r), stock_length
    mid_a, mid_b = cap1_b, cap2_a

    def overlap_add(a, b, steps):
        lo, hi = max(y0, a), min(y1, b)
        if hi > lo:
            add_range(ys, lo, hi, steps)

    overlap_add(cap1_a, cap1_b, 16)
    if mid_b > mid_a:
        span = min(y1, mid_b) - max(y0, mid_a)
        overlap_add(mid_a, mid_b, max(2, int(span / 4) + 1))
    overlap_add(cap2_a, cap2_b, 16)
    ys.extend([y0, y1])
    ys = sorted(set(round(y, 8) for y in ys))
    right = [(cx + half_w(y), y) for y in ys]
    left = [(cx - half_w(y), y) for y in reversed(ys)]
    return right + left


class _Card:
    def __init__(self, frame, length, down, up, holes, on_remove, font):
        self.frame = frame
        self.length_var = tk.StringVar(value=length)
        self.down_var = tk.BooleanVar(value=down)
        self.up_var = tk.BooleanVar(value=up)
        self.holes_var = tk.StringVar(value=holes)
        self._on_remove = on_remove

        # One compact row: #n  Len [ ]  □Bot  □Top  Holes [ ]  ✕
        # Pack the remove button first (side=right) so the expanding
        # holes field cannot squeeze it off the row.
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=2, pady=1)
        self.row = row
        sm = ui_font(SIZE_SM)
        self.remove_btn = make_button(row, "✕", command=self._remove, width=2)
        self.remove_btn.pack(side="right", padx=(2, 0))
        self.title = ttk.Label(row, text="#1", font=ui_font(SIZE_SM, bold=True))
        self.title.pack(side="left", padx=(0, 4))
        ttk.Label(row, text="Len", font=sm).pack(side="left")
        ttk.Entry(row, textvariable=self.length_var, width=6, font=sm).pack(
            side="left", padx=(3, 6)
        )
        ttk.Checkbutton(row, text="Bot", variable=self.down_var).pack(
            side="left", padx=(0, 4)
        )
        ttk.Checkbutton(row, text="Top", variable=self.up_var).pack(
            side="left", padx=(0, 6)
        )
        ttk.Label(row, text="Holes", font=sm).pack(side="left")
        ttk.Entry(row, textvariable=self.holes_var, width=12, font=sm).pack(
            side="left", padx=(3, 4), fill="x", expand=True
        )

    def _remove(self):
        self._on_remove(self)

    def is_blank(self) -> bool:
        return (
            not self.length_var.get().strip()
            and not self.holes_var.get().strip()
            and not self.down_var.get()
            and not self.up_var.get()
        )


class SmallPartsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.font = getattr(app, "font", None) or ui_font(SIZE_SM)
        self._mode = "text"
        self._cards: List[_Card] = []
        self._plan: Optional[CutPlan] = None
        self._scale = 3.0
        self._x_min = -15.0
        self._x_max = 130.0
        self._y_min = -15.0
        self._y_max = 130.0
        self._margin = 36.0
        self._drag = None
        self._help_win = None
        self.build_ui()

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        self.columnconfigure(0, weight=0, minsize=420)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=(8, 8, 4, 8))
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Small parts", font=ui_font(SIZE_MD, bold=True)).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        form = ttk.Frame(left)
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        self.entry_stock_length = self._add_field(form, 0, "Stock Length (mm):", "114")
        self.entry_width = self._add_field(form, 1, "Width (mm):", "10")
        self.entry_gap = self._add_field(form, 2, "Gap (mm):", "5")
        self.entry_hole_radius = self._add_field(form, 3, "Hole Radius (mm):", "1.5")
        self.entry_feedrate = self._add_field(form, 4, "Feedrate (mm/min):", "250")
        self.entry_power = self._add_field(form, 5, "Power (0-1000):", "1000")

        mode_row = ttk.Frame(left)
        mode_row.grid(row=2, column=0, sticky="w", pady=(10, 2))
        ttk.Label(mode_row, text="Input:").pack(side="left", padx=(0, 8))
        self.mode_var = tk.StringVar(value="text")
        ttk.Radiobutton(
            mode_row, text="Text", value="text",
            variable=self.mode_var, command=self.on_mode_change,
        ).pack(side="left", padx=(0, 8))
        ttk.Radiobutton(
            mode_row, text="Cards", value="cards",
            variable=self.mode_var, command=self.on_mode_change,
        ).pack(side="left", padx=(0, 10))
        self.help_btn = make_button(mode_row, "Help", command=self.show_help)
        self.help_btn.pack(side="left")

        editor = ttk.Frame(left)
        editor.grid(row=3, column=0, sticky="nsew", pady=(0, 4))
        left.rowconfigure(3, weight=1)
        editor.columnconfigure(0, weight=1)
        editor.rowconfigure(0, weight=1)

        # Text mode
        self.text_wrap = ttk.Frame(editor)
        self.text_wrap.grid(row=0, column=0, sticky="nsew")
        self.text_wrap.columnconfigure(0, weight=1)
        self.text_wrap.rowconfigure(0, weight=1)
        self.text_parts = tk.Text(self.text_wrap, width=44, height=10, wrap="none")
        attach_scrollbars(self.text_wrap, self.text_parts, vertical=True, horizontal=True)

        # Cards mode
        self.cards_wrap = ttk.Frame(editor)
        self.cards_wrap.columnconfigure(0, weight=1)
        self.cards_wrap.rowconfigure(0, weight=1)
        self.cards_canvas = tk.Canvas(
            self.cards_wrap, highlightthickness=0, borderwidth=0,
        )
        self.cards_scroll = ttk.Scrollbar(
            self.cards_wrap, orient="vertical", command=self.cards_canvas.yview,
        )
        self.cards_canvas.configure(yscrollcommand=self.cards_scroll.set)
        self.cards_canvas.grid(row=0, column=0, sticky="nsew")
        self.cards_scroll.grid(row=0, column=1, sticky="ns")
        self.cards_inner = ttk.Frame(self.cards_canvas)
        self._cards_window = self.cards_canvas.create_window(
            (0, 0), window=self.cards_inner, anchor="nw",
        )
        self.cards_inner.bind("<Configure>", self._on_cards_inner_configure)
        self.cards_canvas.bind("<Configure>", self._on_cards_canvas_configure)

        self.add_card_btn = make_button(left, "Add piece", command=self.add_card)

        btns = ttk.Frame(left)
        btns.grid(row=5, column=0, sticky="ew", pady=(8, 4))
        make_button(btns, "Preview", command=self.on_preview).pack(
            side="left", padx=(0, 6)
        )
        make_button(btns, "Generate GCODE", command=self.on_generate).pack(
            side="left"
        )

        self.stats_var = tk.StringVar(value="No plan yet.")
        ttk.Label(
            left, textvariable=self.stats_var, wraplength=400, justify="left",
            font=ui_font(SIZE_SM, bold=True),
        ).grid(row=6, column=0, sticky="ew", pady=(4, 0))

        # Right: preview
        right = ttk.Frame(self, padding=(4, 8, 8, 8))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        tools = ttk.Frame(right)
        tools.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(tools, text="Preview", font=ui_font(SIZE_MD, bold=True)).pack(
            side="left", padx=(0, 12)
        )
        make_button(tools, "Zoom +", command=lambda: self._zoom_by(1.25)).pack(
            side="left", padx=(0, 4)
        )
        make_button(tools, "Zoom -", command=lambda: self._zoom_by(0.8)).pack(
            side="left", padx=(0, 4)
        )
        make_button(tools, "Fit", command=self._fit_view).pack(side="left")

        canvas_hold = ttk.Frame(right)
        canvas_hold.grid(row=1, column=0, sticky="nsew")
        canvas_hold.columnconfigure(0, weight=1)
        canvas_hold.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_hold, background="white", highlightthickness=0)
        self.hbar = ttk.Scrollbar(
            canvas_hold, orient="horizontal", command=self.canvas.xview,
        )
        self.vbar = ttk.Scrollbar(
            canvas_hold, orient="vertical", command=self.canvas.yview,
        )
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<Configure>", lambda e: self._redraw_if_plan())

        self._show_mode("text")
        self._redraw()

    def _add_field(self, form, row, label, default):
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="e", pady=2, padx=(0, 6))
        entry = ttk.Entry(form, width=12)
        entry.insert(0, default)
        entry.grid(row=row, column=1, sticky="w", pady=2)
        return entry

    # ------------------------------------------------------------------ modes
    def on_mode_change(self):
        new = self.mode_var.get()
        if new == self._mode:
            return
        try:
            parts = self._read_parts(self._mode, allow_blank=True)
        except ValueError as e:
            self.mode_var.set(self._mode)
            messagebox.showerror("Invalid input", str(e))
            return
        self._mode = new
        self._show_mode(new)
        self._write_parts(new, parts)

    def _show_mode(self, mode: str):
        if mode == "text":
            self.cards_wrap.grid_forget()
            self.add_card_btn.grid_forget()
            self.text_wrap.grid(row=0, column=0, sticky="nsew")
        else:
            self.text_wrap.grid_forget()
            self.cards_wrap.grid(row=0, column=0, sticky="nsew")
            self.add_card_btn.grid(row=4, column=0, sticky="w", pady=(0, 2))


    def show_help(self):
        """Open a modest, scrollable Format Help popup (reuse if already open)."""
        existing = getattr(self, "_help_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_set()
                    return existing
            except tk.TclError:
                pass

        parent = self.winfo_toplevel()
        win = tk.Toplevel(parent)
        self._help_win = win
        win.title("Format Help")
        win.geometry(HELP_POPUP_SIZE)
        win.minsize(360, 240)
        win.resizable(True, True)
        try:
            win.transient(parent)
        except tk.TclError:
            pass

        body = ttk.Frame(win)
        body.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        text = tk.Text(
            body, wrap="word", font=ui_font(SIZE_SM),
            width=48, height=16, relief="solid", borderwidth=1,
        )
        scroll = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        text.insert("1.0", HELP_TEXT)
        text.configure(state="disabled")

        def on_wheel(event):
            if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
                text.yview_scroll(1, "units")
            else:
                text.yview_scroll(-1, "units")
            return "break"

        text.bind("<MouseWheel>", on_wheel)
        text.bind("<Button-4>", on_wheel)
        text.bind("<Button-5>", on_wheel)

        btn_row = ttk.Frame(win)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        close_btn = make_button(btn_row, "Close", command=win.destroy)
        close_btn.pack(side="right")

        win.help_text = text
        win.help_scroll = scroll
        win.close_btn = close_btn

        def _on_close():
            try:
                if getattr(self, "_help_win", None) is win:
                    self._help_win = None
            except Exception:
                pass
            try:
                win.destroy()
            except tk.TclError:
                pass

        win.protocol("WM_DELETE_WINDOW", _on_close)
        close_btn.configure(command=_on_close)
        win.bind("<Escape>", lambda e: _on_close())
        try:
            win.focus_set()
        except tk.TclError:
            pass
        return win

    def _read_parts(self, mode: str, allow_blank: bool = False) -> List[Part]:
        if mode == "text":
            txt = self.text_parts.get("1.0", tk.END)
            parts = parse_parts_text(txt)
            if not parts and not allow_blank and not txt.strip():
                raise ValueError("Enter at least one piece.")
            return parts
        parts: List[Part] = []
        for n, card in enumerate(self._cards, start=1):
            if card.is_blank():
                continue
            raw = card.length_var.get().strip()
            try:
                length = float(raw)
            except ValueError as e:
                raise ValueError(f"Card {n}: invalid length {raw!r}") from e
            if length <= 0:
                raise ValueError(f"Card {n}: length must be positive")
            try:
                holes = parse_hole_field(card.holes_var.get())
            except ValueError as e:
                raise ValueError(f"Card {n}: invalid hole list") from e
            parts.append(Part(
                length=length,
                is_cut_down=bool(card.down_var.get()),
                is_cut_up=bool(card.up_var.get()),
                hole_centers=holes,
            ))
        if not parts and not allow_blank:
            raise ValueError("Enter at least one piece.")
        return parts

    def _write_parts(self, mode: str, parts: Sequence[Part]):
        if mode == "text":
            self.text_parts.delete("1.0", tk.END)
            self.text_parts.insert("1.0", format_parts_text(parts))
            if parts:
                self.text_parts.insert(tk.END, "\n")
        else:
            for card in list(self._cards):
                card.frame.destroy()
            self._cards.clear()
            if not parts:
                self.add_card()
            else:
                for p in parts:
                    self.add_card(
                        length=f"{p.length:g}",
                        down=p.is_cut_down,
                        up=p.is_cut_up,
                        holes=format_hole_field(p.hole_centers),
                    )
            self._renumber_cards()

    def add_card(self, length="", down=False, up=False, holes=""):
        frame = ttk.Frame(self.cards_inner)
        frame.pack(fill="x", padx=2, pady=0)
        card = _Card(
            frame, length, down, up, holes,
            on_remove=self._remove_card, font=self.font,
        )
        self._cards.append(card)
        self._renumber_cards()
        return card

    def _remove_card(self, card: _Card):
        if card in self._cards:
            self._cards.remove(card)
        card.frame.destroy()
        if not self._cards:
            self.add_card()
        self._renumber_cards()

    def _renumber_cards(self):
        for i, card in enumerate(self._cards, start=1):
            card.title.configure(text=f"#{i}")

    def _on_cards_inner_configure(self, _event=None):
        self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))

    def _on_cards_canvas_configure(self, event):
        self.cards_canvas.itemconfigure(self._cards_window, width=event.width)

    # ------------------------------------------------------------------ plan
    def _form_values(self):
        stock = float(self.entry_stock_length.get())
        width = float(self.entry_width.get())
        gap = float(self.entry_gap.get())
        hole_radius = float(self.entry_hole_radius.get())
        feedrate = float(self.entry_feedrate.get())
        power = float(self.entry_power.get())
        if not (0 <= power <= 1000):
            raise ValueError("Power must be between 0 and 1000")
        if feedrate <= 0:
            raise ValueError("Feedrate must be positive")
        return stock, width, gap, hole_radius, feedrate, power

    def _build_plan(self) -> CutPlan:
        parts = self._read_parts(self._mode, allow_blank=False)
        stock, width, gap, hole_radius, _feed, _power = self._form_values()
        return build_cut_plan(
            stock_length=stock,
            parts=parts,
            width=width,
            gap=gap,
            hole_radius=hole_radius,
            include_end_cut=True,
            method="auto",
        )

    def _update_stats(self, plan: CutPlan):
        n = len(plan.sticks)
        waste = plan.waste_length()
        pct = plan.waste_percent()
        text = f"Sticks used: {n}    Waste: {waste:g} mm ({pct:.1f}%)"
        if plan.unplaced:
            bits = []
            for i in plan.unplaced:
                if 0 <= i < len(plan.parts):
                    bits.append(f"P{i + 1} ({plan.parts[i].length:g} mm)")
                else:
                    bits.append(f"#{i + 1}")
            text += f"\nUnplaced: {len(plan.unplaced)}  ({', '.join(bits)})"
        self.stats_var.set(text)

    def on_preview(self):
        try:
            plan = self._build_plan()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self._plan = plan
        self._fit_view()
        self._update_stats(plan)
        if plan.unplaced:
            messagebox.showwarning(
                "Unplaced pieces",
                "Some pieces are longer than the stock length and were not placed.",
            )

    def on_generate(self):
        try:
            plan = self._build_plan()
            _stock, _w, _g, _r, feedrate, power = self._form_values()
            export_gcode_extended(
                plan,
                CUT_PLAN_GCODE_PATH,
                feedrate=feedrate,
                power=power,
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self._plan = plan
        self._fit_view()
        self._update_stats(plan)
        extra = ""
        if plan.unplaced:
            extra = "\nSome pieces were longer than the stock and were not placed."
        messagebox.showinfo(
            "OK",
            f"GCODE written to cut_plan.gcode.\n"
            f"Sticks used: {len(plan.sticks)}.{extra}",
        )

    # ------------------------------------------------------------------ canvas
    def _world_bounds(self):
        plan = self._plan
        if plan is None or not plan.sticks:
            length = 114.0
            try:
                length = float(self.entry_stock_length.get())
            except ValueError:
                pass
            return -15.0, 40.0, -15.0, max(length, 20.0) + 15.0
        x_min = -10.0
        x_max = 20.0
        y_min = -10.0
        y_max = plan.stock_length + 10.0
        for stick in plan.sticks:
            x_min = min(x_min, stick.x_left - CUT_EXTRA_MARGIN - 5)
            x_max = max(x_max, stick.x_left + stick.width + CUT_EXTRA_MARGIN + 5)
        for sx, y, length in plan.cuts:
            x_min = min(x_min, sx)
            x_max = max(x_max, sx + length)
            y_min = min(y_min, y - 5)
            y_max = max(y_max, y + 5)
        return x_min, x_max, y_min, y_max

    def _fit_view(self):
        self._x_min, self._x_max, self._y_min, self._y_max = self._world_bounds()
        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        span_x = max(self._x_max - self._x_min, 1.0)
        span_y = max(self._y_max - self._y_min, 1.0)
        pad = self._margin * 2
        scale = min((cw - pad) / span_x, (ch - pad) / span_y)
        self._scale = max(1.0, min(scale, 20.0))
        self._redraw()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def _zoom_by(self, factor: float, canvas_xy=None):
        old = self._scale
        new = max(0.6, min(old * factor, 24.0))
        if abs(new - old) < 1e-9:
            return
        if canvas_xy is None:
            cx = self.canvas.canvasx(self.canvas.winfo_width() / 2)
            cy = self.canvas.canvasy(self.canvas.winfo_height() / 2)
        else:
            cx, cy = canvas_xy
        wx, wy = self._canvas_to_world(cx, cy)
        self._scale = new
        self._redraw()
        nx, ny = self._world_to_canvas(wx, wy)
        self.canvas.xview_scroll(int(nx - cx), "units")
        # xview_scroll in units is crude; use moveto from pixel delta
        self.canvas.scan_mark(int(nx), int(ny))
        self.canvas.scan_dragto(int(cx), int(cy), gain=1)

    def _on_mousewheel(self, event):
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            factor = 1.15
        else:
            factor = 1 / 1.15
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self._zoom_by(factor, (cx, cy))
        return "break"

    def _on_drag_start(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self._drag = (event.x, event.y)

    def _on_drag_move(self, event):
        if self._drag is None:
            return
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_drag_end(self, _event):
        self._drag = None

    def _world_to_canvas(self, x: float, y: float) -> Tuple[float, float]:
        sx = self._margin + (x - self._x_min) * self._scale
        sy = self._margin + (self._y_max - y) * self._scale
        return sx, sy

    def _canvas_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        x = (sx - self._margin) / self._scale + self._x_min
        y = self._y_max - (sy - self._margin) / self._scale
        return x, y

    def _redraw_if_plan(self):
        self._redraw()

    def _poly(self, points: Sequence[Tuple[float, float]]):
        coords = []
        for x, y in points:
            sx, sy = self._world_to_canvas(x, y)
            coords.extend((sx, sy))
        return coords

    def _line(self, x1, y1, x2, y2, **kwargs):
        a = self._world_to_canvas(x1, y1)
        b = self._world_to_canvas(x2, y2)
        return self.canvas.create_line(a[0], a[1], b[0], b[1], **kwargs)

    def _text(self, x, y, **kwargs):
        sx, sy = self._world_to_canvas(x, y)
        kwargs.setdefault("font", canvas_font())
        return self.canvas.create_text(sx, sy, **kwargs)

    def _grid_step(self) -> float:
        # Aim for ~40-80 px between major labels.
        target = 50.0 / max(self._scale, 0.1)
        steps = (1, 2, 5, 10, 20, 25, 50, 100, 200)
        for s in steps:
            if s >= target:
                return float(s)
        return 200.0

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        plan = self._plan
        x_min, x_max, y_min, y_max = self._x_min, self._x_max, self._y_min, self._y_max
        # Slightly pad the drawn grid past the view bounds.
        step = self._grid_step()

        def frange(a, b, s):
            start = math.floor(a / s) * s
            vals = []
            v = start
            # Guard against float drift.
            while v <= b + s * 0.5:
                vals.append(v)
                v = round(v + s, 8)
            return vals

        for x in frange(x_min, x_max, step):
            color = AXIS_COLOR if abs(x) < 1e-9 else (GRID_MAJOR if abs(x) % (step * 5) < 1e-9 else GRID_COLOR)
            width = 2 if abs(x) < 1e-9 else 1
            self._line(x, y_min, x, y_max, fill=color, width=width)
            if abs(x) >= 1e-9:
                self._text(x, 0.0, text=f"{x:g}", fill="#333", anchor="n")
        for y in frange(y_min, y_max, step):
            color = AXIS_COLOR if abs(y) < 1e-9 else (GRID_MAJOR if abs(y) % (step * 5) < 1e-9 else GRID_COLOR)
            width = 2 if abs(y) < 1e-9 else 1
            self._line(x_min, y, x_max, y, fill=color, width=width)
            if abs(y) >= 1e-9:
                self._text(0.0, y, text=f"{y:g}", fill="#333", anchor="e")

        # Axis arrows and names, drawn on top of the grid.
        tip = max(8.0 / self._scale, 1.5)
        self._line(x_min, 0, x_max, 0, fill=AXIS_COLOR, width=2,
                   arrow=tk.LAST, arrowshape=(10, 12, 4))
        self._line(0, y_min, 0, y_max, fill=AXIS_COLOR, width=2,
                   arrow=tk.LAST, arrowshape=(10, 12, 4))
        self._text(x_max, -tip * 1.5, text="X", fill=AXIS_COLOR, anchor="n",
                   font=ui_font(SIZE_SM, bold=True))
        self._text(-tip * 1.5, y_max, text="Y", fill=AXIS_COLOR, anchor="e",
                   font=ui_font(SIZE_SM, bold=True))
        self._text(-tip, -tip, text="O", fill=AXIS_COLOR, anchor="ne")

        if plan is not None:
            self._draw_plan(plan)

        # Scrollregion from the drawn content.
        bbox = c.bbox("all")
        if bbox:
            c.configure(scrollregion=(
                bbox[0] - 8, bbox[1] - 8, bbox[2] + 8, bbox[3] + 8,
            ))

    def _draw_plan(self, plan: CutPlan):
        # Stick body + pieces + waste, then holes, arches, then red cut lines.
        for stick in plan.sticks:
            outline = stadium_slice_polygon(
                stick.x_left, stick.width, stick.length, 0.0, stick.length,
            )
            coords = self._poly(outline)
            if coords:
                self.canvas.create_polygon(
                    *coords, fill="#fbf6ee", outline=STICK_OUTLINE, width=1,
                )

            for waste_a, waste_b in stick.waste:
                poly = stadium_slice_polygon(
                    stick.x_left, stick.width, stick.length, waste_a, waste_b,
                )
                coords = self._poly(poly)
                if coords:
                    self.canvas.create_polygon(
                        *coords, fill=WASTE_FILL, outline="#888888",
                        width=1, stipple="gray25",
                    )
                    cx = stick.x_left + stick.width / 2.0
                    mid = (waste_a + waste_b) / 2.0
                    if waste_b - waste_a >= 4:
                        self._text(cx, mid, text="waste", fill="#666666")

            for p in stick.placements:
                poly = piece_polygon(
                    stick.x_left, stick.width, p.y_start, p.y_end,
                    p.is_cut_down, p.is_cut_up,
                )
                coords = self._poly(poly)
                color = PIECE_COLORS[p.part_index % len(PIECE_COLORS)]
                if coords:
                    self.canvas.create_polygon(
                        *coords, fill=color, outline=STICK_OUTLINE, width=1,
                    )
                cx = stick.x_left + stick.width / 2.0
                mid = (p.y_start + p.y_end) / 2.0
                self._text(
                    cx, mid,
                    text=f"P{p.part_index + 1}  {p.length:g}",
                    fill="#222222",
                )

            # Stick index just below the bottom cap, outside the stock.
            self._text(
                stick.x_left + stick.width / 2.0,
                -4.0,
                text=f"S{stick.index + 1}",
                fill="#444444",
                anchor="n",
            )

        r = plan.radius
        for hx, hy in plan.holes:
            x0, y0 = self._world_to_canvas(hx - r, hy - r)
            x1, y1 = self._world_to_canvas(hx + r, hy + r)
            # Y is flipped, so the bbox still works.
            self.canvas.create_oval(
                x0, y0, x1, y1, outline=HOLE_COLOR, width=2, fill="",
            )

        half = plan.stick_width / 2.0
        for cx, cy, bulge_up in plan.arches:
            # Convex cap, same path as the G2/G3 export (apex on the end cut).
            points = arch_polyline(cx, cy, half, bulge_up, n=18)
            coords = self._poly(points)
            if len(coords) >= 4:
                self.canvas.create_line(
                    *coords, fill=CUT_COLOR, width=2, capstyle=tk.ROUND,
                )

        for sx, y, length in plan.cuts:
            self._line(
                sx, y, sx + length, y,
                fill=CUT_COLOR, width=2, capstyle=tk.ROUND,
            )

