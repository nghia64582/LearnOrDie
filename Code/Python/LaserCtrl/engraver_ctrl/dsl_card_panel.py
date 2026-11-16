"""Scrollable card list widget for the Custom tab Shapes panel."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from common.ui import make_button, mono_font, ui_font, SIZE_SM
from engraver_ctrl.dsl_cards import (
    add_card as logic_add_card,
    apply_inferred_size,
    assemble_cards,
    assemble_line_ranges,
    card_index_for_line,
    copy_card,
    duplicate_card as logic_duplicate_card,
    fmt_delta,
    parse_cards,
)


LIST_HEIGHT = 270
INNER_EDITOR_HEIGHT = 7

# Prefer a compact glyph; fall back if the UI font has no glyph (common
# on Windows Segoe UI for dingbats). Tooltip text is always the full word.
_DUP_GLYPHS = ("❐", "⧉", "❏", "++")
_DEL_GLYPHS = ("×", "✕", "x")


def _font_has_glyph(font, ch):
    try:
        if font.measure(ch) <= 0:
            return False
        # A missing glyph is often substituted at the same width as U+FFFD
        # or a last-resort box; treat equal-to-unknown as missing.
        if font.measure(ch) == font.measure("\uffff") and ch != "\uffff":
            return False
    except tk.TclError:
        return False
    return True


def _pick_glyph(font, candidates):
    for ch in candidates:
        if _font_has_glyph(font, ch):
            return ch
    return candidates[-1]


def _tooltip(widget, text):
    """Show English hover text under a compact icon button."""
    tip = {"win": None}

    def show(_event=None):
        if tip["win"] is not None:
            return
        try:
            x = widget.winfo_rootx() + 6
            y = widget.winfo_rooty() + widget.winfo_height() + 2
        except tk.TclError:
            return
        win = tk.Toplevel(widget)
        win.wm_overrideredirect(True)
        try:
            win.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        win.wm_geometry(f"+{x}+{y}")
        tk.Label(win, text=text, font=ui_font(SIZE_SM), bd=1, relief="solid",
                 padx=4, pady=1).pack()
        tip["win"] = win

    def hide(_event=None):
        win = tip["win"]
        tip["win"] = None
        if win is not None:
            try:
                win.destroy()
            except tk.TclError:
                pass

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)
    widget.bind("<ButtonPress>", hide)


class CardPanel(ttk.Frame):
    """List of cards: collapsed header + one expanded inner DSL editor."""

    def __init__(self, parent, font=None, on_commit=None, on_preview=None,
                 on_ctrl_return=None):
        super().__init__(parent)
        self.font = font or ui_font(SIZE_SM)
        self.on_commit = on_commit
        self.on_preview = on_preview
        self.on_ctrl_return = on_ctrl_return
        self._cards = []
        self._rows = []
        self._expanded = None
        self.dirty = False

        self.canvas = tk.Canvas(
            self, highlightthickness=0, height=LIST_HEIGHT, borderwidth=0,
        )
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.inner = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind("<Destroy>", self._cancel_idle, add="+")
        self._idle_jobs = []
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind(seq, self._on_mousewheel)
            self.inner.bind(seq, self._on_mousewheel)

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------
    def cards(self):
        self._harvest()
        return list(self._cards)

    def set_cards(self, cards, expand=None, keep_expand=True):
        self._harvest()
        prev = self._expanded
        self._cards = [copy_card(c) for c in cards]
        if expand is not None:
            self._expanded = expand
        elif keep_expand and prev is not None and prev < len(self._cards):
            self._expanded = prev
        else:
            self._expanded = None
        self.dirty = False
        self._rebuild()

    def load_text(self, text, keep_expand=True):
        self.set_cards(parse_cards(text), keep_expand=keep_expand)

    def assemble(self):
        self._harvest()
        return assemble_cards(self._cards)

    def set_inner(self, index, inner):
        self._harvest()
        if 0 <= index < len(self._cards):
            self._cards[index].inner = inner
            self.dirty = True
            if self._expanded == index and index < len(self._rows):
                editor = self._rows[index].get("editor")
                if editor is not None:
                    editor.delete("1.0", "end")
                    editor.insert("1.0", inner)
            self._fire_commit(preview=True)

    def add_card(self):
        self._harvest()
        self._cards, card = logic_add_card(self._cards)
        self._expanded = len(self._cards) - 1
        self.dirty = True
        self._rebuild()
        self._fire_commit(preview=True)
        self.select_index(self._expanded, expand=True, scroll=True)
        return card

    def duplicate_card(self, index):
        self._harvest()
        if not (0 <= index < len(self._cards)):
            return None
        self._cards, card = logic_duplicate_card(self._cards, index)
        self._expanded = index + 1
        self.dirty = True
        self._rebuild()
        self._fire_commit(preview=True)
        self.select_index(self._expanded, expand=True, scroll=True)
        return card

    def delete_card(self, index):
        self._harvest()
        if not (0 <= index < len(self._cards)):
            return
        del self._cards[index]
        if self._expanded is None:
            pass
        elif self._expanded == index:
            self._expanded = None
        elif self._expanded > index:
            self._expanded -= 1
        self.dirty = True
        self._rebuild()
        self._fire_commit(preview=True)

    def select_index(self, index, expand=True, scroll=True):
        if not (0 <= index < len(self._cards)):
            return
        if expand and self._expanded != index:
            self._harvest()
            self._expanded = index
            self._rebuild()
        if scroll:
            self._scroll_to(index)

    def select_by_add_line(self, line, expand=True, scroll=True):
        self._harvest()
        idx = card_index_for_line(self._cards, line)
        if idx is not None:
            self.select_index(idx, expand=expand, scroll=scroll)
        return idx

    def line_ranges(self):
        self._harvest()
        return assemble_line_ranges(self._cards)

    # ------------------------------------------------------------------
    # Build rows
    # ------------------------------------------------------------------
    def _rebuild(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self._rows = []
        for i, card in enumerate(self._cards):
            self._rows.append(self._build_row(i, card))
        self._after_idle(self._sync_scrollregion)

    def _build_row(self, index, card):
        row = {"editor": None}
        frame = ttk.Frame(self.inner, padding=(2, 2))
        frame.pack(fill="x", padx=2, pady=2)

        header = ttk.Frame(frame)
        header.pack(fill="x")

        expanded = self._expanded == index
        chevron = ">" if not expanded else "v"
        tog = make_button(
            header, chevron, command=lambda i=index: self._toggle(i), width=2,
        )
        tog.pack(side="left", padx=(0, 2))

        name_var = tk.StringVar(value=card.name)
        dx_var = tk.StringVar(value=fmt_delta(card.dx))
        dy_var = tk.StringVar(value=fmt_delta(card.dy))
        w_var = tk.StringVar(value="" if card.w is None else fmt_delta(card.w))
        h_var = tk.StringVar(value="" if card.h is None else fmt_delta(card.h))
        border_var = tk.BooleanVar(value=bool(card.border))
        row["name_var"] = name_var
        row["dx_var"] = dx_var
        row["dy_var"] = dy_var
        row["w_var"] = w_var
        row["h_var"] = h_var
        row["border_var"] = border_var
        row["frame"] = frame

        name_e = ttk.Entry(header, textvariable=name_var, width=10, font=self.font)
        name_e.pack(side="left", padx=1)
        ttk.Label(header, text="dx", font=self.font).pack(side="left")
        dx_e = ttk.Entry(header, textvariable=dx_var, width=4, font=self.font)
        dx_e.pack(side="left", padx=1)
        ttk.Label(header, text="dy", font=self.font).pack(side="left")
        dy_e = ttk.Entry(header, textvariable=dy_var, width=4, font=self.font)
        dy_e.pack(side="left", padx=1)

        try:
            icon_font = tkfont.Font(font=self.font)
        except tk.TclError:
            icon_font = tkfont.nametofont("TkDefaultFont")
        dup_ch = _pick_glyph(icon_font, _DUP_GLYPHS)
        del_ch = _pick_glyph(icon_font, _DEL_GLYPHS)
        dup_btn = make_button(
            header, dup_ch, command=lambda i=index: self.duplicate_card(i),
            width=2, padding=(2, 0),
        )
        dup_btn.pack(side="left", padx=(4, 1))
        _tooltip(dup_btn, "Duplicate")
        del_btn = make_button(
            header, del_ch, command=lambda i=index: self.delete_card(i),
            width=2, padding=(2, 0),
        )
        del_btn.pack(side="left", padx=1)
        _tooltip(del_btn, "Delete")

        header.bind("<Button-1>", lambda e, i=index: self._toggle(i))

        for entry, kind in ((name_e, "name"), (dx_e, "dx"), (dy_e, "dy")):
            entry.bind("<Return>", lambda e, i=index: self._apply_fields(i, preview=True))
            entry.bind("<FocusOut>", lambda e, i=index: self._apply_fields(i, preview=True))
            entry.bind("<KeyRelease>", lambda e, i=index: self._mark_dirty())

        # w / h / border sit on a second line: the first row (name, dx, dy,
        # icon buttons) already fills a typical 40-char Shapes column.
        size_row = ttk.Frame(frame)
        size_row.pack(fill="x", padx=(22, 0), pady=(2, 0))
        ttk.Label(size_row, text="w", font=self.font).pack(side="left")
        w_e = ttk.Entry(size_row, textvariable=w_var, width=4, font=self.font)
        w_e.pack(side="left", padx=1)
        ttk.Label(size_row, text="h", font=self.font).pack(side="left")
        h_e = ttk.Entry(size_row, textvariable=h_var, width=4, font=self.font)
        h_e.pack(side="left", padx=1)
        ttk.Checkbutton(
            size_row, text="border", variable=border_var,
            command=lambda i=index: self._apply_fields(i, preview=True),
        ).pack(side="left", padx=(6, 0))

        def _live_size(_event=None, i=index):
            self._mark_dirty()
            if i >= len(self._rows):
                return
            row_ = self._rows[i]
            for key in ("w_var", "h_var"):
                raw = row_[key].get().strip()
                if raw == "":
                    continue
                try:
                    float(raw)
                except (ValueError, tk.TclError):
                    return
            self._apply_fields(i, preview=True)

        for entry in (w_e, h_e):
            entry.bind("<Return>", lambda e, i=index: self._apply_fields(i, preview=True))
            entry.bind("<FocusOut>", lambda e, i=index: self._apply_fields(i, preview=True))
            entry.bind("<KeyRelease>", _live_size)

        if expanded:
            editor = tk.Text(
                frame, width=36, height=INNER_EDITOR_HEIGHT,
                font=mono_font(SIZE_SM), undo=True, wrap="none",
            )
            editor.pack(fill="x", pady=(4, 0))
            if card.inner:
                editor.insert("1.0", card.inner)
            editor.bind("<Control-Return>", self._on_ctrl_return)
            editor.bind("<KeyRelease>", lambda e: self._mark_dirty())
            editor.bind("<FocusOut>", lambda e, i=index: self._apply_fields(i, preview=False))
            row["editor"] = editor
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                editor.bind(seq, self._on_mousewheel)

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            frame.bind(seq, self._on_mousewheel)
            header.bind(seq, self._on_mousewheel)
            size_row.bind(seq, self._on_mousewheel)
        return row

    def _toggle(self, index):
        self._harvest()
        self._expanded = None if self._expanded == index else index
        self._rebuild()
        if self._expanded is not None:
            self._scroll_to(self._expanded)

    def _mark_dirty(self):
        self.dirty = True

    def _apply_fields(self, index, preview=False):
        self._harvest()
        if self.dirty:
            self._fire_commit(preview=preview)

    def _read_opt_float(self, var, current):
        """Parse an optional float entry; empty means unset (None)."""
        try:
            raw = var.get().strip()
        except tk.TclError:
            return current
        if raw == "":
            return None
        try:
            return float(raw)
        except ValueError:
            var.set("" if current is None else fmt_delta(current))
            return current

    def _harvest(self):
        if not self._rows or len(self._rows) != len(self._cards):
            return
        changed = False
        for i, (card, row) in enumerate(zip(self._cards, self._rows)):
            try:
                name = row["name_var"].get().strip()
            except tk.TclError:
                return
            if card.name != name:
                card.name = name
                changed = True
            try:
                dx = float(row["dx_var"].get().strip() or 0)
            except ValueError:
                row["dx_var"].set(fmt_delta(card.dx))
                dx = card.dx
            if dx != card.dx:
                card.dx = dx
                changed = True
            try:
                dy = float(row["dy_var"].get().strip() or 0)
            except ValueError:
                row["dy_var"].set(fmt_delta(card.dy))
                dy = card.dy
            if dy != card.dy:
                card.dy = dy
                changed = True
            w = self._read_opt_float(row["w_var"], card.w)
            if w != card.w:
                card.w = w
                changed = True
            h = self._read_opt_float(row["h_var"], card.h)
            if h != card.h:
                card.h = h
                changed = True
            try:
                border = bool(row["border_var"].get())
            except (tk.TclError, KeyError):
                border = card.border
            if border != card.border:
                card.border = border
                changed = True
            editor = row.get("editor")
            if editor is not None:
                try:
                    inner = editor.get("1.0", "end-1c")
                except tk.TclError:
                    inner = card.inner
                if inner != card.inner:
                    card.inner = inner
                    changed = True
            # Ticking border with empty w/h: fill from the current inner bbox.
            if card.border and (card.w is None or card.h is None):
                prev = (card.w, card.h)
                apply_inferred_size(card)
                if (card.w, card.h) != prev:
                    if card.w is not None:
                        row["w_var"].set(fmt_delta(card.w))
                    if card.h is not None:
                        row["h_var"].set(fmt_delta(card.h))
                    changed = True
        if changed:
            self.dirty = True

    def _fire_commit(self, preview=False):
        if self.on_commit:
            self.on_commit()
        if preview and self.on_preview:
            self.on_preview()

    def _on_ctrl_return(self, event):
        self._harvest()
        self.dirty = True
        if self.on_ctrl_return:
            self.on_ctrl_return()
        elif self.on_preview:
            self.on_preview()
        return "break"

    # ------------------------------------------------------------------
    # Scroll
    # ------------------------------------------------------------------
    def _after_idle(self, fn):
        try:
            if not self.winfo_exists():
                return
            job = self.after_idle(fn)
            self._idle_jobs.append(job)
        except tk.TclError:
            pass

    def _cancel_idle(self, _event=None):
        for job in getattr(self, "_idle_jobs", []):
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self._idle_jobs = []

    def _on_inner_configure(self, _event=None):
        self._after_idle(self._sync_scrollregion)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def _sync_scrollregion(self):
        try:
            if not self.winfo_exists():
                return
            self.canvas.configure(scrollregion=self.canvas.bbox("all") or (0, 0, 0, 0))
        except tk.TclError:
            pass

    def _on_mousewheel(self, event):
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self.canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            self.canvas.yview_scroll(1, "units")
        return "break"

    def _scroll_to(self, index):
        if not (0 <= index < len(self._rows)):
            return
        frame = self._rows[index].get("frame")
        if frame is None:
            return

        def _go():
            try:
                self.update_idletasks()
                y = frame.winfo_y()
                total = max(self.inner.winfo_height(), 1)
                self.canvas.yview_moveto(max(0.0, y / total))
            except tk.TclError:
                pass

        self._after_idle(_go)
