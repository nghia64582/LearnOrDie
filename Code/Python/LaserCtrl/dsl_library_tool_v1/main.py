"""Compat launcher for the DSL Library tool.

Prefer: python -m dsl_library_tool  or  the unified laser_app.py
This script remains for older shortcuts.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from common.ui import enable_dpi_awareness, init_fonts
from dsl_library_tool.gui import build_dsl_library_panel


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    root.title("DSL Library Manager")
    root.geometry("1250x780")
    root.minsize(1000, 650)
    init_fonts(root, size=10)
    build_dsl_library_panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
