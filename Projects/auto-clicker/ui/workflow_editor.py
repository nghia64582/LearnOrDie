"""Workflow editor view combining canvas, toolbox, and inspector."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from app.app_state import AppState
from models.node import Node, Position
from storage.exceptions import StorageError
from ui.dialogs import prompt_save_changes, prompt_text, show_error, show_info
from ui.node_toolbox import NodeToolbox
from ui.properties_panel import PropertiesPanel
from ui.workflow_canvas import NODE_WIDTH, WorkflowCanvas


class WorkflowEditor(ttk.Frame):
    """Container frame hosting toolbar, toolbox, canvas, and status bar."""

    def __init__(
        self,
        parent: tk.Widget,
        app_state: AppState,
        on_back_to_list: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.app_state = app_state
        self.on_back_to_list = on_back_to_list

        self._build_ui()
        self.app_state.add_listener("workflow_changed", self._on_workflow_changed)
        self.app_state.add_listener("dirty_changed", self._on_dirty_changed)
        self.app_state.add_listener("selection_changed", self._on_selection_changed)

    def _build_ui(self) -> None:
        # Top Toolbar
        self.toolbar = ttk.Frame(self, padding=(8, 6))
        self.toolbar.pack(fill=tk.X, side=tk.TOP)

        btn_back = ttk.Button(self.toolbar, text="← Workflows", command=self._on_back)
        btn_back.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_title = ttk.Label(
            self.toolbar, text="Untitled", font=("Segoe UI", 12, "bold")
        )
        self.lbl_title.pack(side=tk.LEFT, padx=(0, 6))

        btn_rename_title = ttk.Button(
            self.toolbar, text="✏️", width=3, command=self._on_rename_current
        )
        btn_rename_title.pack(side=tk.LEFT, padx=(0, 15))

        btn_save = ttk.Button(self.toolbar, text="💾 Save", command=self._on_save)
        btn_save.pack(side=tk.LEFT, padx=(0, 6))

        btn_save_as = ttk.Button(self.toolbar, text="💾 Save As...", command=self._on_save_as)
        btn_save_as.pack(side=tk.LEFT, padx=(0, 15))

        # View controls
        btn_zoom_in = ttk.Button(self.toolbar, text="🔍+", width=4, command=self._on_zoom_in)
        btn_zoom_in.pack(side=tk.LEFT, padx=(0, 2))

        btn_zoom_out = ttk.Button(self.toolbar, text="🔍-", width=4, command=self._on_zoom_out)
        btn_zoom_out.pack(side=tk.LEFT, padx=(0, 2))

        btn_reset_view = ttk.Button(self.toolbar, text="Reset View", command=self._on_reset_view)
        btn_reset_view.pack(side=tk.LEFT, padx=(0, 10))

        # Bottom Status Bar
        self.status_bar = ttk.Frame(self, relief=tk.SUNKEN, padding=(8, 4))
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status_selection = ttk.Label(self.status_bar, text="No selection")
        self.lbl_status_selection.pack(side=tk.LEFT)

        self.lbl_status_dirty = ttk.Label(self.status_bar, text="✔ Saved", foreground="#2e7d32")
        self.lbl_status_dirty.pack(side=tk.RIGHT, padx=10)

        self.lbl_status_stats = ttk.Label(self.status_bar, text="Nodes: 0 | Edges: 0")
        self.lbl_status_stats.pack(side=tk.RIGHT, padx=10)

        self.lbl_status_zoom = ttk.Label(self.status_bar, text="Zoom: 100%")
        self.lbl_status_zoom.pack(side=tk.RIGHT, padx=10)

        # Central Paned Area (Toolbox + Canvas)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        self.toolbox = NodeToolbox(
            paned,
            app_state=self.app_state,
            on_add_node_center=self._add_node_to_center,
            width=200,
        )
        paned.add(self.toolbox, weight=0)

        self.canvas = WorkflowCanvas(paned, app_state=self.app_state)
        paned.add(self.canvas, weight=1)

        self.properties_panel = PropertiesPanel(
            paned,
            app_state=self.app_state,
            width=280,
        )
        paned.add(self.properties_panel, weight=0)

    # ================= Actions =================

    def _add_node_to_center(self, node_type: str) -> None:
        """Add node at the center of the current canvas viewport."""
        if not self.app_state.current_workflow:
            return

        cw = self.canvas.winfo_width() / 2.0
        ch = self.canvas.winfo_height() / 2.0
        lx, ly = self.canvas.screen_to_logic(cw, ch)
        lx -= NODE_WIDTH / 2.0
        ly -= 35.0

        new_node = Node.create(node_type, position=Position(round(lx, 1), round(ly, 1)))
        self.app_state.current_workflow.add_node(new_node)
        self.app_state.select_node(new_node.id)
        self.app_state.notify_workflow_modified()
        self.canvas.repaint()

    def _on_save(self) -> None:
        try:
            saved_path = self.app_state.service.save_workflow()
            self.app_state.notify_workflow_saved()
            self.lbl_title.configure(text=self.app_state.current_workflow.workflow.name)
        except Exception as err:
            show_error(self, "Save Failed", f"Failed to save workflow:\n{err}")

    def _on_save_as(self) -> None:
        wf = self.app_state.current_workflow
        if not wf:
            return

        new_name = prompt_text(
            self, "Save As", "Enter new workflow name:", f"{wf.workflow.name} Copy"
        )
        if not new_name or not new_name.strip():
            return

        try:
            self.app_state.service.save_as(new_name.strip())
            self.app_state.notify_workflow_saved()
            self.lbl_title.configure(text=self.app_state.current_workflow.workflow.name)
            show_info(self, "Saved", f"Workflow saved as '{new_name.strip()}'.")
        except StorageError as err:
            show_error(self, "Save As Failed", str(err))

    def _on_rename_current(self) -> None:
        wf = self.app_state.current_workflow
        if not wf:
            return

        new_name = prompt_text(
            self, "Rename Workflow", "Enter new workflow name:", wf.workflow.name
        )
        if not new_name or not new_name.strip() or new_name == wf.workflow.name:
            return

        try:
            self.app_state.service.rename_workflow(new_name.strip())
            self.app_state.notify_workflow_saved()
            self.lbl_title.configure(text=self.app_state.current_workflow.workflow.name)
        except StorageError as err:
            show_error(self, "Rename Failed", str(err))

    def _on_back(self) -> None:
        if self.app_state.is_dirty:
            wf_name = (
                self.app_state.current_workflow.workflow.name
                if self.app_state.current_workflow
                else "Untitled"
            )
            choice = prompt_save_changes(self, wf_name)
            if choice == "save":
                try:
                    self.app_state.service.save_workflow()
                    self.app_state.notify_workflow_saved()
                except Exception as err:
                    show_error(self, "Save Failed", f"Could not save changes: {err}")
                    return
            elif choice == "cancel":
                return

        self.on_back_to_list()

    def _on_zoom_in(self) -> None:
        self.canvas.zoom_in()
        self._update_zoom_label()

    def _on_zoom_out(self) -> None:
        self.canvas.zoom_out()
        self._update_zoom_label()

    def _on_reset_view(self) -> None:
        self.canvas.reset_view()
        self._update_zoom_label()

    def _update_zoom_label(self) -> None:
        self.lbl_status_zoom.configure(text=f"Zoom: {int(self.canvas.zoom * 100)}%")

    # ================= State Change Handlers =================

    def _on_workflow_changed(self, workflow: Optional[Workflow]) -> None:
        if workflow:
            name = workflow.workflow.name
            dirty_star = " *" if self.app_state.is_dirty else ""
            self.lbl_title.configure(text=f"{name}{dirty_star}")
            node_count = len(workflow.nodes)
            edge_count = len(workflow.edges)
            self.lbl_status_stats.configure(
                text=f"Nodes: {node_count} | Edges: {edge_count}"
            )
        else:
            self.lbl_title.configure(text="No Workflow")
            self.lbl_status_stats.configure(text="Nodes: 0 | Edges: 0")

        self._update_zoom_label()
        self.canvas.repaint()

    def _on_dirty_changed(self, is_dirty: bool) -> None:
        if self.app_state.current_workflow:
            name = self.app_state.current_workflow.workflow.name
            dirty_star = " *" if is_dirty else ""
            self.lbl_title.configure(text=f"{name}{dirty_star}")

        if is_dirty:
            self.lbl_status_dirty.configure(
                text="● Unsaved changes", foreground="#d32f2f"
            )
        else:
            self.lbl_status_dirty.configure(text="✔ Saved", foreground="#2e7d32")

    def _on_selection_changed(
        self, node_id: Optional[str], edge_id: Optional[str]
    ) -> None:
        if node_id and self.app_state.current_workflow:
            node = self.app_state.current_workflow.get_node(node_id)
            if node:
                self.lbl_status_selection.configure(
                    text=f"Selected Node: {node.name} ({node.type}) [ID: {node.id[:8]}...]"
                )
                return
        elif edge_id and self.app_state.current_workflow:
            edge = self.app_state.current_workflow.get_edge(edge_id)
            if edge:
                self.lbl_status_selection.configure(
                    text=f"Selected Edge: {edge.source}:{edge.source_port} → {edge.target}:{edge.target_port}"
                )
                return

        self.lbl_status_selection.configure(text="No selection")
