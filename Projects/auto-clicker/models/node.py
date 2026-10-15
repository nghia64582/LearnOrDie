"""Node data model."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from models.exceptions import InvalidNodeError
from models.node_definitions import (
    get_default_params,
    get_node_definition,
    is_valid_node_type,
)


@dataclass
class Position:
    """Represents a 2D position in graph logic coordinates."""

    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert position to dictionary."""
        return {"x": float(self.x), "y": float(self.y)}

    @classmethod
    def from_dict(cls, data: Any) -> Position:
        """Create a Position instance from a dictionary.

        Raises InvalidNodeError if data is malformed.
        """
        if not isinstance(data, dict):
            raise InvalidNodeError(f"Position must be a dict, got {type(data).__name__}")
        if "x" not in data or "y" not in data:
            raise InvalidNodeError("Position dict must contain 'x' and 'y' keys")

        x, y = data["x"], data["y"]
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise InvalidNodeError(f"Position 'x' must be numeric, got {type(x).__name__}")
        if isinstance(y, bool) or not isinstance(y, (int, float)):
            raise InvalidNodeError(f"Position 'y' must be numeric, got {type(y).__name__}")

        return cls(x=float(x), y=float(y))


@dataclass
class Node:
    """Represents a workflow graph node."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    position: Position = field(default_factory=Position)

    @classmethod
    def create(
        cls,
        node_type: str,
        name: Optional[str] = None,
        position: Optional[Position] = None,
        params: Optional[dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> Node:
        """Convenience factory to create a node with defaults from the catalog."""
        if not is_valid_node_type(node_type):
            raise InvalidNodeError(f"Unknown node type: '{node_type}'")

        definition = get_node_definition(node_type)
        resolved_name = name if name is not None else definition.default_name
        resolved_pos = position if position is not None else Position(0.0, 0.0)

        merged_params = get_default_params(node_type)
        if params is not None:
            merged_params.update(params)

        actual_id = node_id if node_id is not None else str(uuid.uuid4())

        return cls(
            id=actual_id,
            type=node_type,
            name=resolved_name,
            params=merged_params,
            position=resolved_pos,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize node to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "params": copy.deepcopy(self.params),
            "position": self.position.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Any) -> Node:
        """Deserialize node from a dictionary.

        Raises InvalidNodeError on unknown node types or malformed structures.
        """
        if not isinstance(data, dict):
            raise InvalidNodeError(f"Node data must be a dict, got {type(data).__name__}")

        node_id = data.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise InvalidNodeError(f"Node 'id' must be a non-empty string, got {node_id!r}")

        node_type = data.get("type")
        if not isinstance(node_type, str):
            raise InvalidNodeError(f"Node 'type' must be a string, got {type(node_type).__name__}")
        if not is_valid_node_type(node_type):
            raise InvalidNodeError(f"Unknown node type: '{node_type}'")

        name = data.get("name")
        if not isinstance(name, str):
            raise InvalidNodeError(f"Node 'name' must be a string, got {type(name).__name__}")

        params = data.get("params")
        if not isinstance(params, dict):
            raise InvalidNodeError(f"Node 'params' must be a dict, got {type(params).__name__}")

        raw_pos = data.get("position")
        position = Position.from_dict(raw_pos)

        return cls(
            id=node_id,
            type=node_type,
            name=name,
            params=copy.deepcopy(params),
            position=position,
        )
