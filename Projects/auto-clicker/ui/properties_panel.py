"""Properties panel for inspecting and editing selected nodes, edges, or workflow."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from app.app_state import AppState
from models.edge import Edge
from models.node import Node
from models.node_definitions import (
    ParameterDefinition,
    get_node_definition,
)
from ui.dialogs import confirm_action


class PropertiesPanel(ttk.Frame):
    """Inspector panel displaying properties of the currently selected element."""

    def __init__(self, parent: tk.Widget, app_state: AppState, **kwargs) -> None:
        kwargs.setdefault("width", 280)
        super().__init__(parent, **kwargs)

        self.app_state = app_state
        self._current_node_id: Optional[str] = None
        self._current_edge_id: Optional[str] = None
        self._param_vars: dict[str, tk.Variable] = {}
        self._is_updating_ui: bool = False

        self._build_container()
        self.app_state.add_listener("selection_changed", self._on_selection_changed)
        self.app_state.add_listener("workflow_changed", self._on_workflow_changed)

        self.refresh()

    def _build_container(self) -> None:
        # Header title
        self.header_frame = ttk.Frame(self, padding=(10, 8))
        self.header_frame.pack(fill=tk.X, side=tk.TOP)

        self.lbl_header = ttk.Label(
            self.header_frame, text="Properties", font=("Segoe UI", 11, "bold")
        )
        self.lbl_header.pack(side=tk.LEFT)

        # Scrollable content frame
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg="#fcfcfc")
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, padding=10)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _clear_content(self) -> None:
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self._param_vars.clear()

    def refresh(self) -> None:
        """Re-render inspector depending on what is selected."""
        self._is_updating_ui = True
        try:
            self._clear_content()

            node = self.app_state.get_selected_node()
            edge = self.app_state.get_selected_edge()

            if node:
                self._render_node_properties(node)
            elif edge:
                self._render_edge_properties(edge)
            else:
                self._render_workflow_properties()
        finally:
            self._is_updating_ui = False

    # ================= Node Properties =================

    def _render_node_properties(self, node: Node) -> None:
        self.lbl_header.configure(text=f"Node: {node.type}")

        # General Section
        gen_frame = ttk.LabelFrame(self.scrollable_frame, text="General", padding=8)
        gen_frame.pack(fill=tk.X, pady=(0, 10))

        # Node ID (readonly)
        ttk.Label(gen_frame, text="Node ID:", font=("Segoe UI", 8, "bold")).pack(
            anchor=tk.W
        )
        id_lbl = ttk.Label(
            gen_frame,
            text=node.id,
            font=("Segoe UI", 8),
            foreground="#666666",
            wraplength=230,
        )
        id_lbl.pack(anchor=tk.W, pady=(0, 6))

        # Node Name (editable)
        ttk.Label(gen_frame, text="Name:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.name_var = tk.StringVar(value=node.name)
        name_entry = ttk.Entry(gen_frame, textvariable=self.name_var)
        name_entry.pack(fill=tk.X, pady=(2, 6))
        name_entry.bind("<FocusOut>", lambda e: self._on_name_commit(node))
        name_entry.bind("<Return>", lambda e: self._on_name_commit(node))

        # Parameters Section
        defn = get_node_definition(node.type)
        if defn.parameters:
            param_frame = ttk.LabelFrame(self.scrollable_frame, text="Parameters", padding=8)
            param_frame.pack(fill=tk.X, pady=(0, 10))

            for param_name, param_def in defn.parameters.items():
                self._render_param_field(param_frame, node, param_name, param_def)

        # Danger zone / Actions
        act_frame = ttk.LabelFrame(self.scrollable_frame, text="Actions", padding=8)
        act_frame.pack(fill=tk.X, pady=(0, 10))

        btn_delete = ttk.Button(
            act_frame,
            text="🗑️ Delete Node",
            command=lambda: self._on_delete_node(node),
        )
        btn_delete.pack(fill=tk.X)

    def _render_param_field(
        self,
        parent: ttk.Frame,
        node: Node,
        param_name: str,
        param_def: ParameterDefinition,
    ) -> None:
        current_val = node.params.get(param_name, param_def.default)

        field_container = ttk.Frame(parent)
        field_container.pack(fill=tk.X, pady=4)

        # Label and description
        label_text = param_def.display_name or param_name
        if param_def.required:
            label_text += " *"
        ttk.Label(
            field_container, text=label_text, font=("Segoe UI", 9, "bold")
        ).pack(anchor=tk.W)

        if param_def.description:
            ttk.Label(
                field_container,
                text=param_def.description,
                font=("Segoe UI", 7),
                foreground="#777777",
                wraplength=230,
            ).pack(anchor=tk.W)

        # Widget selection based on type
        if param_def.type == "enum" and param_def.options:
            var = tk.StringVar(value=str(current_val))
            self._param_vars[param_name] = var
            combo = ttk.Combobox(
                field_container,
                textvariable=var,
                values=list(param_def.options),
                state="readonly",
            )
            combo.pack(fill=tk.X, pady=(2, 0))
            combo.bind(
                "<<ComboboxSelected>>",
                lambda e, p=param_name, d=param_def: self._on_param_commit(node, p, d),
            )

        elif param_def.type == "int":
            var = tk.StringVar(value=str(current_val))
            self._param_vars[param_name] = var
            min_v = int(param_def.min_value) if param_def.min_value is not None else 0
            max_v = int(param_def.max_value) if param_def.max_value is not None else 1000000
            spin = ttk.Spinbox(field_container, from_=min_v, to=max_v, textvariable=var)
            spin.pack(fill=tk.X, pady=(2, 0))
            spin.bind(
                "<FocusOut>",
                lambda e, p=param_name, d=param_def: self._on_param_commit(node, p, d),
            )
            spin.bind(
                "<Return>",
                lambda e, p=param_name, d=param_def: self._on_param_commit(node, p, d),
            )

        elif param_def.type == "float":
            var = tk.StringVar(value=str(current_val))
            self._param_vars[param_name] = var
            entry = ttk.Entry(field_container, textvariable=var)
            entry.pack(fill=tk.X, pady=(2, 0))
            entry.bind(
                "<FocusOut>",
                lambda e, p=param_name, d=param_def: self._on_param_commit(node, p, d),
            )
            entry.bind(
                "<Return>",
                lambda e, p=param_name, d=param_def: self._on_param_commit(node, p, d),
            )

        else:  # str or default
            var = tk.StringVar(value=str(current_val) if current_val is not None else "")
            self._param_vars[param_name] = var
            entry = ttk.Entry(field_container, textvariable=var)
            entry.pack(fill=tk.X, pady=(2, 0))
            entry.bind(
                "<FocusOut>",
                lambda e, p=param_name, d=param_def: self._on_param_commit(node, p, d),
            )
            entry.bind(
                "<Return>",
                lambda e, p=param_name, d=param_def: self._on_param_commit(node, p, d),
            )

    def _on_name_commit(self, node: Node) -> None:
        if self._is_updating_ui:
            return
        new_name = self.name_var.get().strip()
        if new_name and new_name != node.name:
            node.name = new_name
            self.app_state.notify_workflow_modified()

    def _on_param_commit(
        self, node: Node, param_name: str, param_def: ParameterDefinition
    ) -> None:
        if self._is_updating_ui or param_name not in self._param_vars:
            return

        raw_val = self._param_vars[param_name].get().strip()

        try:
            if param_def.type == "int":
                parsed_val = int(raw_val)
                if param_def.min_value is not None and parsed_val < param_def.min_value:
                    parsed_val = int(param_def.min_value)
                    self._param_vars[param_name].set(str(parsed_val))
                if param_def.max_value is not None and parsed_val > param_def.max_value:
                    parsed_val = int(param_def.max_value)
                    self._param_vars[param_name].set(str(parsed_val))
            elif param_def.type == "float":
                parsed_val = float(raw_val)
                if param_def.min_value is not None and parsed_val < param_def.min_value:
                    parsed_val = float(param_def.min_value)
                    self._param_vars[param_name].set(str(parsed_val))
                if param_def.max_value is not None and parsed_val > param_def.max_value:
                    parsed_val = float(param_def.max_value)
                    self._param_vars[param_name].set(str(parsed_val))
            else:
                parsed_val = raw_val

            if node.params.get(param_name) != parsed_val:
                node.params[param_name] = parsed_val
                self.app_state.notify_workflow_modified()
        except ValueError:
            # Revert to current value on parse error
            current = node.params.get(param_name, param_def.default)
            self._param_vars[param_name].set(str(current))

    def _on_delete_node(self, node: Node) -> None:
        wf = self.app_state.current_workflow
        if not wf:
            return
        if confirm_action(
            self,
            "Delete Node",
            f"Delete node '{node.name}' and all connected edges?",
        ):
            wf.remove_node(node.id)
            self.app_state.clear_selection()
            self.app_state.notify_workflow_modified()

    # ================= Edge Properties =================

    def _render_edge_properties(self, edge: Edge) -> None:
        self.lbl_header.configure(text="Edge Connection")

        frame = ttk.LabelFrame(self.scrollable_frame, text="Connection Info", padding=8)
        frame.pack(fill=tk.X, pady=(0, 10))

        wf = self.app_state.current_workflow
        src_name = wf.get_node(edge.source).name if wf and wf.get_node(edge.source) else edge.source
        tgt_name = wf.get_node(edge.target).name if wf and wf.get_node(edge.target) else edge.target

        ttk.Label(frame, text="Source:", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text=f"{src_name} (port: {edge.source_port})",
            font=("Segoe UI", 8),
            foreground="#333333",
        ).pack(anchor=tk.W, pady=(0, 4))

        ttk.Label(frame, text="Target:", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text=f"{tgt_name} (port: {edge.target_port})",
            font=("Segoe UI", 8),
            foreground="#333333",
        ).pack(anchor=tk.W, pady=(0, 8))

        btn_delete = ttk.Button(
            frame,
            text="🗑️ Delete Edge",
            command=lambda: self._on_delete_edge(edge),
        )
        btn_delete.pack(fill=tk.X)

    def _on_delete_edge(self, edge: Edge) -> None:
        wf = self.app_state.current_workflow
        if not wf:
            return
        wf.remove_edge(edge.id)
        self.app_state.clear_selection()
        self.app_state.notify_workflow_modified()

    # ================= Workflow Properties =================

    def _render_workflow_properties(self) -> None:
        self.lbl_header.configure(text="Workflow Properties")

        wf = self.app_state.current_workflow
        if not wf:
            ttk.Label(
                self.scrollable_frame,
                text="No active workflow",
                font=("Segoe UI", 9, "italic"),
                foreground="#777777",
            ).pack(pady=20)
            return

        frame = ttk.LabelFrame(self.scrollable_frame, text="Workflow Info", padding=8)
        frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Workflow ID:", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text=wf.workflow.id,
            font=("Segoe UI", 8),
            foreground="#666666",
            wraplength=230,
        ).pack(anchor=tk.W, pady=(0, 6))

        ttk.Label(frame, text="Description:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.desc_text = tk.Text(frame, height=4, font=("Segoe UI", 9), wrap=tk.WORD)
        self.desc_text.insert("1.0", wf.workflow.description)
        self.desc_text.pack(fill=tk.X, pady=(2, 6))
        self.desc_text.bind("<FocusOut>", self._on_desc_commit)

        ttk.Label(frame, text=f"Total Nodes: {len(wf.nodes)}", font=("Segoe UI", 8)).pack(
            anchor=tk.W
        )
        ttk.Label(frame, text=f"Total Edges: {len(wf.edges)}", font=("Segoe UI", 8)).pack(
            anchor=tk.W
        )
        ttk.Label(
            frame, text=f"Created: {wf.workflow.created_at[:19]}", font=("Segoe UI", 7)
        ).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(
            frame, text=f"Updated: {wf.workflow.updated_at[:19]}", font=("Segoe UI", 7)
        ).pack(anchor=tk.W)

    def _on_desc_commit(self, event: tk.Event) -> None:
        wf = self.app_state.current_workflow
        if not wf or not hasattr(self, "desc_text"):
            return
        new_desc = self.desc_text.get("1.0", "end-1c").strip()
        if new_desc != wf.workflow.description:
            wf.workflow.description = new_desc
            self.app_state.notify_workflow_modified()

    # ================= Listeners =================

    def _on_selection_changed(
        self, node_id: Optional[str], edge_id: Optional[str]
    ) -> None:
        self.refresh()

    def _on_workflow_changed(self, workflow: Optional[Workflow]) -> None:
        # Re-render only if current selected element was modified
        self.refresh()
