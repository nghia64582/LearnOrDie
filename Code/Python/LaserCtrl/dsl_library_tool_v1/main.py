import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from dsl_library import DSLLibrary
from dsl_parser import parse_dsl
from dsl_canvas import DSLCanvas

import ctypes
import sys

def _enable_dpi_awareness():
    """Bật DPI awareness trên Windows để chữ không bị mờ (font blur) khi
    màn hình chạy tỉ lệ scale > 100%. Không có tác dụng (và không lỗi)
    trên macOS/Linux."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_enable_dpi_awareness()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DSL Library Manager v1")
        self.geometry("1250x780")
        self.minsize(1000, 650)

        self.library_path = Path(__file__).parent / "dsl_library"
        self.library = DSLLibrary(self.library_path)
        self.current_file = None
        self.dirty = False

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="DSL Library:").pack(side="left")
        self.folder_var = tk.StringVar(value=str(self.library_path))
        ttk.Entry(top, textvariable=self.folder_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="Choose Folder", command=self.choose_folder).pack(side="left")
        ttk.Button(top, text="New DSL", command=self.new_dsl).pack(side="left", padx=(6, 0))

        main = ttk.Panedwindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(main, padding=5)
        right = ttk.Frame(main, padding=5)
        main.add(left, weight=1)
        main.add(right, weight=4)

        ttk.Label(left, text="DSL Files").pack(anchor="w")
        self.search_var = tk.StringVar()
        search = ttk.Entry(left, textvariable=self.search_var)
        search.pack(fill="x", pady=(4, 6))
        search.bind("<KeyRelease>", lambda e: self.refresh_list())

        self.listbox = tk.Listbox(left, activestyle="dotbox")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Refresh", command=self.refresh_list).pack(side="left", fill="x", expand=True)
        ttk.Button(btns, text="Delete", command=self.delete_dsl).pack(side="left", fill="x", expand=True, padx=(5, 0))

        editor = ttk.Frame(right)
        editor.pack(fill="x")

        ttk.Label(editor, text="Name").grid(row=0, column=0, sticky="w", pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(editor, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", padx=6, pady=2)

        ttk.Label(editor, text="Description").grid(row=1, column=0, sticky="nw", pady=2)
        self.desc_var = tk.StringVar()
        ttk.Entry(editor, textvariable=self.desc_var).grid(row=1, column=1, sticky="ew", padx=6, pady=2)

        editor.columnconfigure(1, weight=1)

        ttk.Label(right, text="DSL").pack(anchor="w", pady=(8, 3))
        self.dsl_text = tk.Text(right, height=13, undo=True, font=("Consolas", 10))
        self.dsl_text.pack(fill="x")
        self.dsl_text.bind("<<Modified>>", self.on_text_modified)

        actions = ttk.Frame(right)
        actions.pack(fill="x", pady=6)
        ttk.Button(actions, text="Save", command=self.save_dsl).pack(side="left")
        ttk.Button(actions, text="Preview", command=self.preview).pack(side="left", padx=5)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(actions, textvariable=self.status_var).pack(side="right")

        ttk.Label(right, text="Preview").pack(anchor="w")
        self.canvas = DSLCanvas(right)
        self.canvas.pack(fill="both", expand=True, pady=(3, 0))

    def choose_folder(self):
        p = filedialog.askdirectory(initialdir=self.library_path)
        if not p:
            return
        self.library_path = Path(p)
        self.folder_var.set(str(self.library_path))
        self.library = DSLLibrary(self.library_path)
        self.current_file = None
        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, "end")
        q = self.search_var.get().lower().strip()
        for p in self.library.list_files():
            data = self.library.load(p)
            if q and q not in data["name"].lower() and q not in data["description"].lower():
                continue
            self.listbox.insert("end", data["name"])

    def on_select(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        names = []
        q = self.search_var.get().lower().strip()
        for p in self.library.list_files():
            data = self.library.load(p)
            if q and q not in data["name"].lower() and q not in data["description"].lower():
                continue
            names.append(p)
        if sel[0] >= len(names):
            return
        self.load_file(names[sel[0]])

    def load_file(self, path):
        data = self.library.load(path)
        self.current_file = path
        self.name_var.set(data["name"])
        self.desc_var.set(data["description"])
        self.dsl_text.delete("1.0", "end")
        self.dsl_text.insert("1.0", data["dsl"])
        self.dsl_text.edit_modified(False)
        self.dirty = False
        self.preview()

    def new_dsl(self):
        self.current_file = None
        self.name_var.set("New DSL")
        self.desc_var.set("")
        self.dsl_text.delete("1.0", "end")
        self.dsl_text.insert("1.0", "# Enter DSL here\n")
        self.dsl_text.edit_modified(False)
        self.dirty = True
        self.canvas.clear()
        self.status_var.set("New DSL")

    def save_dsl(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Save", "Name cannot be empty.")
            return

        if self.current_file is None:
            filename = self.library.safe_filename(name)
            self.current_file = self.library.path / filename

        dsl = self.dsl_text.get("1.0", "end-1c")
        result = parse_dsl(dsl)
        if result.errors:
            msg = "\n".join(f"Line {e.line}: {e.message}" for e in result.errors[:8])
            if not messagebox.askyesno("DSL has errors", msg + "\n\nSave anyway?"):
                return

        self.library.save(
            self.current_file,
            name,
            self.desc_var.get().strip(),
            dsl,
        )
        self.dirty = False
        self.dsl_text.edit_modified(False)
        self.status_var.set(f"Saved: {self.current_file.name}")
        self.refresh_list()

    def delete_dsl(self):
        if self.current_file is None:
            return
        if not messagebox.askyesno("Delete", f"Delete {self.current_file.name}?"):
            return
        self.library.delete(self.current_file)
        self.current_file = None
        self.new_dsl()
        self.refresh_list()

    def on_text_modified(self, _event=None):
        if self.dsl_text.edit_modified():
            self.dirty = True
            self.dsl_text.edit_modified(False)
            self.preview()

    def preview(self):
        result = parse_dsl(self.dsl_text.get("1.0", "end-1c"))
        self.canvas.render(result)
        if result.errors:
            self.status_var.set(f"DSL errors: {len(result.errors)}")
        else:
            self.status_var.set(f"OK - {len(result.segments)} segments")


if __name__ == "__main__":
    App().mainloop()
