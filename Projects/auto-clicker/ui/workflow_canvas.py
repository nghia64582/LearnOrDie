"""Interactive canvas for workflow graph editing."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Optional

from app.app_state import AppState
from models.edge import Edge
from models.node import Node, Position
from models.node_definitions import (
    GROUP_ACTION,
    GROUP_CONDITION,
    GROUP_FLOW,
    NODE_DEFINITIONS,
    get_input_ports,
    get_node_definition,
    get_output_ports,
)
from models.workflow import Workflow

NODE_WIDTH = 170.0
NODE_MIN_HEIGHT = 70.0
PORT_RADIUS = 5.0
GRID_SIZE = 30.0

# Group color schemes: (header_bg, header_fg, body_bg, border_color)
GROUP_COLORS = {
    GROUP_FLOW: ("#5c6bc0", "#ffffff", "#ffffff", "#3949ab"),
    GROUP_ACTION: ("#26a69a", "#ffffff", "#ffffff", "#00897b"),
    GROUP_CONDITION: ("#ffa726", "#ffffff", "#ffffff", "#fb8c00"),
}


class WorkflowCanvas(tk.Canvas):
    """Tkinter Canvas for displaying and manipulating workflow nodes and edges."""

    def __init__(self, parent: tk.Widget, app_state: AppState, **kwargs) -> None:
        kwargs.setdefault("bg", "#f5f7fa")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self.app_state = app_state

        # Dragging and panning state
        self._drag_node_id: Optional[str] = None
        self._drag_start_screen: tuple[float, float] = (0.0, 0.0)
        self._drag_start_node_pos: tuple[float, float] = (0.0, 0.0)
        self._has_dragged: bool = False

        self._pan_start: Optional[tuple[float, float]] = None

        # Tags and item registry
        self._node_items: dict[str, list[int]] = {}
        self._edge_items: dict[str, list[int]] = {}

        self._bind_events()
        self.app_state.add_listener("workflow_changed", self._on_workflow_changed)
        self.app_state.add_listener("selection_changed", self._on_selection_changed)

    @property
    def workflow(self) -> Optional[Workflow]:
        return self.app_state.current_workflow

    @property
    def zoom(self) -> float:
        if self.workflow and self.workflow.view:
            return max(0.2, min(3.0, self.workflow.view.zoom))
        return 1.0

    @zoom.setter
    def zoom(self, val: float) -> None:
        if self.workflow and self.workflow.view:
            self.workflow.view.zoom = max(0.2, min(3.0, val))

    @property
    def pan_x(self) -> float:
        return self.workflow.view.pan_x if self.workflow and self.workflow.view else 0.0

    @pan_x.setter
    def pan_x(self, val: float) -> None:
        if self.workflow and self.workflow.view:
            self.workflow.view.pan_x = val

    @property
    def pan_y(self) -> float:
        return self.workflow.view.pan_y if self.workflow and self.workflow.view else 0.0

    @pan_y.setter
    def pan_y(self, val: float) -> None:
        if self.workflow and self.workflow.view:
            self.workflow.view.pan_y = val

    # ================= Coordinate Conversion =================

    def logic_to_screen(self, lx: float, ly: float) -> tuple[float, float]:
        """Convert graph logic coordinates to canvas screen pixel coordinates."""
        return (lx * self.zoom + self.pan_x, ly * self.zoom + self.pan_y)

    def screen_to_logic(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert canvas screen pixel coordinates to graph logic coordinates."""
        return ((sx - self.pan_x) / self.zoom, (sy - self.pan_y) / self.zoom)

    # ================= Geometry & Port Positions =================

    def get_node_height(self, node: Node) -> float:
        """Compute logic height of a node based on its output ports."""
        outputs = get_output_ports(node.type)
        return max(NODE_MIN_HEIGHT, 40.0 + len(outputs) * 18.0)

    def get_port_logic_pos(
        self, node_id: str, port_name: str, is_output: bool
    ) -> Optional[tuple[float, float]]:
        """Calculate the logic center (x, y) coordinates for a node port."""
        if not self.workflow:
            return None
        node = self.workflow.get_node(node_id)
        if not node:
            return None

        h = self.get_node_height(node)
        if not is_output:
            # Input port on left edge center
            return (node.position.x, node.position.y + h / 2.0)
        else:
            outputs = get_output_ports(node.type)
            if port_name not in outputs:
                return (node.position.x + NODE_WIDTH, node.position.y + h / 2.0)
            idx = outputs.index(port_name)
            count = len(outputs)
            spacing = (h - 26.0) / (count + 1)
            py = node.position.y + 26.0 + spacing * (idx + 1)
            return (node.position.x + NODE_WIDTH, py)

    # ================= Event Bindings =================

    def _bind_events(self) -> None:
        self.bind("<ButtonPress-1>", self._on_left_click_press)
        self.bind("<B1-Motion>", self._on_left_click_drag)
        self.bind("<ButtonRelease-1>", self._on_left_click_release)

        # Pan with Right Mouse Button or Middle Mouse Button
        self.bind("<ButtonPress-2>", self._on_pan_press)
        self.bind("<B2-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-2>", self._on_pan_release)

        self.bind("<ButtonPress-3>", self._on_pan_press)
        self.bind("<B3-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-3>", self._on_pan_release)

        # Zoom with MouseWheel
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self._on_wheel_zoom(e, 1.1))  # Linux
        self.bind("<Button-5>", lambda e: self._on_wheel_zoom(e, 0.9))  # Linux

        # Keyboard shortcuts
        self.bind("<Delete>", self._on_delete_key)
        self.bind("<BackSpace>", self._on_delete_key)
        self.bind("<Escape>", self._on_escape_key)

        # Resize
        self.bind("<Configure>", lambda e: self.repaint())

    # ================= User Interaction Handlers =================

    def _on_left_click_press(self, event: tk.Event) -> None:
        self.focus_set()

        # If user has a pending node type from toolbox, place it at click position
        if self.app_state.pending_node_type:
            lx, ly = self.screen_to_logic(event.x, event.y)
            # Center node on click
            lx -= NODE_WIDTH / 2.0
            ly -= 35.0
            new_node = Node.create(
                self.app_state.pending_node_type,
                position=Position(round(lx, 1), round(ly, 1)),
            )
            if self.workflow:
                self.workflow.add_node(new_node)
                self.app_state.set_pending_node_type(None)
                self.app_state.select_node(new_node.id)
                self.app_state.notify_workflow_modified()
                self.repaint()
            return

        # Find item under cursor
        hit_node_id = self._find_node_at(event.x, event.y)
        if hit_node_id:
            self._drag_node_id = hit_node_id
            self._drag_start_screen = (event.x, event.y)
            node = self.workflow.get_node(hit_node_id) if self.workflow else None
            if node:
                self._drag_start_node_pos = (node.position.x, node.position.y)
            self._has_dragged = False
            self.app_state.select_node(hit_node_id)
            self.repaint()
            return

        hit_edge_id = self._find_edge_at(event.x, event.y)
        if hit_edge_id:
            self.app_state.select_edge(hit_edge_id)
            self.repaint()
            return

        # Clicked on empty canvas -> clear selection
        self.app_state.clear_selection()
        self.repaint()

    def _on_left_click_drag(self, event: tk.Event) -> None:
        if not self._drag_node_id or not self.workflow:
            return

        dx = (event.x - self._drag_start_screen[0]) / self.zoom
        dy = (event.y - self._drag_start_screen[1]) / self.zoom

        node = self.workflow.get_node(self._drag_node_id)
        if node:
            node.position.x = round(self._drag_start_node_pos[0] + dx, 1)
            node.position.y = round(self._drag_start_node_pos[1] + dy, 1)
            self._has_dragged = True
            self.repaint()

    def _on_left_click_release(self, event: tk.Event) -> None:
        if self._drag_node_id and self._has_dragged:
            self.app_state.notify_workflow_modified()
        self._drag_node_id = None
        self._has_dragged = False

    def _on_pan_press(self, event: tk.Event) -> None:
        self._pan_start = (event.x, event.y)

    def _on_pan_drag(self, event: tk.Event) -> None:
        if not self._pan_start:
            return
        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]
        self._pan_start = (event.x, event.y)

        self.pan_x += dx
        self.pan_y += dy
        self.repaint()

    def _on_pan_release(self, event: tk.Event) -> None:
        self._pan_start = None

    def _on_mousewheel(self, event: tk.Event) -> None:
        factor = 1.15 if event.delta > 0 else 0.85
        self._on_wheel_zoom(event, factor)

    def _on_wheel_zoom(self, event: tk.Event, factor: float) -> None:
        old_zoom = self.zoom
        new_zoom = max(0.2, min(3.0, old_zoom * factor))
        if math.isclose(old_zoom, new_zoom):
            return

        # Zoom centering at mouse position
        cx, cy = event.x, event.y
        lx, ly = self.screen_to_logic(cx, cy)
        self.zoom = new_zoom
        self.pan_x = cx - lx * new_zoom
        self.pan_y = cy - ly * new_zoom
        self.repaint()

    def _on_delete_key(self, event: tk.Event) -> None:
        if not self.workflow:
            return

        if self.app_state.selected_node_id:
            node_id = self.app_state.selected_node_id
            self.workflow.remove_node(node_id)
            self.app_state.clear_selection()
            self.app_state.notify_workflow_modified()
            self.repaint()
        elif self.app_state.selected_edge_id:
            edge_id = self.app_state.selected_edge_id
            self.workflow.remove_edge(edge_id)
            self.app_state.clear_selection()
            self.app_state.notify_workflow_modified()
            self.repaint()

    def _on_escape_key(self, event: tk.Event) -> None:
        self.app_state.set_pending_node_type(None)
        self.app_state.clear_selection()
        self.repaint()

    # ================= Hit Testing =================

    def _find_node_at(self, sx: float, sy: float) -> Optional[str]:
        if not self.workflow:
            return None
        # Test in reverse order (topmost node first)
        for node in reversed(self.workflow.nodes):
            nx0, ny0 = self.logic_to_screen(node.position.x, node.position.y)
            h = self.get_node_height(node)
            nx1 = nx0 + NODE_WIDTH * self.zoom
            ny1 = ny0 + h * self.zoom
            if nx0 <= sx <= nx1 and ny0 <= sy <= ny1:
                return node.id
        return None

    def _find_edge_at(self, sx: float, sy: float) -> Optional[str]:
        """Find edge close to the click position using canvas find_withtag."""
        items = self.find_overlapping(sx - 4, sy - 4, sx + 4, sy + 4)
        for item in reversed(items):
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith("edge:"):
                    return tag.split("edge:")[1]
        return None

    # ================= Rendering =================

    def _on_workflow_changed(self, workflow: Optional[Workflow]) -> None:
        self.repaint()

    def _on_selection_changed(self, node_id: Optional[str], edge_id: Optional[str]) -> None:
        self.repaint()

    def repaint(self) -> None:
        """Clear and redraw the entire canvas."""
        self.delete("all")
        self._node_items.clear()
        self._edge_items.clear()

        if not self.workflow:
            self._draw_empty_placeholder()
            return

        self._draw_grid()
        self._draw_edges()
        self._draw_nodes()

    def _draw_empty_placeholder(self) -> None:
        w = self.winfo_width()
        h = self.winfo_height()
        self.create_text(
            w / 2,
            h / 2,
            text="No workflow open.\nSelect or create a workflow to begin.",
            font=("Segoe UI", 12),
            fill="#888888",
            justify=tk.CENTER,
        )

    def _draw_grid(self) -> None:
        w = max(self.winfo_width(), 1000)
        h = max(self.winfo_height(), 800)

        step = GRID_SIZE * self.zoom
        if step < 12.0:
            return  # Do not draw overly dense grid

        start_x = self.pan_x % step
        start_y = self.pan_y % step

        x = start_x
        while x < w:
            self.create_line(x, 0, x, h, fill="#e9edf2", width=1, tags="grid")
            x += step

        y = start_y
        while y < h:
            self.create_line(0, y, w, y, fill="#e9edf2", width=1, tags="grid")
            y += step

    def _draw_nodes(self) -> None:
        if not self.workflow:
            return

        for node in self.workflow.nodes:
            self._draw_single_node(node)

    def _draw_single_node(self, node: Node) -> None:
        is_selected = node.id == self.app_state.selected_node_id
        defn = get_node_definition(node.type)
        group = defn.group
        header_bg, header_fg, body_bg, border_color = GROUP_COLORS.get(
            group, ("#78909c", "#ffffff", "#ffffff", "#546e7a")
        )

        h_logic = self.get_node_height(node)
        x0, y0 = self.logic_to_screen(node.position.x, node.position.y)
        x1 = x0 + NODE_WIDTH * self.zoom
        y1 = y0 + h_logic * self.zoom
        header_height = 24.0 * self.zoom

        tag = f"node:{node.id}"

        # Outer border / body
        outline_width = 3 if is_selected else 1
        outline_color = "#2196f3" if is_selected else border_color

        body_rect = self.create_rectangle(
            x0, y0, x1, y1,
            fill=body_bg,
            outline=outline_color,
            width=outline_width,
            tags=("node", tag),
        )

        # Header background
        header_rect = self.create_rectangle(
            x0, y0, x1, y0 + header_height,
            fill=header_bg,
            outline=outline_color,
            width=outline_width,
            tags=("node", tag),
        )

        # Header title: type
        font_size_header = max(7, int(9 * self.zoom))
        self.create_text(
            x0 + 8 * self.zoom,
            y0 + header_height / 2.0,
            text=node.type,
            font=("Segoe UI", font_size_header, "bold"),
            fill=header_fg,
            anchor=tk.W,
            tags=("node", tag),
        )

        # Node name in body
        font_size_body = max(8, int(10 * self.zoom))
        self.create_text(
            x0 + 10 * self.zoom,
            y0 + header_height + 12 * self.zoom,
            text=node.name,
            font=("Segoe UI", font_size_body),
            fill="#212121",
            anchor=tk.W,
            tags=("node", tag),
        )

        # Draw Input Port ('in') if node accepts input
        inputs = get_input_ports(node.type)
        if inputs:
            port_name = inputs[0]
            port_lpos = self.get_port_logic_pos(node.id, port_name, is_output=False)
            if port_lpos:
                px, py = self.logic_to_screen(port_lpos[0], port_lpos[1])
                pr = PORT_RADIUS * self.zoom
                self.create_oval(
                    px - pr, py - pr, px + pr, py + pr,
                    fill="#90caf9",
                    outline="#1565c0",
                    width=2,
                    tags=("port", f"port_in:{node.id}:{port_name}", tag),
                )
                self.create_text(
                    px + pr + 4 * self.zoom,
                    py,
                    text=port_name,
                    font=("Segoe UI", max(6, int(8 * self.zoom))),
                    fill="#555555",
                    anchor=tk.W,
                    tags=("port", tag),
                )

        # Draw Output Ports
        outputs = get_output_ports(node.type)
        for port_name in outputs:
            port_lpos = self.get_port_logic_pos(node.id, port_name, is_output=True)
            if port_lpos:
                px, py = self.logic_to_screen(port_lpos[0], port_lpos[1])
                pr = PORT_RADIUS * self.zoom
                self.create_oval(
                    px - pr, py - pr, px + pr, py + pr,
                    fill="#a5d6a7",
                    outline="#2e7d32",
                    width=2,
                    tags=("port", f"port_out:{node.id}:{port_name}", tag),
                )
                self.create_text(
                    px - pr - 4 * self.zoom,
                    py,
                    text=port_name,
                    font=("Segoe UI", max(6, int(8 * self.zoom))),
                    fill="#333333",
                    anchor=tk.E,
                    tags=("port", tag),
                )

    def _draw_edges(self) -> None:
        if not self.workflow:
            return

        for edge in self.workflow.edges:
            self._draw_single_edge(edge)

    def _draw_single_edge(self, edge: Edge) -> None:
        src_pos = self.get_port_logic_pos(edge.source, edge.source_port, is_output=True)
        tgt_pos = self.get_port_logic_pos(edge.target, edge.target_port, is_output=False)

        if not src_pos or not tgt_pos:
            return

        x1, y1 = self.logic_to_screen(src_pos[0], src_pos[1])
        x2, y2 = self.logic_to_screen(tgt_pos[0], tgt_pos[1])

        is_selected = edge.id == self.app_state.selected_edge_id
        color = "#ff6f00" if is_selected else "#455a64"
        width = 3 if is_selected else 2

        tag = f"edge:{edge.id}"

        # Calculate smooth bezier control points
        dx = max(40.0 * self.zoom, abs(x2 - x1) * 0.5)
        cx1, cy1 = x1 + dx, y1
        cx2, cy2 = x2 - dx, y2

        arrow_size = (int(10 * self.zoom), int(12 * self.zoom), int(5 * self.zoom))

        self.create_line(
            x1, y1, cx1, cy1, cx2, cy2, x2, y2,
            smooth=True,
            arrow=tk.LAST,
            arrowshape=arrow_size,
            fill=color,
            width=width,
            tags=("edge", tag),
        )

        # Port label badge near edge start
        badge_x = x1 + 18.0 * self.zoom
        badge_y = y1 - 8.0 * self.zoom
        font_size = max(7, int(8 * self.zoom))
        self.create_text(
            badge_x,
            badge_y,
            text=edge.source_port,
            font=("Segoe UI", font_size, "italic"),
            fill="#37474f",
            anchor=tk.W,
            tags=("edge", tag),
        )

    # ================= View Control Helpers =================

    def reset_view(self) -> None:
        """Reset zoom to 1.0 and pan to center nodes."""
        self.zoom = 1.0
        self.pan_x = 50.0
        self.pan_y = 50.0
        self.repaint()

    def zoom_in(self) -> None:
        w, h = self.winfo_width() / 2, self.winfo_height() / 2
        lx, ly = self.screen_to_logic(w, h)
        self.zoom = min(3.0, self.zoom * 1.2)
        self.pan_x = w - lx * self.zoom
        self.pan_y = h - ly * self.zoom
        self.repaint()

    def zoom_out(self) -> None:
        w, h = self.winfo_width() / 2, self.winfo_height() / 2
        lx, ly = self.screen_to_logic(w, h)
        self.zoom = max(0.2, self.zoom / 1.2)
        self.pan_x = w - lx * self.zoom
        self.pan_y = h - ly * self.zoom
        self.repaint()
