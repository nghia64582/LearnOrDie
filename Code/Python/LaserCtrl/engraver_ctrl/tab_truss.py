"""Engraver / Truss: design planar popsicle-stick trusses.

Inputs on the left, Optimise -> top-3 layouts, a scaled preview with
layer colours and clickable nodes (glue <-> pin), a piece table and
stats. "Send to Small parts" replaces the Small parts list with the
truss pieces (label + qty) and switches to that tab.
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from common.ui import SIZE_MD, SIZE_SM, canvas_font, make_button, ui_font
from engraver_ctrl.truss_core import (
    KIND_NAMES,
    LOAD_LEVELS,
    TRUSS_TYPES,
    TrussDesign,
    TrussParams,
    optimise,
    to_small_parts,
    toggle_pin,
)

LAYER_FILLS = ("#cfe8ff", "#ffd8a8", "#c8ecc8", "#e4d4f5", "#f5c6d0", "#fff3b0")
LAYER_LINES = ("#4a7fb5", "#c27a2c", "#4f9a4f", "#8a6bb5", "#b5566c", "#b59a2c")
PIN_COLOR = "#7a1028"
GLUE_COLOR = "#ffffff"
NODE_OUTLINE = "#333333"
HELP_POPUP_SIZE = "520x360"

HELP_TEXT = """\
Truss — Help

What it does
  Designs a flat (2D) rectangular truss from popsicle sticks and
  sends the pieces to Small parts for cutting. Several flat trusses
  can later be joined into a 3D frame.

Inputs
  Frame W / H (mm): outer size, node centre to node centre.
  Stick L / W (mm): stick length incl. factory caps and width
    (default 114 x 10). Usable length is L - W (104 mm).
  Thickness (mm): stick thickness, used for the stack height.
  Hole radius (mm): pin hole radius for a 3 mm bamboo skewer
    (default 1.5; try 1.45 for a tighter fit).
  Type: Auto tries all; or Pratt, Howe, Warren, X, K.
  Panels / Rows: auto, or a fixed count along X / Y.
  Max layers: most sticks stacked anywhere (thickness = layers x t).
  Load: Light = glue only; Medium = pins at the 4 corners and at
    splices; Heavy = pins at every joint.
  Hole at every node: drill all joints (holes also help alignment);
    off = holes only where a pin goes.
  Lap splices: let long chords join mid-panel with two pins instead
    of stacking an extra layer on a node.

Pieces
  Each member is a stick lapped over the others at the joints.
  Piece length = node span + W + 2: the hole sits W/2 + 1 from each
  end, centred on the rounded cap. The longest span one stick can
  carry is L - W - (W + 2) = 92 mm on a 114 x 10 stick; longer
  lines are spliced from several sticks (at a node, or with a lap
  splice). Spacer discs (S) fill a skipped layer in a joint stack.

Optimise
  Every layout must be rigid (rigidity rank 2N - 3), every member
  must fit one stick and the layer limit must hold. Layouts are
  ranked by sticks used (Small parts packer), then joints, pieces,
  pins, extra layers and spacers. The best three are listed; click
  one to show it.

Preview
  Colours show the layer of each piece (L1 at the bottom). Filled
  dots are pins, hollow dots are glue joints; small dots are lap
  splice pins. Click a joint to switch it between glue and pin.

Send to Small parts
  Replaces the Small parts list with these pieces (identical
  pieces grouped: label + quantity), copies stick size and hole
  radius, and opens the Small parts tab.
