from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from models.image_library import ImageLibrary
from models.workflow_store import WorkflowStore
from ui.images_tab import ImagesTab
from ui.workflows_tab import WorkflowsTab


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Auto Clicker")
        self.geometry("1100x640")
        self.minsize(900, 520)

        self.image_library = ImageLibrary()
        self.workflow_store = WorkflowStore()

        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.workflows_tab = WorkflowsTab(notebook, self.workflow_store, self.image_library)
        notebook.add(self.workflows_tab, text="Workflow")

        self.images_tab = ImagesTab(notebook, self.image_library)
        notebook.add(self.images_tab, text="Hình ảnh")

        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        notebook.select(self.workflows_tab)

    def _on_tab_changed(self, event: tk.Event) -> None:
        widget = event.widget
        selected = widget.nametowidget(widget.select())
        if selected is self.workflows_tab:
            self.workflows_tab.refresh_images()
        elif selected is self.images_tab:
            self.images_tab.refresh_list()
