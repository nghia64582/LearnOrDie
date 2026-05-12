import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter.font import Font

from api import (
    create_note,
    get_notes,
    get_notes_by_tags,
    get_note_by_id,
    edit_note
)

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()
# -----------------------
# Global config
# -----------------------
APP_WIDTH = 900
APP_HEIGHT = 600

FONT_FAMILY = "JetBrains Mono"
FONT_SIZE = 11


# -----------------------
# Helper
# -----------------------
def parse_tags(tag_string: str):
    return [t.strip() for t in tag_string.split(",") if t.strip()]


# -----------------------
# App
# -----------------------
class NoteApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Note App")
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")

        # global font
        self.default_font = Font(family=FONT_FAMILY, size=FONT_SIZE)
        self.option_add("*Font", self.default_font)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self._create_tabs()

    # -----------------------
    # Tabs
    # -----------------------
    def _create_tabs(self):
        self.tab_create_note()
        self.tab_list_notes()
        self.tab_list_by_tags()
        self.tab_get_by_id()
        self.tab_edit_note()

    # -----------------------
    # Tab 1: Create note
    # -----------------------
    def tab_create_note(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Create Note")

        ttk.Label(tab, text="Topic ID").pack(anchor="w")
        topic_entry = ttk.Entry(tab)
        topic_entry.pack(fill="x")

        ttk.Label(tab, text="Tags (comma separated)").pack(anchor="w")
        tags_entry = ttk.Entry(tab)
        tags_entry.pack(fill="x")

        ttk.Label(tab, text="Content").pack(anchor="w")
        content_text = scrolledtext.ScrolledText(tab, height=15)
        content_text.pack(fill="both", expand=True)

        def submit():
            try:
                topic_id = topic_entry.get().strip()
                topic_id = int(topic_id) if topic_id else None

                tags = parse_tags(tags_entry.get())
                content = content_text.get("1.0", "end").strip()

                if not content:
                    messagebox.show_error("Error", "Content is required")
                    return

                result = create_note(
                    content=content,
                    topic_id=topic_id,
                    tags=tags
                )
                messagebox.showinfo("Success", f"Created note ID: {result['id']}")

                content_text.delete("1.0", "end")
                tags_entry.delete(0, "end")
                topic_entry.delete(0, "end")

            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(tab, text="Create", command=submit).pack(pady=10)

    # -----------------------
    # Tab 2: List notes
    # -----------------------
    def tab_list_notes(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="List Notes")

        control = ttk.Frame(tab)
        control.pack(fill="x")

        ttk.Label(control, text="Offset").pack(side="left")
        offset_entry = ttk.Entry(control, width=5)
        offset_entry.insert(0, "0")
        offset_entry.pack(side="left", padx=5)

        ttk.Label(control, text="Limit").pack(side="left")
        limit_entry = ttk.Entry(control, width=5)
        limit_entry.insert(0, "10")
        limit_entry.pack(side="left", padx=5)

        output = scrolledtext.ScrolledText(tab)
        output.pack(fill="both", expand=True)

        def load():
            try:
                offset = int(offset_entry.get())
                limit = int(limit_entry.get())

                notes = get_notes(offset, limit)
                output.delete("1.0", "end")

                for n in notes:
                    output.insert(
                        "end",
                        f"ID: {n['id']} | Updated: {n['updated_at']}\n"
                    )
                    output.insert("end", "-" * 50 + "\n")

            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(control, text="Load", command=load).pack(side="left", padx=10)

    # -----------------------
    # Tab 3: List by tags
    # -----------------------
    def tab_list_by_tags(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Notes by Tags")

        control = ttk.Frame(tab)
        control.pack(fill="x")

        ttk.Label(control, text="Tags").pack(side="left")
        tags_entry = ttk.Entry(control, width=30)
        tags_entry.pack(side="left", padx=5)

        ttk.Label(control, text="Offset").pack(side="left")
        offset_entry = ttk.Entry(control, width=5)
        offset_entry.insert(0, "0")
        offset_entry.pack(side="left")

        ttk.Label(control, text="Limit").pack(side="left")
        limit_entry = ttk.Entry(control, width=5)
        limit_entry.insert(0, "10")
        limit_entry.pack(side="left")

        output = scrolledtext.ScrolledText(tab)
        output.pack(fill="both", expand=True)

        def load():
            try:
                tags = parse_tags(tags_entry.get())
                offset = int(offset_entry.get())
                limit = int(limit_entry.get())

                notes = get_notes_by_tags(tags, offset, limit)
                output.delete("1.0", "end")

                for n in notes:
                    output.insert(
                        "end",
                        f"ID: {n['id']} | Updated: {n['updated_at']}\n"
                    )
                    output.insert("end", "-" * 50 + "\n")

            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(control, text="Load", command=load).pack(side="left", padx=10)

    # -----------------------
    # Tab 4: Get note by ID
    # -----------------------
    def tab_get_by_id(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Get Note by ID")

        ttk.Label(tab, text="Note ID").pack(anchor="w")
        id_entry = ttk.Entry(tab)
        id_entry.pack(fill="x")

        output = scrolledtext.ScrolledText(tab)
        output.pack(fill="both", expand=True)

        def load():
            try:
                note_id = int(id_entry.get())
                note = get_note_by_id(note_id)

                output.delete("1.0", "end")
                output.insert("end", f"ID: {note['id']}\n")
                output.insert("end", f"Topic: {note['topic_id']}\n")
                output.insert("end", f"Tags: {', '.join(t['name'] for t in note['tags'])}\n")
                output.insert("end", "-" * 40 + "\n")
                output.insert("end", note['content'])

            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(tab, text="Load", command=load).pack(pady=5)

    # -----------------------
    # Tab 5: Edit note
    # -----------------------
    def tab_edit_note(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Edit Note")

        ttk.Label(tab, text="Note ID").pack(anchor="w")
        id_entry = ttk.Entry(tab)
        id_entry.pack(fill="x")

        ttk.Label(tab, text="Topic ID").pack(anchor="w")
        topic_entry = ttk.Entry(tab)
        topic_entry.pack(fill="x")

        ttk.Label(tab, text="Tags").pack(anchor="w")
        tags_entry = ttk.Entry(tab)
        tags_entry.pack(fill="x")

        ttk.Label(tab, text="Content").pack(anchor="w")
        content_text = scrolledtext.ScrolledText(tab, height=15)
        content_text.pack(fill="both", expand=True)

        def submit():
            try:
                note_id = int(id_entry.get())
                topic_id = topic_entry.get().strip()
                topic_id = int(topic_id) if topic_id else None

                tags = parse_tags(tags_entry.get())
                content = content_text.get("1.0", "end").strip()

                edit_note(
                    note_id=note_id,
                    content=content,
                    topic_id=topic_id,
                    tags=tags
                )

                messagebox.showinfo("Success", "Note updated")

            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(tab, text="Update", command=submit).pack(pady=10)


# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app = NoteApp()
    app.mainloop()
