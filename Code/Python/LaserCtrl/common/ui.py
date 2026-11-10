"""
LaserCtrl shared UI config — EDIT THIS FILE to change app-wide look.

One font family + three sizes for every label/button/text widget.
Buttons stay neutral (native/default ttk); do not paint custom colors
on controls. Geometry / preview drawing may still use semantic colors.
"""

from __future__ import annotations

import sys

# ---------------------------------------------------------------------------
# >>> Easy-to-edit theme knobs (single source of truth)
# ---------------------------------------------------------------------------

# Preferred UI family (first available on the machine wins).
# ONE family for every text: labels, buttons, Text editors, canvas labels.
FONT_FAMILY_PREF = ("Segoe UI", "DejaVu Sans", "Helvetica", "Arial")

# Only these three UI sizes are used across the whole app.
SIZE_SM = 10   # default body / labels / buttons / notebook tabs
SIZE_MD = 12   # section emphasis / result values
SIZE_LG = 14   # rare headings

# Buttons: use ttk.Button (native neutral). No custom bg/fg on controls.
USE_TTK_BUTTONS = True

# Notebook tab chip padding (horizontal, vertical).
NOTEBOOK_TAB_PADDING = (16, 7)
NOTEBOOK_TAB_PADDING_SELECTED = (16, 8)
NOTEBOOK_PADDING = 4

# Preview-only fills for male/female mortise-tenon joints (under G-code strokes).
JM_HIGHLIGHT = "#bbd9f7"  # soft blue (male / tenon)
JF_HIGHLIGHT = "#f6cbb8"  # soft peach (female / mortise)

# ---------------------------------------------------------------------------
# Resolved at runtime by init_fonts()
# ---------------------------------------------------------------------------
FONT_FAMILY = "TkDefaultFont"
# Alias kept for call-site compatibility; always equals FONT_FAMILY (not a
# separate monospace face — user requires one family everywhere).
MONO_FAMILY = FONT_FAMILY
_SCALE = 1.0
_INITIALIZED = False


