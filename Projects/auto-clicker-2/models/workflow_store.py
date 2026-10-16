from __future__ import annotations

import json
from pathlib import Path

from app.paths import WORKFLOWS_DIR, ensure_data_dirs
from models.workflow import Workflow


class WorkflowStore:
    def __init__(self, workflows_dir: Path | None = None) -> None:
        self.workflows_dir = workflows_dir or WORKFLOWS_DIR
        ensure_data_dirs()
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

    def all(self) -> list[Workflow]:
        workflows = [self._load_file(path) for path in self.workflows_dir.glob("*.json")]
        return sorted(
            [item for item in workflows if item is not None],
            key=lambda item: item.name.lower(),
        )

    def get(self, workflow_id: str) -> Workflow | None:
        path = self._path(workflow_id)
        if not path.exists():
            return None
        return self._load_file(path)

    def save(self, workflow: Workflow) -> None:
        workflow.touch()
        path = self._path(workflow.id)
        path.write_text(
            json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def delete(self, workflow_id: str) -> None:
        path = self._path(workflow_id)
        if path.exists():
            path.unlink()

    def _path(self, workflow_id: str) -> Path:
        return self.workflows_dir / f"{workflow_id}.json"

    def _load_file(self, path: Path) -> Workflow | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Workflow.from_dict(data)
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return None
