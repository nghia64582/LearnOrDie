"""Workflow aggregate data model."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from models.edge import Edge
from models.exceptions import (
    DuplicateIdError,
    InvalidEdgeError,
    InvalidSchemaVersionError,
    ModelError,
)
from models.node import Node, Position
from models.node_definitions import (
    NODE_TYPE_START,
    get_input_ports,
    get_output_ports,
)

CURRENT_SCHEMA_VERSION = 1


def current_iso_timestamp() -> str:
    """Return current timestamp as ISO 8601 with local timezone."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class WorkflowMeta:
    """Metadata describing a workflow."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Workflow"
    description: str = ""
    created_at: str = field(default_factory=current_iso_timestamp)
    updated_at: str = field(default_factory=current_iso_timestamp)

    def to_dict(self) -> dict[str, str]:
        """Convert metadata to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Any) -> WorkflowMeta:
        """Deserialize WorkflowMeta from a dictionary."""
        if not isinstance(data, dict):
            raise ModelError(f"Workflow metadata must be a dict, got {type(data).__name__}")

        wf_id = data.get("id")
        if not isinstance(wf_id, str) or not wf_id.strip():
            raise ModelError(f"Workflow 'id' must be a non-empty string, got {wf_id!r}")

        name = data.get("name")
        if not isinstance(name, str):
            raise ModelError(f"Workflow 'name' must be a string, got {type(name).__name__}")

        description = data.get("description", "")
        if not isinstance(description, str):
            raise ModelError(f"Workflow 'description' must be a string, got {type(description).__name__}")

        created_at = data.get("created_at")
        if not isinstance(created_at, str) or not created_at.strip():
            raise ModelError(f"Workflow 'created_at' must be a non-empty string, got {created_at!r}")

        updated_at = data.get("updated_at")
        if not isinstance(updated_at, str) or not updated_at.strip():
            raise ModelError(f"Workflow 'updated_at' must be a non-empty string, got {updated_at!r}")

        return cls(
            id=wf_id,
            name=name,
            description=description,
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class ViewState:
    """Viewport zoom and pan state for the editor canvas."""

    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert ViewState to dictionary."""
        return {
            "zoom": float(self.zoom),
            "pan_x": float(self.pan_x),
            "pan_y": float(self.pan_y),
        }

    @classmethod
    def from_dict(cls, data: Any) -> ViewState:
        """Deserialize ViewState from a dictionary."""
        if not isinstance(data, dict):
            raise ModelError(f"View state must be a dict, got {type(data).__name__}")

        zoom = data.get("zoom", 1.0)
        pan_x = data.get("pan_x", 0.0)
        pan_y = data.get("pan_y", 0.0)

        for val, key in ((zoom, "zoom"), (pan_x, "pan_x"), (pan_y, "pan_y")):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ModelError(f"View state '{key}' must be numeric, got {type(val).__name__}")

        return cls(zoom=float(zoom), pan_x=float(pan_x), pan_y=float(pan_y))


@dataclass
class Workflow:
    """Aggregate root representing an entire workflow graph."""

    schema_version: int = CURRENT_SCHEMA_VERSION
    workflow: WorkflowMeta = field(default_factory=WorkflowMeta)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    view: ViewState = field(default_factory=ViewState)

    @classmethod
    def create_default(cls, name: str = "New Workflow", description: str = "") -> Workflow:
        """Create a new workflow initialized with a default START node."""
        wf = cls(
            schema_version=CURRENT_SCHEMA_VERSION,
            workflow=WorkflowMeta(name=name, description=description),
            nodes=[],
            edges=[],
            view=ViewState(),
        )
        start_node = Node.create(
            node_type=NODE_TYPE_START,
            name="Start",
            position=Position(300.0, 60.0),
        )
        wf.add_node(start_node)
        return wf

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by its ID, or None if not found."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def add_node(self, node: Node) -> None:
        """Add a node to the workflow.

        Raises DuplicateIdError if a node with the same ID already exists.
        """
        if self.get_node(node.id) is not None:
            raise DuplicateIdError(f"Node with ID '{node.id}' already exists in workflow")
        self.nodes.append(node)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and cascade-delete all edges attached to it.

        Returns True if node was found and removed, False otherwise.
        """
        target_node = self.get_node(node_id)
        if target_node is None:
            return False

        # Cascade edge removal: remove any edges connected to this node as source or target
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        self.nodes.remove(target_node)
        return True

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get an edge by its ID, or None if not found."""
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None

    def add_edge(self, edge: Edge, strict: bool = False) -> None:
        """Add an edge to the workflow.

        If strict is True, validates:
        - Source and target nodes exist.
        - Source port is a valid output port for the source node type.
        - Target port is a valid input port for the target node type.
        - Source output port does not already have an outgoing edge.

        Always checks for duplicate edge IDs and duplicate identical edges.
        """
        if self.get_edge(edge.id) is not None:
            raise DuplicateIdError(f"Edge with ID '{edge.id}' already exists in workflow")

        # Check duplicate identical edge
        for existing in self.edges:
            if (
                existing.source == edge.source
                and existing.source_port == edge.source_port
                and existing.target == edge.target
                and existing.target_port == edge.target_port
            ):
                raise InvalidEdgeError("Edge between the same ports already exists")

        if strict:
            source_node = self.get_node(edge.source)
            if source_node is None:
                raise InvalidEdgeError(f"Source node '{edge.source}' does not exist")

            target_node = self.get_node(edge.target)
            if target_node is None:
                raise InvalidEdgeError(f"Target node '{edge.target}' does not exist")

            valid_outputs = get_output_ports(source_node.type)
            if edge.source_port not in valid_outputs:
                raise InvalidEdgeError(
                    f"Port '{edge.source_port}' is not a valid output port for node type '{source_node.type}'"
                )

            valid_inputs = get_input_ports(target_node.type)
            if edge.target_port not in valid_inputs:
                raise InvalidEdgeError(
                    f"Port '{edge.target_port}' is not a valid input port for node type '{target_node.type}'"
                )

            # Each output port can have at most one outgoing edge
            for existing in self.edges:
                if existing.source == edge.source and existing.source_port == edge.source_port:
                    raise InvalidEdgeError(
                        f"Output port '{edge.source_port}' on node '{edge.source}' already has an outgoing edge"
                    )

        self.edges.append(edge)

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge by its ID.

        Returns True if edge was removed, False otherwise.
        """
        target_edge = self.get_edge(edge_id)
        if target_edge is None:
            return False
        self.edges.remove(target_edge)
        return True

    def find_edges_by_node(self, node_id: str) -> list[Edge]:
        """Find all edges attached to a node (incoming or outgoing)."""
        return [e for e in self.edges if e.source == node_id or e.target == node_id]

    def find_outgoing_edges(self, node_id: str, port: Optional[str] = None) -> list[Edge]:
        """Find all outgoing edges from a node, optionally filtered by port."""
        if port is None:
            return [e for e in self.edges if e.source == node_id]
        return [e for e in self.edges if e.source == node_id and e.source_port == port]

    def find_incoming_edges(self, node_id: str, port: Optional[str] = None) -> list[Edge]:
        """Find all incoming edges to a node, optionally filtered by port."""
        if port is None:
            return [e for e in self.edges if e.target == node_id]
        return [e for e in self.edges if e.target == node_id and e.target_port == port]

    def to_dict(self) -> dict[str, Any]:
        """Serialize workflow to dictionary matching the JSON specification."""
        return {
            "schema_version": self.schema_version,
            "workflow": self.workflow.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "view": self.view.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize workflow to human-readable JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Any) -> Workflow:
        """Deserialize workflow from a dictionary.

        Raises InvalidSchemaVersionError or ModelError if structure is invalid.
        """
        if not isinstance(data, dict):
            raise ModelError(f"Workflow data must be a dict, got {type(data).__name__}")

        if "schema_version" not in data:
            raise InvalidSchemaVersionError("Missing 'schema_version' field")

        schema_version = data["schema_version"]
        if schema_version != CURRENT_SCHEMA_VERSION:
            raise InvalidSchemaVersionError(
                f"Unsupported schema_version: {schema_version}. Expected {CURRENT_SCHEMA_VERSION}."
            )

        if "workflow" not in data:
            raise ModelError("Missing 'workflow' metadata field")
        workflow_meta = WorkflowMeta.from_dict(data["workflow"])

        raw_nodes = data.get("nodes")
        if not isinstance(raw_nodes, list):
            raise ModelError(f"'nodes' must be a list, got {type(raw_nodes).__name__}")

        nodes: list[Node] = []
        node_ids: set[str] = set()
        for raw_node in raw_nodes:
            node = Node.from_dict(raw_node)
            if node.id in node_ids:
                raise DuplicateIdError(f"Duplicate node ID '{node.id}' in workflow")
            node_ids.add(node.id)
            nodes.append(node)

        raw_edges = data.get("edges")
        if not isinstance(raw_edges, list):
            raise ModelError(f"'edges' must be a list, got {type(raw_edges).__name__}")

        edges: list[Edge] = []
        edge_ids: set[str] = set()
        for raw_edge in raw_edges:
            edge = Edge.from_dict(raw_edge)
            if edge.id in edge_ids:
                raise DuplicateIdError(f"Duplicate edge ID '{edge.id}' in workflow")
            edge_ids.add(edge.id)
            edges.append(edge)

        raw_view = data.get("view", {})
        view = ViewState.from_dict(raw_view)

        return cls(
            schema_version=schema_version,
            workflow=workflow_meta,
            nodes=nodes,
            edges=edges,
            view=view,
        )

    @classmethod
    def from_json(cls, json_str: str) -> Workflow:
        """Deserialize workflow from a JSON string."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as err:
            raise ModelError(f"Invalid JSON string: {err}") from err
        return cls.from_dict(data)