def enable_dpi_awareness():
    """Call once before creating tk.Tk(). Safe no-op on non-Windows."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
    except Exception:
        return False
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return True
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return True
    except Exception:
        return False


def init_scaling(root):
    global _SCALE
    try:
        _SCALE = max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
    except Exception:
        _SCALE = 1.0
    return _SCALE


def px(n):
    return int(round(n * _SCALE))


def _pick(root, prefs, default):
    try:
        from tkinter import font as tkfont
        have = set(tkfont.families(root))
    except Exception:
        return default
    for f in prefs:
        if f in have:
            return f
    for f in ("DejaVu Sans", "Liberation Sans", "FreeSans", "Helvetica", "Arial"):
        if f in have:
            return f
    # Avoid leaving the sentinel name "TkDefaultFont" as a family string.
    return default if default in have else "Helvetica"


def ui_font(size=None, bold=False):
    """Tuple font for labels/buttons (UI family)."""
    sz = SIZE_SM if size is None else size
    if bold:
        return (FONT_FAMILY, sz, "bold")
    return (FONT_FAMILY, sz)


def mono_font(size=None):
    """Alias of ui_font for DSL / log Text widgets.

    Uses the SAME shared UI family (not Consolas/Courier). Name kept so
    existing call sites do not need a mass rename.
    """
    return ui_font(size)


def canvas_font(bold=False):
    """Canvas overlay labels — always SIZE_SM of the UI family."""
    return ui_font(SIZE_SM, bold=bold)


def fonts(size=None):
    """Back-compat tuple pack: (ui, ui_bold, ui_sm_alias, mono, ui_md_bold)."""
    base = SIZE_SM if size is None else size
    return (
        ui_font(base),
        ui_font(base, bold=True),
        ui_font(base),
        mono_font(base),
        ui_font(SIZE_MD, bold=True),
    )


def make_button(parent, text, command=None, **kwargs):
    """Neutral control button. Prefers ttk; never applies custom colors."""
    from tkinter import ttk
    # Drop any accidental color kwargs so callers cannot reintroduce orange.
    for key in ("bg", "fg", "activebackground", "activeforeground",
                "highlightbackground", "highlightcolor", "selectcolor"):
        kwargs.pop(key, None)
    if USE_TTK_BUTTONS:
        opts = {k: v for k, v in kwargs.items()
                if k in ("state", "width", "padding", "style", "cursor")}
        return ttk.Button(parent, text=text, command=command, **opts)
    import tkinter as tk
    return tk.Button(parent, text=text, command=command, **kwargs)


def attach_scrollbars(parent, text_widget, vertical=True, horizontal=True):
    """Grid a Text with ttk scrollbars. Returns (vbar, hbar) (may be None)."""
    from tkinter import ttk
    vbar = hbar = None
    text_widget.grid(row=0, column=0, sticky="nsew")
    if vertical:
        vbar = ttk.Scrollbar(parent, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=vbar.set)
        vbar.grid(row=0, column=1, sticky="ns")
    if horizontal:
        hbar = ttk.Scrollbar(parent, orient="horizontal", command=text_widget.xview)
        text_widget.configure(xscrollcommand=hbar.set)
        hbar.grid(row=1, column=0, sticky="ew")
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    return vbar, hbar


def init_fonts(root, size=None):
    """Resolve family, install named fonts, set ttk/option defaults."""
    global FONT_FAMILY, MONO_FAMILY, _INITIALIZED
    size = SIZE_SM if size is None else size
    FONT_FAMILY = _pick(root, FONT_FAMILY_PREF, "Helvetica")
    try:
        from tkinter import font as tkfont
        # Normalize to the engine's actual family string (e.g. DejaVu Sans).
        FONT_FAMILY = tkfont.Font(
            root=root, family=FONT_FAMILY, size=SIZE_SM
        ).actual("family")
    except Exception:
        pass
    MONO_FAMILY = FONT_FAMILY  # one family everywhere
    try:
        from tkinter import font as tkfont
        from tkinter import ttk
        for name in (
            "TkDefaultFont", "TkTextFont", "TkMenuFont",
            "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
            "TkIconFont", "TkTooltipFont",
        ):
            tkfont.nametofont(name, root).configure(family=FONT_FAMILY, size=size)
        # TkFixedFont also forced to the shared UI family (no Courier/Consolas).
        tkfont.nametofont("TkFixedFont", root).configure(
            family=FONT_FAMILY, size=size
        )
        # Named fonts for explicit use in widgets/canvas (all same family).
        for n, sz, weight in (
            ("AppFont", SIZE_SM, "normal"),
            ("AppFontBold", SIZE_SM, "bold"),
            ("AppFontMd", SIZE_MD, "normal"),
            ("AppFontMdBold", SIZE_MD, "bold"),
            ("AppFontLg", SIZE_LG, "normal"),
            ("AppMono", SIZE_SM, "normal"),  # alias name; same family
        ):
            try:
                existing = tkfont.nametofont(n, root)
                existing.configure(family=FONT_FAMILY, size=sz, weight=weight)
            except Exception:
                tkfont.Font(
                    root=root, name=n,
                    family=FONT_FAMILY,
                    size=sz, weight=weight,
                )
        style = ttk.Style(root)
        style.configure(".", font=ui_font(SIZE_SM))
        style.configure("TButton", font=ui_font(SIZE_SM))
        style.configure("TLabel", font=ui_font(SIZE_SM))
        style.configure("TCheckbutton", font=ui_font(SIZE_SM))
        style.configure("TRadiobutton", font=ui_font(SIZE_SM))
        style.configure("TEntry", font=ui_font(SIZE_SM))
        style.configure("TCombobox", font=ui_font(SIZE_SM))
        style.configure("Heading.TLabel", font=ui_font(SIZE_MD, bold=True))
    except Exception:
        pass
    root.option_add("*Font", ui_font(SIZE_SM))
    root.option_add("*Text.Font", mono_font(SIZE_SM))
    root.option_add("*Entry.Font", ui_font(SIZE_SM))
    root.option_add("*Button.Font", ui_font(SIZE_SM))
    root.option_add("*Label.Font", ui_font(SIZE_SM))
    style_notebooks(root, size=SIZE_SM)
    _INITIALIZED = True
    return fonts(SIZE_SM)


def style_notebooks(root, size=None):
    """Pad Notebook tabs so main/sub labels are easier to separate."""
    size = SIZE_SM if size is None else size
    try:
        from tkinter import ttk
        style = ttk.Style(root)
        style.configure(
            "TNotebook.Tab",
            font=ui_font(size),
            padding=NOTEBOOK_TAB_PADDING,
        )
        style.configure("TNotebook", padding=NOTEBOOK_PADDING)
        try:
            style.map(
                "TNotebook.Tab",
                padding=[
                    ("selected", NOTEBOOK_TAB_PADDING_SELECTED),
                    ("!selected", NOTEBOOK_TAB_PADDING),
                ],
            )
        except Exception:
            pass
    except Exception:
        pass
