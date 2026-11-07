from common.ui import enable_dpi_awareness, init_fonts
from dsl_nesting.gui import build_dsl_nesting_panel
import tkinter as tk
from tkinter import messagebox


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    root.title("DSL Nesting")
    root.geometry("1280x820")
    init_fonts(root, size=10)
    panel = build_dsl_nesting_panel(root)

    def on_close():
        if panel.is_busy() and not messagebox.askyesno(
            "Busy", "CP-SAT is still solving. Close anyway?"
        ):
            return
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
