"""Validation panel for displaying graph diagnostics and selecting issues."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from app.app_state import AppState
from engine.validator import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    ValidationIssue,
    validate_workflow,
)


class ValidationPanel(ttk.Frame):
    """Side panel displaying validation issues and navigation."""

    def __init__(self, parent: tk.Widget, app_state: AppState, **kwargs) -> None:
        kwargs.setdefault("width", 280)
        super().__init__(parent, **kwargs)

        self.app_state = app_state
        self._current_issues: list[ValidationIssue] = []

        self._build_ui()
        self.app_state.add_listener("workflow_changed", lambda wf: self._on_workflow_changed())

    def _build_ui(self) -> None:
        # Header frame
        header_frame = ttk.Frame(self, padding=(10, 8))
        header_frame.pack(fill=tk.X, side=tk.TOP)

        lbl_title = ttk.Label(
            header_frame, text="Validation", font=("Segoe UI", 11, "bold")
        )
        lbl_title.pack(side=tk.LEFT)

        btn_run = ttk.Button(
            header_frame, text="🔍 Validate", command=self.run_validation
        )
        btn_run.pack(side=tk.RIGHT)

        # Status summary banner
        self.summary_frame = ttk.Frame(self, padding=(10, 4))
        self.summary_frame.pack(fill=tk.X)

        self.lbl_summary = ttk.Label(
            self.summary_frame,
            text="Click 'Validate' to check graph.",
            font=("Segoe UI", 9),
            foreground="#555555",
        )
        self.lbl_summary.pack(anchor=tk.W)

        # Issues Treeview
        tree_frame = ttk.Frame(self, padding=8)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("type", "message")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("type", text="Type", anchor=tk.W)
        self.tree.heading("message", text="Issue", anchor=tk.W)

        self.tree.column("type", width=75, minwidth=60)
        self.tree.column("message", width=180, minwidth=120)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_issue_selected)

        # Help hint
        hint_lbl = ttk.Label(
            self,
            text="Tip: Click an issue above to highlight the affected node or edge on the canvas.",
            font=("Segoe UI", 8),
            foreground="#777777",
            wraplength=250,
            padding=(10, 6),
        )
        hint_lbl.pack(fill=tk.X, side=tk.BOTTOM)

    def run_validation(self) -> None:
        """Execute validation against the current active workflow."""
        wf = self.app_state.current_workflow
        if not wf:
            self._current_issues = []
            self._update_display()
            return

        self._current_issues = validate_workflow(wf)
        self._update_display()

    def _update_display(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        errors_count = sum(1 for i in self._current_issues if i.severity == SEVERITY_ERROR)
        warnings_count = sum(1 for i in self._current_issues if i.severity == SEVERITY_WARNING)

        if not self._current_issues:
            self.lbl_summary.configure(
                text="✔ Graph is valid! No errors or warnings.",
                foreground="#2e7d32",
            )
        else:
            text = f"Issues: {errors_count} Errors, {warnings_count} Warnings"
            fg = "#d32f2f" if errors_count > 0 else "#f57f17"
            self.lbl_summary.configure(text=text, foreground=fg)

        for idx, issue in enumerate(self._current_issues):
            type_label = "❌ Error" if issue.severity == SEVERITY_ERROR else "⚠️ Warn"
            self.tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(type_label, f"[{issue.code}] {issue.message}"),
            )

    def _on_issue_selected(self, event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return

        idx = int(selection[0])
        if 0 <= idx < len(self._current_issues):
            issue = self._current_issues[idx]
            if issue.node_id:
                self.app_state.select_node(issue.node_id)
            elif issue.edge_id:
                self.app_state.select_edge(issue.edge_id)

    def _on_workflow_changed(self) -> None:
        # Clear or retain current issues according to policy
        if not self._current_issues:
            return
        # Keep issues displayed, user can click Validate to refresh
