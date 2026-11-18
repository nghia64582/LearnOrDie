"""Top-level Box tab: generate card-formatted DSL for a plywood box."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from common.ui import (
    JF_HIGHLIGHT,
    JM_HIGHLIGHT,
    SIZE_MD,
    SIZE_SM,
    attach_scrollbars,
    canvas_font,
    make_button,
    mono_font,
    ui_font,
)
from engraver_ctrl.dsl_joint import (
    THICKNESS,
    pair_color,
    parse_joint_file,
    world_mark_corners,
)
from engraver_ctrl.dsl_parse import all_segments, parse_text, segments_bbox

from box_maker.box_core import FACE_NAMES, build_box


class BoxTab(ttk.Frame):
    def __init__(self, parent, shell=None):
        super().__init__(parent)
        self.shell = shell
        self._result = None
        self._view = (0.0, 0.0, 1.0, 1.0)  # left, bottom, right, top
        self._build()

    def _build(self):
        # Bottom action bar first so it stays visible at 1280x720.
        action = ttk.Frame(self)
        action.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        make_button(
            action, "Generate", command=self.generate,
        ).pack(side="left", padx=(0, 6))
        make_button(
            action, "Send to Custom", command=self.send_to_custom,
        ).pack(side="left", padx=(0, 6))
        make_button(
            action, "Save .dsl", command=self.save_dsl,
        ).pack(side="left")
        self.status = ttk.Label(action, text="", font=ui_font(SIZE_SM))
        self.status.pack(side="left", padx=(12, 0))

        # Input row
        form = ttk.Frame(self)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))

        ttk.Label(form, text="Box", font=ui_font(SIZE_MD, bold=True)).grid(
            row=0, column=0, sticky="w", padx=(0, 12),
        )

        self.length_var = tk.StringVar(value="100")
        self.width_var = tk.StringVar(value="60")
        self.height_var = tk.StringVar(value="40")
        self.thickness_var = tk.StringVar(value=str(int(THICKNESS)
                                                   if float(THICKNESS).is_integer()
                                                   else THICKNESS))

        def add_field(col, label, var):
            ttk.Label(form, text=label).grid(row=0, column=col, sticky="e", padx=(0, 4))
            entry = ttk.Entry(form, textvariable=var, width=7)
            entry.grid(row=0, column=col + 1, sticky="w", padx=(0, 10))
            return entry

        add_field(1, "L (mm)", self.length_var)
        add_field(3, "W (mm)", self.width_var)
        add_field(5, "H (mm)", self.height_var)
        add_field(7, "t (mm)", self.thickness_var)

        face_row = ttk.Frame(self)
        face_row.pack(side="top", fill="x", padx=8, pady=(0, 4))
        ttk.Label(face_row, text="Faces").pack(side="left", padx=(0, 8))
        self.face_vars = {}
        for name in FACE_NAMES:
            var = tk.BooleanVar(value=True)
            self.face_vars[name] = var
            ttk.Checkbutton(
                face_row, text=name, variable=var,
            ).pack(side="left", padx=(0, 8))

        # DSL output (modest height, scrollbar) above the action bar;
        # preview canvas takes the remaining space.
        dsl_wrap = ttk.Frame(self)
        dsl_wrap.pack(side="bottom", fill="x", padx=8, pady=(4, 6))
        ttk.Label(dsl_wrap, text="DSL").pack(anchor="w")
        text_host = ttk.Frame(dsl_wrap)
        text_host.pack(fill="x")
        self.dsl_text = tk.Text(
            text_host, height=8, wrap="none", font=mono_font(SIZE_SM),
            state="disabled",
        )
        attach_scrollbars(text_host, self.dsl_text, vertical=True, horizontal=True)

        preview_wrap = ttk.Frame(self)
        preview_wrap.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 4))
        ttk.Label(preview_wrap, text="Preview").pack(anchor="w")
        self.canvas = tk.Canvas(preview_wrap, background="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._redraw())

    # ---- generate / io ----

    def _selected_faces(self):
        return [name for name in FACE_NAMES if self.face_vars[name].get()]

    def _parse_inputs(self):
        def read(var, label):
            raw = var.get().strip()
            try:
                return float(raw)
            except ValueError as exc:
                raise ValueError(f"{label} must be a number") from exc

        return (
            read(self.length_var, "L"),
            read(self.width_var, "W"),
            read(self.height_var, "H"),
            read(self.thickness_var, "t"),
        )

    def generate(self):
        try:
            length, width, height, thickness = self._parse_inputs()
            result = build_box(
                length, width, height,
                thickness=thickness,
                faces=self._selected_faces(),
            )
        except ValueError as exc:
            self._result = None
            self.status.configure(text=str(exc))
            messagebox.showerror("Box", str(exc), parent=self.winfo_toplevel())
            return
        self._result = result
        self._set_dsl(result.dsl)
        n_faces = len(result.faces)
        n_pairs = len(result.pairs)
        msg = f"{n_faces} face(s), {n_pairs} pair(s)"
        if result.warnings:
            msg += f"  ({len(result.warnings)} warning(s))"
        self.status.configure(text=msg)
        self._redraw()

    def _set_dsl(self, text):
        self.dsl_text.configure(state="normal")
        self.dsl_text.delete("1.0", "end")
        self.dsl_text.insert("1.0", text)
        self.dsl_text.configure(state="disabled")

    def current_dsl(self):
        if self._result is not None:
            return self._result.dsl
        return self.dsl_text.get("1.0", "end")

    def send_to_custom(self):
        dsl = (self.current_dsl() or "").strip()
        if not dsl:
            messagebox.showinfo(
                "Box", "Generate a box DSL first.",
                parent=self.winfo_toplevel(),
            )
            return
        tab = getattr(self.shell, "custom_tab", None) if self.shell else None
        if tab is None or not hasattr(tab, "load_dsl"):
            messagebox.showerror(
                "Box", "Custom tab is not available.",
                parent=self.winfo_toplevel(),
            )
            return
        tab.load_dsl(dsl)
        show = getattr(self.shell, "show_custom_tab", None)
        if callable(show):
            show()
        self.status.configure(text="Sent to Custom")

    def save_dsl(self):
        dsl = (self.current_dsl() or "").strip()
        if not dsl:
            messagebox.showinfo(
                "Box", "Generate a box DSL first.",
                parent=self.winfo_toplevel(),
            )
            return
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save box DSL",
            defaultextension=".dsl",
            filetypes=[("DSL files", "*.dsl"), ("Text files", "*.txt"),
                       ("All files", "*.*")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(dsl if dsl.endswith("\n") else dsl + "\n")
        self.status.configure(text=f"Saved {os.path.basename(path)}")

    # ---- preview ----

    def _redraw(self):
        canvas = self.canvas
        canvas.delete("all")
        width = max(int(canvas.winfo_width()), 1)
        height = max(int(canvas.winfo_height()), 1)
        dsl = (self.current_dsl() or "").strip()
        if not dsl:
            canvas.create_text(
                12, 12, text="Generate to preview",
                font=canvas_font(), anchor="nw", fill="#666666",
            )
            return
        segments = all_segments(parse_text(dsl))
        marks, _outlines, _warnings = parse_joint_file(dsl)
        box = segments_bbox(segments)
        if box is None and not marks:
            return
        if box is None:
            xs, ys = [], []
        else:
            minx, miny, maxx, maxy = box
            xs, ys = [minx, maxx], [miny, maxy]
        for mark in marks:
            (x0, y0), (x1, _y), (_x, y1), _ = world_mark_corners(mark)
            xs.extend([x0, x1])
            ys.extend([y0, y1])
        minx, miny, maxx, maxy = min(xs), min(ys), max(xs), max(ys)
        pad = 8.0
        minx -= pad
        miny -= pad
        maxx += pad
        maxy += pad
        span_x = max(maxx - minx, 1e-6)
        span_y = max(maxy - miny, 1e-6)
        scale = min(width / span_x, height / span_y) * 0.92
        # Center the content.
        ox = (width - span_x * scale) / 2.0
        oy = (height - span_y * scale) / 2.0

        def to_canvas(x, y):
            return (ox + (x - minx) * scale,
                    height - (oy + (y - miny) * scale))

        # Origin axes if visible
        if miny <= 0 <= maxy:
            x1, y1 = to_canvas(minx, 0)
            x2, y2 = to_canvas(maxx, 0)
            canvas.create_line(x1, y1, x2, y2, fill="#e08080", width=1)
        if minx <= 0 <= maxx:
            x1, y1 = to_canvas(0, miny)
            x2, y2 = to_canvas(0, maxy)
            canvas.create_line(x1, y1, x2, y2, fill="#8080e0", width=1)

        # J fills first (under strokes), colored by M/F role.
        for mark in marks:
            corners = world_mark_corners(mark)
            coords = []
            for x, y in corners:
                coords.extend(to_canvas(x, y))
            fill = JM_HIGHLIGHT if mark.role == "M" else (
                JF_HIGHLIGHT if mark.role == "F" else "#dddddd"
            )
            outline = pair_color(mark.name)
            canvas.create_polygon(*coords, fill=fill, outline=outline, width=1)

        # Face outlines
        for x1, y1, x2, y2 in segments:
            a = to_canvas(x1, y1)
            b = to_canvas(x2, y2)
            canvas.create_line(a[0], a[1], b[0], b[1], fill="#222222", width=1)

        # J name labels, nudged toward the face interior so labels on
        # touching sheet edges do not sit on top of each other.
        face_of = {}
        if self._result is not None:
            for face in self._result.faces:
                for joint in face.joints:
                    face_of[(joint.pair_name, joint.role)] = face
        for mark in marks:
            corners = world_mark_corners(mark)
            cx = sum(p[0] for p in corners) / 4.0
            cy = sum(p[1] for p in corners) / 4.0
            face = face_of.get((mark.name, mark.role))
            if face is not None:
                fcx = face.dx + face.width / 2.0
                fcy = face.dy + face.height / 2.0
                dx, dy = fcx - cx, fcy - cy
                dist = (dx * dx + dy * dy) ** 0.5 or 1.0
                # Move ~8 mm toward the face center in world space.
                step = min(8.0, dist * 0.5)
                cx += dx / dist * step
                cy += dy / dist * step
            px, py = to_canvas(cx, cy)
            label = f"{mark.name} {mark.role}" if mark.role else mark.name
            canvas.create_text(
                px, py, text=label, font=canvas_font(),
                fill=pair_color(mark.name),
            )

        if self._result is not None:
            for face in self._result.faces:
                # Interior of the face, just below the top-left corner.
                px, py = to_canvas(
                    face.dx + 6, face.dy + face.height - 8,
                )
                canvas.create_text(
                    px, py, text=face.name, font=canvas_font(bold=True),
                    fill="#333333", anchor="nw",
                )
