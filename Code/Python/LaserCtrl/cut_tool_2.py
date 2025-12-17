import tkinter as tk
from tkinter import ttk

# ------- DPI FIX -------
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()
# -----------------------

from tab_machine import MachineTab
from tab_small_parts import SmallPartsTab
from tab_parallel import ParallelTab

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

        notebook.add(self.tab_machine, text="Machine")
        notebook.add(self.tab_small_parts, text="Small parts")
        notebook.add(self.tab_parallel, text="Parallel")


if __name__ == "__main__":
    root = tk.Tk()
    app = CutToolApp(root)
    root.mainloop()
