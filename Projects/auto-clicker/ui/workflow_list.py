"""Workflow list view for managing workflows on disk."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from app.app_state import AppState
from storage.exceptions import StorageError
from storage.workflow_repository import WorkflowSummary
from ui.dialogs import (
    confirm_action,
    prompt_save_changes,
    prompt_text,
    show_error,
    show_info,
)


class WorkflowList(ttk.Frame):
    """View displaying available workflows with CRUD controls."""

    def __init__(
        self,
        parent: tk.Widget,
        app_state: AppState,
        on_open_workflow: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.app_state = app_state
        self.on_open_workflow = on_open_workflow
        self._summaries: dict[str, WorkflowSummary] = {}

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        # Header / Title
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=16, pady=(16, 8))

        lbl_title = ttk.Label(
            header_frame, text="Workflows", font=("Segoe UI", 16, "bold")
        )
        lbl_title.pack(side=tk.LEFT)

        # Action Buttons bar
        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill=tk.X, padx=16, pady=(0, 8))

        btn_new = ttk.Button(btn_bar, text="➕ New Workflow", command=self._on_new)
        btn_new.pack(side=tk.LEFT, padx=(0, 6))

        btn_open = ttk.Button(btn_bar, text="📂 Open", command=self._on_open)
        btn_open.pack(side=tk.LEFT, padx=(0, 6))

        btn_rename = ttk.Button(btn_bar, text="✏️ Rename", command=self._on_rename)
        btn_rename.pack(side=tk.LEFT, padx=(0, 6))

        btn_dup = ttk.Button(btn_bar, text="📋 Duplicate", command=self._on_duplicate)
        btn_dup.pack(side=tk.LEFT, padx=(0, 6))

        btn_del = ttk.Button(btn_bar, text="🗑️ Delete", command=self._on_delete)
        btn_del.pack(side=tk.LEFT, padx=(0, 6))

        btn_refresh = ttk.Button(btn_bar, text="🔄 Refresh", command=self.refresh)
        btn_refresh.pack(side=tk.RIGHT)

        # Treeview table
        columns = ("name", "description", "updated_at", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Name", anchor=tk.W)
        self.tree.heading("description", text="Description", anchor=tk.W)
        self.tree.heading("updated_at", text="Last Modified", anchor=tk.W)
        self.tree.heading("status", text="Status", anchor=tk.CENTER)

        self.tree.column("name", width=200, minwidth=120)
        self.tree.column("description", width=250, minwidth=150)
        self.tree.column("updated_at", width=180, minwidth=120)
        self.tree.column("status", width=90, minwidth=80, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0), pady=(0, 16))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 16), pady=(0, 16))

        self.tree.bind("<Double-Button-1>", lambda e: self._on_open())

    def refresh(self) -> None:
        """Scan directory and reload workflow list."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._summaries.clear()

        summaries = self.app_state.service.list_workflows()
        for s in summaries:
            item_id = str(s.file_path)
            self._summaries[item_id] = s
            status_text = "Corrupt ⚠️" if s.is_corrupted else "Ready"
            self.tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=(s.name, s.description, s.updated_at, status_text),
            )

    def _check_unsaved_changes_ok(self) -> bool:
        """If current workflow has unsaved changes, prompt user. Return False if cancelled."""
        if not self.app_state.is_dirty:
            return True

        current_wf = self.app_state.current_workflow
        wf_name = current_wf.workflow.name if current_wf else "Untitled"
        choice = prompt_save_changes(self, wf_name)

        if choice == "save":
            try:
                self.app_state.service.save_workflow()
                self.app_state.notify_workflow_saved()
                return True
            except Exception as err:
                show_error(self, "Save Failed", f"Could not save changes: {err}")
                return False
        elif choice == "discard":
            return True
        else:  # cancel
            return False

    def _get_selected_summary(self) -> Optional[WorkflowSummary]:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._summaries.get(selection[0])

    def _on_new(self) -> None:
        if not self._check_unsaved_changes_ok():
            return

        name = prompt_text(self, "New Workflow", "Enter workflow name:", "My Workflow")
        if not name or not name.strip():
            return

        try:
            self.app_state.service.create_workflow(name=name.strip())
            self.app_state.notify_workflow_loaded()
            self.refresh()
            self.on_open_workflow()
        except Exception as err:
            show_error(self, "Error", f"Failed to create workflow: {err}")

    def _on_open(self) -> None:
        summary = self._get_selected_summary()
        if not summary:
            show_info(self, "Selection Required", "Please select a workflow to open.")
            return

        if summary.is_corrupted:
            show_error(
                self,
                "Corrupted File",
                f"Cannot open '{summary.file_path.name}':\n{summary.error_message}",
            )
            return

        if not self._check_unsaved_changes_ok():
            return

        try:
            self.app_state.service.open_workflow(summary.file_path)
            self.app_state.notify_workflow_loaded()
            self.on_open_workflow()
        except Exception as err:
            show_error(self, "Open Failed", f"Failed to open workflow: {err}")

    def _on_rename(self) -> None:
        summary = self._get_selected_summary()
        if not summary:
            show_info(self, "Selection Required", "Please select a workflow to rename.")
            return

        if summary.is_corrupted:
            show_error(self, "Corrupted File", "Cannot rename a corrupted file.")
            return

        new_name = prompt_text(
            self, "Rename Workflow", "Enter new workflow name:", summary.name
        )
        if not new_name or not new_name.strip() or new_name == summary.name:
            return

        try:
            # If the selected workflow is currently open in editor:
            if (
                self.app_state.service.current_file_path
                and self.app_state.service.current_file_path.resolve()
                == summary.file_path.resolve()
            ):
                self.app_state.service.rename_workflow(new_name.strip())
                self.app_state.notify_workflow_saved()
            else:
                self.app_state.service.repository.rename(
                    summary.file_path, new_name.strip()
                )
            self.refresh()
        except StorageError as err:
            show_error(self, "Rename Error", str(err))

    def _on_duplicate(self) -> None:
        summary = self._get_selected_summary()
        if not summary:
            show_info(self, "Selection Required", "Please select a workflow to duplicate.")
            return

        if summary.is_corrupted:
            show_error(self, "Corrupted File", "Cannot duplicate a corrupted file.")
            return

        default_name = f"{summary.name} (Copy)"
        new_name = prompt_text(
            self, "Duplicate Workflow", "Enter name for duplicate:", default_name
        )
        if not new_name or not new_name.strip():
            return

        try:
            self.app_state.service.duplicate_workflow(summary.file_path, new_name.strip())
            self.refresh()
            show_info(self, "Success", f"Workflow duplicated as '{new_name.strip()}'.")
        except StorageError as err:
            show_error(self, "Duplicate Error", str(err))

    def _on_delete(self) -> None:
        summary = self._get_selected_summary()
        if not summary:
            show_info(self, "Selection Required", "Please select a workflow to delete.")
            return

        if not confirm_action(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete '{summary.name}'?\nFile: {summary.file_path.name}",
        ):
            return

        try:
            self.app_state.service.delete_workflow(summary.file_path)
            self.refresh()
        except Exception as err:
            show_error(self, "Delete Failed", f"Failed to delete workflow: {err}")
