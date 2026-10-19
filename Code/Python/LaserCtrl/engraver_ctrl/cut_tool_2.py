import sys
import os
import tkinter as tk
from tkinter import ttk

# Ensure the parent folder (LaserCtrl) is on the path so that
# `import engraver_ctrl.xxx` works even when this script is run
# directly from inside the engraver_ctrl directory.
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from engraver_ctrl.tab_designer import DesignerTab
# ------- DPI FIX -------
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()
# -----------------------
from engraver_ctrl.tab_machine import MachineTab
from engraver_ctrl.tab_small_parts import SmallPartsTab
from engraver_ctrl.tab_parallel import ParallelTab
from engraver_ctrl.tab_simulate import TabSimulate

class CutToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Laser Cutting Tool v2 (GCODE Only)")
        self.font = ("Times New Roman", 11)

        self.ser = None  # shared serial object

        self.build_gui()

    def build_gui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both")

        # -------- Tabs --------
        self.tab_machine = MachineTab(
            notebook, self
        )
        self.tab_small_parts = SmallPartsTab(
            notebook, self
        )

        self.tab_parallel = ParallelTab(
            notebook, self
        )

        self.tab_custom = DesignerTab(
            notebook, self
        )

        self.tab_simulate = TabSimulate(
            notebook, self
        )


        notebook.add(self.tab_machine, text="Machine")
        notebook.add(self.tab_small_parts, text="Small parts")
        notebook.add(self.tab_parallel, text="Parallel")
        notebook.add(self.tab_custom, text="Custom")
        notebook.add(self.tab_simulate, text="Simulate")


if __name__ == "__main__":
    root = tk.Tk()
    app = CutToolApp(root)
    root.mainloop()
