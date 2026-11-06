"""
Frame Toolkit - unified launcher

Combines all 5 standalone tools into one window using tabs (ttk.Notebook).
Each tool's own code is reused as-is (imported as a module) -- this file
only wires them together, it does not duplicate any logic.

Place this file in the SAME folder as all of the following:
  joint_nesting_gui.py   + joint_nesting_solver.py   (mối nối / connector tool)
  beam_dsl_gui.py        + beam_dsl_core.py          (thanh dầm / beam stick tool)
  rail_skeleton_gui.py   + rail_skeleton_core.py     (khung xương / skeleton tool)
  rail_cutlist_gui.py                                (dầm ngang / rail cut-list tool)
  box_gui.py            + box_core.py               (hộp / box frame tool)

Run locally with: python main_app.py
Requires: pip install ortools   (only needed for the "Mối nối" tab)
"""

import sys
import os
import tkinter as tk
from tkinter import ttk

# Ensure the parent folder (LaserCtrl) is on the path so that
# `import frame_creator.xxx` works even when this script is run
# directly from inside the frame_creator directory.
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


# Custom font -- change these two to adjust the whole app's font in one place
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 10


def add_tab(notebook, title, build_fn):
    """Create a tab frame, hand it to build_fn(frame). If the tool fails to
    load (e.g. a missing dependency like ortools), show the error inside
    that tab instead of crashing the whole app."""
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=title)
    try:
        build_fn(frame)
    except Exception as e:
        ttk.Label(frame, text=f"Failed to load this tool:\n{e}",
                  foreground="red", wraplength=500, justify="left"
                  ).pack(padx=20, pady=20, anchor="nw")


def main():
    try:
        from common.ui import enable_dpi_awareness, init_fonts
        enable_dpi_awareness()
    except Exception:
        enable_dpi_awareness = None
        init_fonts = None
    root = tk.Tk()
    if init_fonts is not None:
        init_fonts(root, size=FONT_SIZE)

    root.title("Frame Toolkit")
    root.geometry("1150x780")

    default_font = (FONT_FAMILY, FONT_SIZE)
    root.option_add("*Font", default_font)
    style = ttk.Style(root)
    style.configure(".", font=default_font)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    def build_joint(frame):
        import frame_creator.joint_nesting_gui as m
        m.JointNestingApp(frame)

    def build_beam(frame):
        import frame_creator.beam_dsl_gui as m
        m.BeamDslApp(frame)

    def build_skeleton(frame):
        import frame_creator.rail_skeleton_gui as m
        m.SkeletonApp(frame)

    def build_railcut(frame):
        import frame_creator.rail_cutlist_gui as m
        m.RailDslApp(frame)

    def build_box(frame):
        import frame_creator.box_gui as m
        m.BoxApp(frame)

    add_tab(notebook, "Joint", build_joint)
    add_tab(notebook, "Beam", build_beam)
    add_tab(notebook, "Skeleton", build_skeleton)
    add_tab(notebook, "Rail cut-list", build_railcut)
    add_tab(notebook, "Box", build_box)

    root.mainloop()


if __name__ == "__main__":
    main()
