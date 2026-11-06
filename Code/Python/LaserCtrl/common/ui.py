"""Shared DPI + font helpers (Segoe UI 10 by default)."""

import sys

_SCALE = 1.0

FONT_FAMILY_PREF = ("Segoe UI", "DejaVu Sans", "Helvetica", "Arial")
MONO_FAMILY_PREF = ("Consolas", "DejaVu Sans Mono", "Courier New", "Courier")
FONT_FAMILY = "TkDefaultFont"
MONO_FAMILY = "TkFixedFont"


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
    return default


def fonts(size=10):
    return (
        (FONT_FAMILY, size),
        (FONT_FAMILY, size, "bold"),
        (FONT_FAMILY, size - 2),
        (MONO_FAMILY, size - 2),
        (FONT_FAMILY, size + 1, "bold"),
    )


def init_fonts(root, size=10):
    """Pick Segoe UI when available and set as the app-wide default."""
    global FONT_FAMILY, MONO_FAMILY
    FONT_FAMILY = _pick(root, FONT_FAMILY_PREF, "TkDefaultFont")
    MONO_FAMILY = _pick(root, MONO_FAMILY_PREF, "TkFixedFont")
    try:
        from tkinter import font as tkfont
        from tkinter import ttk
        for name in (
            "TkDefaultFont", "TkTextFont", "TkMenuFont",
            "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
            "TkIconFont", "TkTooltipFont",
        ):
            tkfont.nametofont(name, root).configure(family=FONT_FAMILY, size=size)
        tkfont.nametofont("TkFixedFont", root).configure(
            family=MONO_FAMILY, size=max(size - 2, 8)
        )
        style = ttk.Style(root)
        style.configure(".", font=(FONT_FAMILY, size))
    except Exception:
        pass
    root.option_add("*Font", (FONT_FAMILY, size))
    return fonts(size)
