from dsl_library_tool.gui import build_dsl_library_panel
from common.ui import enable_dpi_awareness, init_fonts
import tkinter as tk


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