"""


class TrussTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.designs: List[TrussDesign] = []
        self.design: Optional[TrussDesign] = None
        self._help_win = None
        self._scale = 1.0
        self._ox = 0.0
        self._oy = 0.0
        self._node_px = {}
        self.build_ui()

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        self.columnconfigure(0, weight=0, minsize=380)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=(8, 8, 4, 8))
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)

        head = ttk.Frame(left)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(head, text="Truss", font=ui_font(SIZE_MD, bold=True)).pack(side="left")
        self.help_btn = make_button(head, "Help", command=self.show_help)
        self.help_btn.pack(side="right")

        form = ttk.Frame(left)
        form.grid(row=1, column=0, sticky="ew")
        self.e_width = self._field(form, 0, 0, "Frame W (mm):", "300")
        self.e_height = self._field(form, 0, 2, "Frame H (mm):", "60")
        self.e_stock = self._field(form, 1, 0, "Stick L (mm):", "114")
        self.e_stick_w = self._field(form, 1, 2, "Stick W (mm):", "10")
        self.e_thick = self._field(form, 2, 0, "Thickness (mm):", "2")
        self.e_hole = self._field(form, 2, 2, "Hole radius (mm):", "1.5")
        self.e_panels = self._field(form, 3, 0, "Panels:", "auto")
        self.e_rows = self._field(form, 3, 2, "Rows:", "auto")

        ttk.Label(form, text="Type:").grid(row=4, column=0, sticky="e", padx=(0, 4), pady=2)
        self.type_var = tk.StringVar(value="Auto")
        ttk.Combobox(
            form, textvariable=self.type_var, state="readonly", width=8,
            values=("Auto",) + TRUSS_TYPES,
        ).grid(row=4, column=1, sticky="w", pady=2)
        ttk.Label(form, text="Max layers:").grid(row=4, column=2, sticky="e", padx=(8, 4), pady=2)
        self.layers_var = tk.StringVar(value="3")
        ttk.Combobox(
            form, textvariable=self.layers_var, state="readonly", width=8,
            values=("2", "3", "4", "5", "6"),
        ).grid(row=4, column=3, sticky="w", pady=2)
        ttk.Label(form, text="Load:").grid(row=5, column=0, sticky="e", padx=(0, 4), pady=2)
        self.load_var = tk.StringVar(value="Medium")
        ttk.Combobox(
            form, textvariable=self.load_var, state="readonly", width=8,
            values=LOAD_LEVELS,
        ).grid(row=5, column=1, sticky="w", pady=2)

        checks = ttk.Frame(left)
        checks.grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.holes_var = tk.BooleanVar(value=True)
        self.lap_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(checks, text="Hole at every node", variable=self.holes_var).pack(
            side="left", padx=(0, 10))
        ttk.Checkbutton(checks, text="Lap splices", variable=self.lap_var).pack(side="left")

        btns = ttk.Frame(left)
        btns.grid(row=3, column=0, sticky="ew", pady=(8, 4))
        self.optimise_btn = make_button(btns, "Optimise", command=self.on_optimise)
        self.optimise_btn.pack(side="left", padx=(0, 6))
        self.send_btn = make_button(
            btns, "Send to Small parts", command=self.on_send, state="disabled")
        self.send_btn.pack(side="left")

        ttk.Label(left, text="Best layouts", font=ui_font(SIZE_SM, bold=True)).grid(
            row=4, column=0, sticky="w", pady=(6, 2))
        cols = ("layout", "sticks", "pieces", "joints", "pins", "layers")
        self.options = ttk.Treeview(left, columns=cols, show="headings", height=3,
                                    selectmode="browse")
        heads = {"layout": ("Layout", 110), "sticks": ("Sticks", 52),
                 "pieces": ("Pieces", 52), "joints": ("Joints", 52),
                 "pins": ("Pins", 44), "layers": ("Layers", 50)}
        for c in cols:
            text, w = heads[c]
            self.options.heading(c, text=text)
            self.options.column(c, width=w, anchor="w" if c == "layout" else "center",
                                stretch=c == "layout")
        self.options.grid(row=5, column=0, sticky="ew")
        self.options.bind("<<TreeviewSelect>>", self._on_option_select)

        self.stats_var = tk.StringVar(value="Set the frame size and press Optimise.")
        ttk.Label(left, textvariable=self.stats_var, wraplength=360, justify="left",
                  font=ui_font(SIZE_SM)).grid(row=6, column=0, sticky="ew", pady=(8, 0))
        left.rowconfigure(7, weight=1)

        # Right: preview (top) + piece table (bottom)
        right = ttk.Frame(self, padding=(4, 8, 8, 8))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        tools = ttk.Frame(right)
        tools.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(tools, text="Preview", font=ui_font(SIZE_MD, bold=True)).pack(
            side="left", padx=(0, 12))
        make_button(tools, "Fit", command=self.redraw).pack(side="left")
        self.labels_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tools, text="Labels", variable=self.labels_var,
                        command=self.redraw).pack(side="left", padx=(8, 0))
        ttk.Label(tools, text="Click a joint: glue / pin").pack(side="right")

        pane = ttk.PanedWindow(right, orient="vertical")
        pane.grid(row=1, column=0, sticky="nsew")
        canvas_hold = ttk.Frame(pane)
        self.canvas = tk.Canvas(canvas_hold, background="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<Button-1>", self._on_click)
        pane.add(canvas_hold, weight=3)

        table_hold = ttk.Frame(pane)
        table_hold.columnconfigure(0, weight=1)
        table_hold.rowconfigure(0, weight=1)
        pcols = ("label", "kind", "length", "holes", "layer", "nodes")
        self.table = ttk.Treeview(table_hold, columns=pcols, show="headings", height=7)
        pheads = {"label": ("Label", 56), "kind": ("Kind", 90), "length": ("Len", 64),
                  "holes": ("Holes (mm from start)", 220), "layer": ("Layer", 50),
                  "nodes": ("Joints", 160)}
        for c in pcols:
            text, w = pheads[c]
            self.table.heading(c, text=text)
            self.table.column(c, width=w, anchor="w",
                              stretch=c in ("holes", "nodes"))
        vbar = ttk.Scrollbar(table_hold, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=vbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        pane.add(table_hold, weight=1)

    def _field(self, form, row, col, label, default):
        ttk.Label(form, text=label).grid(row=row, column=col, sticky="e",
                                         padx=(0 if col == 0 else 8, 4), pady=2)
        entry = ttk.Entry(form, width=9)
        entry.insert(0, default)
        entry.grid(row=row, column=col + 1, sticky="w", pady=2)
        return entry

    # ------------------------------------------------------------- params
    @staticmethod
    def _count(text: str, name: str) -> Optional[int]:
        raw = text.strip().lower()
        if raw in ("", "auto", "a", "0"):
            return None
        try:
            val = int(raw)
        except ValueError as e:
            raise ValueError(f"{name} must be a whole number or 'auto'") from e
        if val < 1:
            raise ValueError(f"{name} must be >= 1")
        return val

    def read_params(self) -> TrussParams:
        def num(entry, name, positive=True):
            try:
                v = float(entry.get())
            except ValueError as e:
                raise ValueError(f"{name}: enter a number") from e
            if positive and v <= 0:
                raise ValueError(f"{name} must be positive")
            return v

        return TrussParams(
            width=num(self.e_width, "Frame W"),
            height=num(self.e_height, "Frame H"),
            stock_length=num(self.e_stock, "Stick L"),
            stick_width=num(self.e_stick_w, "Stick W"),
            thickness=num(self.e_thick, "Thickness"),
            hole_radius=num(self.e_hole, "Hole radius"),
            truss_type=self.type_var.get(),
            panels=self._count(self.e_panels.get(), "Panels"),
            rows=self._count(self.e_rows.get(), "Rows"),
            max_layers=int(self.layers_var.get()),
            load=self.load_var.get(),
            holes_every_node=bool(self.holes_var.get()),
            lap_splice=bool(self.lap_var.get()),
        )

    # ------------------------------------------------------------ actions
    def on_optimise(self):
        try:
            params = self.read_params()
            if params.hole_radius * 2 >= params.stick_width:
                raise ValueError("Hole diameter must be smaller than the stick width")
            self.configure(cursor="watch")
            self.update_idletasks()
            designs = optimise(params)
        except Exception as e:
            self.configure(cursor="")
            messagebox.showerror("Truss", str(e))
            return
        finally:
            self.configure(cursor="")
        self.designs = designs
        for item in self.options.get_children():
            self.options.delete(item)
        if not designs:
            self.design = None
            self.send_btn.configure(state="disabled")
            self.stats_var.set(
                f"No layout fits. Each member must span <= {params.max_span:g} mm "
                f"(L - W - (W + 2)); try other panels/rows or a bigger stick.")
            self.redraw()
            self._fill_table()
            return
        for i, d in enumerate(designs):
            self.options.insert("", "end", iid=str(i), values=self._option_values(d))
        self.options.selection_set("0")
        self.show_design(designs[0])

    def _option_values(self, d: TrussDesign):
        return (
            f"{d.truss_type} {d.panels}x{d.rows}", d.sticks, len(d.all_pieces),
            len(d.nodes), d.pin_count, d.layers,
        )

    def _on_option_select(self, _event=None):
        sel = self.options.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.designs) and self.designs[idx] is not self.design:
            self.show_design(self.designs[idx])

    def show_design(self, design: TrussDesign):
        self.design = design
        self.send_btn.configure(state="normal")
        self._update_stats()
        self._fill_table()
        self.redraw()

    def on_send(self):
        d = self.design
        if d is None:
            return
        small = getattr(self.app, "small_parts_tab", None)
        if small is None:
            messagebox.showerror("Truss", "Small parts tab is not available.")
            return
        parts = to_small_parts(d)
        # Show the tab first so its preview canvas has a real size.
        show = getattr(self.app, "show_engraver_tab", None)
        if callable(show):
            show("Small parts")
            try:
                small.update_idletasks()
            except tk.TclError:
                pass
        small.load_parts(
            parts,
            stock_length=d.params.stock_length,
            width=d.params.stick_width,
            hole_radius=d.params.hole_radius,
        )

    # -------------------------------------------------------------- stats
    def _update_stats(self):
        d = self.design
        if d is None:
            self.stats_var.set("")
            return
        p = d.params
        hist = ", ".join(f"{k} layers x{v}" for k, v in d.stack_histogram().items() if k)
        skewer = sum(d.skewer_length(v) for v in range(len(d.nodes)) if d.pins[v])
        lines = [
            f"{d.truss_type} {d.panels} panels x {d.rows} rows",
            f"Sticks: {d.sticks} ({'exact' if d.exact else 'heuristic'} packing),"
            f" offcuts {d.waste:.0f} mm (factory caps not counted)",
            f"Pieces: {len(d.pieces)} + {len(d.spacers)} spacers",
            f"Joints: {len(d.nodes)} ({d.lap_splices} lap splices), pins: {d.pin_count}",
            f"Layers: {d.layers} -> {d.thickness:g} mm thick",
            f"Joint stacks: {hist}",
            f"Skewer: {skewer:.0f} mm total (stack + 2 mm per pin)",
            f"Max span per stick: {p.max_span:g} mm",
        ]
        if d.relaxed_layers:
            lines.append(
                f"Note: no layout fits {p.max_layers} layers; "
                f"showing the thinnest ({d.relaxed_layers}).")
        self.stats_var.set("\n".join(lines))

    def _node_name(self, v: int) -> str:
        d = self.design
        if d is None:
            return ""
        if d.aux[v]:
            k = sum(1 for a in d.aux[:v + 1] if a)
            return f"J{k}"
        k = sum(1 for a in d.aux[:v + 1] if not a)
        return f"N{k}"

    def _fill_table(self):
        for item in self.table.get_children():
            self.table.delete(item)
        d = self.design
        if d is None:
            return
        for p in d.all_pieces:
            holes = ", ".join(f"{h:g}" for h in (round(x, 2) for x in p.holes))
            joints = " ".join(self._node_name(v) for v in p.nodes)
            self.table.insert("", "end", values=(
                p.label, KIND_NAMES.get(p.kind, p.kind), f"{p.length:.2f}".rstrip("0").rstrip("."),
                holes, f"L{p.layer + 1}", joints,
            ))

    # ------------------------------------------------------------ preview
    def _to_px(self, x, y):
        return self._ox + x * self._scale, self._oy - y * self._scale

    def redraw(self):
        c = self.canvas
        c.delete("all")
        self._node_px = {}
        d = self.design
        cw = max(c.winfo_width(), 50)
        ch = max(c.winfo_height(), 50)
        if d is None:
            c.create_text(cw / 2, ch / 2, text="No truss yet — press Optimise.",
                          fill="#666666", font=canvas_font())
            return
        p = d.params
        e = p.end_offset
        margin = 40 + e
        W, H = p.width, p.height
        sx = (cw - 2 * margin) / max(W + 2 * e, 1)
        sy = (ch - 2 * margin - 18) / max(H + 2 * e, 1)
        self._scale = max(0.2, min(sx, sy))
        self._ox = (cw - W * self._scale) / 2
        self._oy = (ch + H * self._scale) / 2 + 9

        # Pieces, bottom layer first.
        for piece in sorted(d.pieces + d.spacers, key=lambda q: q.layer):
            fill = LAYER_FILLS[piece.layer % len(LAYER_FILLS)]
            line = LAYER_LINES[piece.layer % len(LAYER_LINES)]
            w_px = max(2.0, p.stick_width * self._scale)
            if piece.kind == "S":
                x, y = self._to_px(*piece.p0)
                r = e * self._scale
                c.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=line)
                continue
            (x0, y0), (x1, y1) = piece.p0, piece.p1
            ln = math.hypot(x1 - x0, y1 - y0) or 1.0
            ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
            ext = e - p.stick_width / 2.0  # round cap tip reaches e
            a = self._to_px(x0 - ux * ext, y0 - uy * ext)
            b = self._to_px(x1 + ux * ext, y1 + uy * ext)
            c.create_line(*a, *b, width=w_px + 2, fill=line, capstyle=tk.ROUND)
            c.create_line(*a, *b, width=w_px, fill=fill, capstyle=tk.ROUND)
        if self.labels_var.get():
            for piece in d.pieces:
                mx = (piece.p0[0] + piece.p1[0]) / 2
                my = (piece.p0[1] + piece.p1[1]) / 2
                x, y = self._to_px(mx, my)
                c.create_text(x, y, text=piece.label, fill="#222222", font=canvas_font())

        # Joints.
        hr = max(3.0, p.hole_radius * self._scale)
        for v, (nx, ny) in enumerate(d.nodes):
            x, y = self._to_px(nx, ny)
            self._node_px[v] = (x, y)
            r = hr * (0.75 if d.aux[v] else 1.0)
            fill = PIN_COLOR if d.pins[v] else GLUE_COLOR
            c.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=NODE_OUTLINE,
                          width=1.5, tags=("node", f"node{v}"))
            if self.labels_var.get() and not d.aux[v]:
                stack = d.node_stack(v)
                c.create_text(x + r + 2, y - r - 2, anchor="sw",
                              text=f"{self._node_name(v)}" + (f"·{stack}" if stack > 2 else ""),
                              fill="#555555", font=canvas_font())

        # Legend.
        lx, ly = 10, 10
        for k in range(d.layers):
            c.create_rectangle(lx, ly, lx + 14, ly + 10, fill=LAYER_FILLS[k % 6],
                               outline=LAYER_LINES[k % 6])
            c.create_text(lx + 18, ly + 5, anchor="w", text=f"L{k + 1}", font=canvas_font())
            lx += 46
        c.create_oval(lx, ly, lx + 10, ly + 10, fill=PIN_COLOR, outline=NODE_OUTLINE)
        c.create_text(lx + 14, ly + 5, anchor="w", text="pin", font=canvas_font())
        lx += 46
        c.create_oval(lx, ly, lx + 10, ly + 10, fill=GLUE_COLOR, outline=NODE_OUTLINE)
        c.create_text(lx + 14, ly + 5, anchor="w", text="glue", font=canvas_font())
        lx += 50
        c.create_text(lx, ly + 5, anchor="w", fill="#555555", font=canvas_font(),
                      text=f"{d.params.width:g} x {d.params.height:g} mm   N·k = k layers")

    def node_at(self, x: float, y: float, radius: float = 10.0) -> Optional[int]:
        best, best_d = None, radius
        for v, (px, py) in self._node_px.items():
            dist = math.hypot(px - x, py - y)
            if dist <= best_d:
                best, best_d = v, dist
        return best

    def _on_click(self, event):
        v = self.node_at(event.x, event.y)
        if v is None or self.design is None:
            return
        self.toggle_node(v)

    def toggle_node(self, v: int):
        d = self.design
        toggle_pin(d, v, method="heuristic")
        sel = self.options.selection()
        if sel:
            self.options.item(sel[0], values=self._option_values(d))
        self._update_stats()
        self._fill_table()
        self.redraw()

    # --------------------------------------------------------------- help
    def show_help(self):
        existing = self._help_win
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    return existing
            except tk.TclError:
                pass
        parent = self.winfo_toplevel()
        win = tk.Toplevel(parent)
        self._help_win = win
        win.title("Truss Help")
        win.geometry(HELP_POPUP_SIZE)
        win.minsize(360, 240)
        try:
            win.transient(parent)
        except tk.TclError:
            pass
        body = ttk.Frame(win)
        body.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        text = tk.Text(body, wrap="word", font=ui_font(SIZE_SM), width=48, height=16,
                       relief="solid", borderwidth=1)
        scroll = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        text.insert("1.0", HELP_TEXT)
        text.configure(state="disabled")
        row = ttk.Frame(win)
        row.pack(fill="x", padx=8, pady=(0, 8))

        def close():
            if self._help_win is win:
                self._help_win = None
            try:
                win.destroy()
            except tk.TclError:
                pass

        close_btn = make_button(row, "Close", command=close)
        close_btn.pack(side="right")
        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _e: close())
        win.help_text = text
        win.close_btn = close_btn
        return win
