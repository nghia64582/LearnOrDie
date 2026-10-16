from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from models.node import Node
from models.step import Step


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Workflow:
    """Quy trình gồm tập hợp các bước (step) và layout canvas (node)."""

    id: str
    name: str
    steps: list[Step] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    @classmethod
    def create(cls, name: str) -> Workflow:
        now = _utc_now_iso()
        return cls(id=str(uuid4()), name=name, created_at=now, updated_at=now)

    def touch(self) -> None:
        self.updated_at = _utc_now_iso()

    def add_step(self, step: Step, node: Node | None = None, index: int | None = None) -> None:
        if index is None:
            index = len(self.steps)
        index = max(0, min(index, len(self.steps)))
        self.steps.insert(index, step)
        if node is None:
            node = Node.create(step.id)
        self.nodes.insert(index, node)
        self._relayout_nodes()
        self.touch()

    def remove_step(self, step_id: str) -> None:
        self.steps = [step for step in self.steps if step.id != step_id]
        self.nodes = [node for node in self.nodes if node.step_id != step_id]
        self._relayout_nodes()
        self.touch()

    def move_step(self, step_id: str, offset: int) -> bool:
        index = next((i for i, step in enumerate(self.steps) if step.id == step_id), None)
        if index is None:
            return False
        new_index = index + offset
        if new_index < 0 or new_index >= len(self.steps):
            return False
        self.steps[index], self.steps[new_index] = self.steps[new_index], self.steps[index]
        self._relayout_nodes()
        self.touch()
        return True

    def _relayout_nodes(self) -> None:
        by_step = {node.step_id: node for node in self.nodes}
        laid_out: list[Node] = []
        for index, step in enumerate(self.steps):
            node = by_step.get(step.id) or Node.create(step.id)
            node.x = 40.0
            node.y = 24.0 + index * 96.0
            laid_out.append(node)
        self.nodes = laid_out

    def step_by_id(self, step_id: str) -> Step | None:
        return next((step for step in self.steps if step.id == step_id), None)

    def node_for_step(self, step_id: str) -> Node | None:
        return next((node for node in self.nodes if node.step_id == step_id), None)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "steps": [step.to_dict() for step in self.steps],
            "nodes": [node.to_dict() for node in self.nodes],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Workflow:
        return cls(
            id=data["id"],
            name=data["name"],
            steps=[Step.from_dict(item) for item in data.get("steps", [])],
            nodes=[Node.from_dict(item) for item in data.get("nodes", [])],
            created_at=data.get("created_at", _utc_now_iso()),
            updated_at=data.get("updated_at", data.get("created_at", _utc_now_iso())),
        )
