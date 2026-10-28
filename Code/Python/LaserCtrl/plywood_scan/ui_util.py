"""
Tien ich GUI dung chung: bat DPI awareness tren Windows (het mo chu) va
he so scale cho cac kich thuoc tinh bang pixel.
"""
import sys

_SCALE = 1.0


def enable_dpi_awareness():
    """
    Goi TRUOC khi tao tk.Tk(). Tren Windows, neu khong bat thi Windows phong
    to bitmap cua cua so => chu bi mo tren man hinh scale 125% / 150%.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
    except Exception:
        return False
    try:
        # 1 = PROCESS_SYSTEM_DPI_AWARE (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return True
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Windows Vista+
        return True
    except Exception:
        return False


def init_scaling(root):
    """
    Tinh he so scale theo DPI that (96 dpi = 1.0). Font tinh theo point nen
    Tk tu scale; chi cac kich thuoc pixel (be rong panel, wraplength...) can
    nhan them he so nay qua ham px().
    """
    global _SCALE
    try:
        _SCALE = max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
    except Exception:
        _SCALE = 1.0
    return _SCALE


def px(n):
    """Doi kich thuoc pixel thiet ke (o 96 dpi) sang pixel thuc."""
    return int(round(n * _SCALE))


def fit_geometry(root, w, h):
    """Dat kich thuoc cua so (pixel thiet ke), khong vuot qua man hinh."""
    W = min(px(w), int(root.winfo_screenwidth() * 0.95))
    H = min(px(h), int(root.winfo_screenheight() * 0.9))
    root.geometry("%dx%d" % (W, H))


# ---------------------------------------------------------------------------
# Font dung chung cho ca 2 tool (1 ho font duy nhat)
# ---------------------------------------------------------------------------
FONT_FAMILY_PREF = ("Segoe UI", "DejaVu Sans", "Helvetica", "Arial")
MONO_FAMILY_PREF = ("Consolas", "DejaVu Sans Mono", "Courier New", "Courier")
FONT_FAMILY = "TkDefaultFont"
MONO_FAMILY = "TkFixedFont"


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


def fonts(size=11):
    """Tra ve (FONT, FONT_B, FONT_S, FONT_MONO, FONT_L) cung 1 ho font."""
    return ((FONT_FAMILY, size), (FONT_FAMILY, size, "bold"),
            (FONT_FAMILY, size - 2), (MONO_FAMILY, size - 2),
            (FONT_FAMILY, size + 1, "bold"))


def init_fonts(root, size=11):
    """
    Goi ngay sau tk.Tk(): chon ho font (Segoe UI neu co), dat lam mac dinh
    cho moi widget tk/ttk. Tra ve fonts(size).
    """
    global FONT_FAMILY, MONO_FAMILY
    FONT_FAMILY = _pick(root, FONT_FAMILY_PREF, "TkDefaultFont")
    MONO_FAMILY = _pick(root, MONO_FAMILY_PREF, "TkFixedFont")
    try:
        from tkinter import font as tkfont
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                     "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
                     "TkIconFont", "TkTooltipFont"):
            tkfont.nametofont(name, root).configure(family=FONT_FAMILY,
                                                    size=size)
        tkfont.nametofont("TkFixedFont", root).configure(family=MONO_FAMILY,
                                                         size=size - 2)
    except Exception:
        pass
    root.option_add("*Font", (FONT_FAMILY, size))
    return fonts(size)
