"""Toolbox panel for selecting and adding graph nodes."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from app.app_state import AppState
from models.node_definitions import (
    GROUP_ACTION,
    GROUP_CONDITION,
    GROUP_FLOW,
    NODE_DEFINITIONS,
)


class NodeToolbox(ttk.Frame):
    """Sidebar toolbox for adding nodes to the canvas."""

    def __init__(
        self,
        parent: tk.Widget,
        app_state: AppState,
        on_add_node_center: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.app_state = app_state
        self.on_add_node_center = on_add_node_center
        self._buttons: dict[str, ttk.Button] = {}

        self._build_ui()
        self.app_state.add_listener("toolbox_changed", self._on_toolbox_changed)

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Toolbox", font=("Segoe UI", 11, "bold"))
        header.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Pointer / Select button
        self.btn_select = ttk.Button(
            self,
            text="↖ Select / Move",
            command=self._on_select_mode_clicked,
        )
        self.btn_select.pack(fill=tk.X, padx=10, pady=(0, 10))

        help_lbl = ttk.Label(
            self,
            text="Click a node type, then click on Canvas to place it.\nOr click [+] to add to center.",
            font=("Segoe UI", 8),
            foreground="#666666",
            wraplength=160,
        )
        help_lbl.pack(fill=tk.X, padx=10, pady=(0, 8))

        groups = [
            (GROUP_FLOW, "#e3f2fd"),
            (GROUP_ACTION, "#e8f5e9"),
            (GROUP_CONDITION, "#fff9c4"),
        ]

        for group_name, _ in groups:
            group_frame = ttk.LabelFrame(self, text=group_name)
            group_frame.pack(fill=tk.X, padx=8, pady=4)

            # Find all nodes in this group
            nodes_in_group = [
                (ntype, defn)
                for ntype, defn in NODE_DEFINITIONS.items()
                if defn.group == group_name
            ]

            for ntype, defn in nodes_in_group:
                btn_row = ttk.Frame(group_frame)
                btn_row.pack(fill=tk.X, padx=4, pady=2)

                btn = ttk.Button(
                    btn_row,
                    text=defn.display_name,
                    command=lambda t=ntype: self._on_tool_clicked(t),
                )
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._buttons[ntype] = btn

                add_btn = ttk.Button(
                    btn_row,
                    text="+",
                    width=2,
                    command=lambda t=ntype: self._on_plus_clicked(t),
                )
                add_btn.pack(side=tk.RIGHT, padx=(2, 0))

    def _on_tool_clicked(self, node_type: str) -> None:
        if self.app_state.pending_node_type == node_type:
            # Toggle off
            self.app_state.set_pending_node_type(None)
        else:
            self.app_state.set_pending_node_type(node_type)

    def _on_plus_clicked(self, node_type: str) -> None:
        if self.on_add_node_center:
            self.on_add_node_center(node_type)

    def _on_select_mode_clicked(self) -> None:
        self.app_state.set_pending_node_type(None)

    def _on_toolbox_changed(self, pending_type: Optional[str]) -> None:
        # Update button text/state indication
        for ntype, btn in self._buttons.items():
            defn = NODE_DEFINITIONS[ntype]
            if pending_type == ntype:
                btn.configure(text=f"👉 {defn.display_name}")
            else:
                btn.configure(text=defn.display_name)
