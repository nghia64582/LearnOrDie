"""Edge data model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from models.exceptions import InvalidEdgeError
from models.node_definitions import DEFAULT_INPUT_PORT


@dataclass
class Edge:
    """Represents a directed connection between two node ports."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    source_port: str = ""
    target: str = ""
    target_port: str = DEFAULT_INPUT_PORT

    def to_dict(self) -> dict[str, str]:
        """Convert edge to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "source": self.source,
            "source_port": self.source_port,
            "target": self.target,
            "target_port": self.target_port,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Edge:
        """Deserialize edge from a dictionary.

        Raises InvalidEdgeError if data is malformed.
        """
        if not isinstance(data, dict):
            raise InvalidEdgeError(f"Edge data must be a dict, got {type(data).__name__}")

        edge_id = data.get("id")
        if not isinstance(edge_id, str) or not edge_id.strip():
            raise InvalidEdgeError(f"Edge 'id' must be a non-empty string, got {edge_id!r}")

        source = data.get("source")
        if not isinstance(source, str) or not source.strip():
            raise InvalidEdgeError(f"Edge 'source' must be a non-empty string, got {source!r}")

        source_port = data.get("source_port")
        if not isinstance(source_port, str) or not source_port.strip():
            raise InvalidEdgeError(f"Edge 'source_port' must be a non-empty string, got {source_port!r}")

        target = data.get("target")
        if not isinstance(target, str) or not target.strip():
            raise InvalidEdgeError(f"Edge 'target' must be a non-empty string, got {target!r}")

        target_port = data.get("target_port")
        if not isinstance(target_port, str) or not target_port.strip():
            raise InvalidEdgeError(f"Edge 'target_port' must be a non-empty string, got {target_port!r}")

        return cls(
            id=edge_id,
            source=source,
            source_port=source_port,
            target=target,
            target_port=target_port,
        )
