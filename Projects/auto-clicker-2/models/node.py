from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


DEFAULT_NODE_WIDTH = 180.0
DEFAULT_NODE_HEIGHT = 72.0


@dataclass
class Node:
    """Vị trí hiển thị của một step trên canvas workflow."""

    id: str
    step_id: str
    x: float
    y: float
    width: float = DEFAULT_NODE_WIDTH
    height: float = DEFAULT_NODE_HEIGHT

    @classmethod
    def create(
        cls,
        step_id: str,
        x: float = 40.0,
        y: float = 40.0,
        width: float = DEFAULT_NODE_WIDTH,
        height: float = DEFAULT_NODE_HEIGHT,
    ) -> Node:
        return cls(id=str(uuid4()), step_id=step_id, x=x, y=y, width=width, height=height)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "step_id": self.step_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Node:
        return cls(
            id=data["id"],
            step_id=data["step_id"],
            x=float(data.get("x", 40)),
            y=float(data.get("y", 40)),
            width=float(data.get("width", DEFAULT_NODE_WIDTH)),
            height=float(data.get("height", DEFAULT_NODE_HEIGHT)),
        )
