#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSL Nesting launcher (compat).

Opens the DSL nesting panel only. Manual pieces UI has been removed;
use the unified app or this launcher for ADD-block nesting.

Requires: pip install ortools
Run: python rect_nesting_app.py
"""

from __future__ import annotations

import os
import sys
import tkinter as tk

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from common.ui import enable_dpi_awareness, init_fonts
from dsl_nesting.gui import build_dsl_nesting_panel


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    root.title("DSL Nesting")
    root.geometry("1280x820")
    root.minsize(980, 640)
    init_fonts(root, size=10)
    panel = build_dsl_nesting_panel(root)

    def on_close():
        if panel.is_busy():
            from tkinter import messagebox
            if not messagebox.askyesno(
                "Busy", "CP-SAT is still solving. Close anyway?"
            ):
                return
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
