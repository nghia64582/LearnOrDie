"""Application state and event dispatcher."""

from __future__ import annotations

from typing import Callable, Optional

from models.edge import Edge
from models.node import Node
from models.workflow import Workflow
from services.workflow_service import WorkflowService


class AppState:
    """Central state container for the application."""

    def __init__(
        self,
        service: WorkflowService,
        image_service: Optional[Any] = None,
    ) -> None:
        self.service = service
        self.image_service = image_service
        self.selected_node_id: Optional[str] = None
        self.selected_edge_id: Optional[str] = None
        self.pending_node_type: Optional[str] = None

        self._listeners: dict[str, list[Callable[..., None]]] = {
            "workflow_changed": [],
            "selection_changed": [],
            "dirty_changed": [],
            "view_changed": [],
            "toolbox_changed": [],
        }

    @property
    def current_workflow(self) -> Optional[Workflow]:
        return self.service.current_workflow

    @property
    def is_dirty(self) -> bool:
        return self.service.is_dirty

    def add_listener(self, event: str, callback: Callable[..., None]) -> None:
        """Register a callback for an application event."""
        if event in self._listeners:
            self._listeners[event].append(callback)

    def remove_listener(self, event: str, callback: Callable[..., None]) -> None:
        """Unregister a callback for an application event."""
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to all registered listeners."""
        for callback in list(self._listeners.get(event, [])):
            callback(*args, **kwargs)

    def select_node(self, node_id: Optional[str]) -> None:
        """Select a single node by ID and deselect any active edge."""
        if self.selected_node_id == node_id and self.selected_edge_id is None:
            return
        self.selected_node_id = node_id
        self.selected_edge_id = None
        self.emit("selection_changed", self.selected_node_id, self.selected_edge_id)

    def select_edge(self, edge_id: Optional[str]) -> None:
        """Select a single edge by ID and deselect any active node."""
        if self.selected_edge_id == edge_id and self.selected_node_id is None:
            return
        self.selected_edge_id = edge_id
        self.selected_node_id = None
        self.emit("selection_changed", self.selected_node_id, self.selected_edge_id)

    def clear_selection(self) -> None:
        """Deselect all nodes and edges."""
        if self.selected_node_id is not None or self.selected_edge_id is not None:
            self.selected_node_id = None
            self.selected_edge_id = None
            self.emit("selection_changed", None, None)

    def get_selected_node(self) -> Optional[Node]:
        """Return currently selected Node or None."""
        if self.selected_node_id and self.current_workflow:
            return self.current_workflow.get_node(self.selected_node_id)
        return None

    def get_selected_edge(self) -> Optional[Edge]:
        """Return currently selected Edge or None."""
        if self.selected_edge_id and self.current_workflow:
            return self.current_workflow.get_edge(self.selected_edge_id)
        return None

    def set_pending_node_type(self, node_type: Optional[str]) -> None:
        """Set or clear the node type pending addition on canvas click."""
        self.pending_node_type = node_type
        self.emit("toolbox_changed", self.pending_node_type)

    def notify_workflow_modified(self) -> None:
        """Mark workflow as dirty and notify listeners."""
        was_dirty = self.service.is_dirty
        self.service.mark_dirty()
        if not was_dirty:
            self.emit("dirty_changed", True)
        self.emit("workflow_changed", self.current_workflow)

    def notify_workflow_loaded(self) -> None:
        """Call after opening or creating a new workflow."""
        self.clear_selection()
        self.set_pending_node_type(None)
        self.emit("dirty_changed", self.service.is_dirty)
        self.emit("workflow_changed", self.current_workflow)

    def notify_workflow_saved(self) -> None:
        """Call after saving the current workflow."""
        self.emit("dirty_changed", False)
        self.emit("workflow_changed", self.current_workflow)
