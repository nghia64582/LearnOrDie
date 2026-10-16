"""Main application window and view navigation."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from app.app_state import AppState
from services.workflow_service import WorkflowService
from storage.workflow_repository import WorkflowRepository
from ui.dialogs import prompt_save_changes, show_error
from ui.workflow_editor import WorkflowEditor
from ui.workflow_list import WorkflowList


class MainWindow(tk.Tk):
    """Root application window."""

    def __init__(self, workflows_dir: Path | str = "data/workflows") -> None:
        super().__init__()

        self.title("Workflow Graph Editor")
        self.geometry("1150x720")
        self.minsize(850, 550)

        # Style configuration
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Service & State initialization
        self.repository = WorkflowRepository(workflows_dir)
        self.repository.ensure_sample_workflow()
        self.service = WorkflowService(self.repository)
        self.app_state = AppState(self.service)

        # Container for swappable views
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.list_view = WorkflowList(
            self.container,
            app_state=self.app_state,
            on_open_workflow=self.show_editor,
        )
        self.editor_view = WorkflowEditor(
            self.container,
            app_state=self.app_state,
            on_back_to_list=self.show_list,
        )

        # Listen to state changes to update window title
        self.app_state.add_listener("workflow_changed", lambda wf: self._update_title())
        self.app_state.add_listener("dirty_changed", lambda d: self._update_title())

        # Global shortcuts
        self.bind("<Control-n>", lambda e: self.list_view._on_new())
        self.bind("<Control-N>", lambda e: self.list_view._on_new())
        self.bind("<Control-w>", lambda e: self._on_close_tab())
        self.bind("<Control-W>", lambda e: self._on_close_tab())

        # Start with list view
        self.show_list()

        # Handle window closing with unsaved changes prompt
        self.protocol("WM_DELETE_WINDOW", self._on_close_window)

    def _update_title(self) -> None:
        """Update window title with active workflow name and dirty star."""
        if self.app_state.current_workflow:
            wf_name = self.app_state.current_workflow.workflow.name
            dirty_star = " *" if self.app_state.is_dirty else ""
            self.title(f"Workflow Graph Editor — {wf_name}{dirty_star}")
        else:
            self.title("Workflow Graph Editor")

    def _on_close_tab(self) -> None:
        """Handle Ctrl+W shortcut to return to list."""
        if self.editor_view.winfo_ismapped():
            self.editor_view._on_back()

    def show_list(self) -> None:
        """Switch view to workflow list."""
        self.editor_view.pack_forget()
        self.list_view.pack(fill=tk.BOTH, expand=True)
        self.list_view.refresh()

    def show_editor(self) -> None:
        """Switch view to workflow editor."""
        self.list_view.pack_forget()
        self.editor_view.pack(fill=tk.BOTH, expand=True)
        self.editor_view.canvas.repaint()

    def _on_close_window(self) -> None:
        """Intercept window close to check for unsaved changes."""
        if self.app_state.is_dirty:
            wf_name = (
                self.app_state.current_workflow.workflow.name
                if self.app_state.current_workflow
                else "Untitled"
            )
            choice = prompt_save_changes(self, wf_name)
            if choice == "save":
                try:
                    self.service.save_workflow()
                except Exception as err:
                    show_error(self, "Save Failed", f"Could not save changes: {err}")
                    return
            elif choice == "cancel":
                return

        self.destroy()
