"""Workflow repository for JSON file persistence."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from models.exceptions import ModelError
from models.workflow import Workflow, current_iso_timestamp
from storage.exceptions import (
    CorruptWorkflowError,
    WorkflowCollisionError,
    WorkflowNotFoundError,
)

# Invalid characters for filenames on Windows and general OS
INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename(name: str) -> str:
    """Sanitize a workflow name into a safe, valid filesystem filename without extension."""
    cleaned = INVALID_CHARS_PATTERN.sub("_", name)
    cleaned = cleaned.strip(". ")
    cleaned = re.sub(r"\s+", "_", cleaned)
    if not cleaned:
        cleaned = "untitled_workflow"
    if cleaned.upper() in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned


@dataclass
class WorkflowSummary:
    """Lightweight summary of a workflow file for listings."""

    file_path: Path
    id: str = ""
    name: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    is_corrupted: bool = False
    error_message: Optional[str] = None


class WorkflowRepository:
    """Handles loading, saving, listing, renaming, and deleting workflow JSON files."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_path_for_name(self, name: str) -> Path:
        """Derive standard .json file path from workflow name."""
        safe_name = sanitize_filename(name)
        return self.base_dir / f"{safe_name}.json"

    def ensure_sample_workflow(self) -> Path:
        """Create sample branching workflow login_dashboard.json if it does not exist."""
        sample_path = self.base_dir / "login_dashboard.json"
        if not sample_path.exists():
            sample_content = {
                "schema_version": 1,
                "workflow": {
                    "id": "wf_login_dashboard",
                    "name": "Login and Check Dashboard",
                    "description": "Example branching workflow with CHECK_IMAGE",
                    "created_at": current_iso_timestamp(),
                    "updated_at": current_iso_timestamp(),
                },
                "nodes": [
                    {"id": "start_1", "type": "START", "name": "Start", "params": {}, "position": {"x": 300.0, "y": 60.0}},
                    {"id": "check_1", "type": "CHECK_IMAGE", "name": "Dashboard visible?", "params": {"image_id": "dashboard", "threshold": 0.85}, "position": {"x": 300.0, "y": 180.0}},
                    {"id": "click_1", "type": "CLICK_IMAGE", "name": "Click dashboard", "params": {"image_id": "dashboard", "offset_x": 0.0, "offset_y": 0.0}, "position": {"x": 160.0, "y": 340.0}},
                    {"id": "wait_1", "type": "WAIT_IMAGE", "name": "Wait for dashboard", "params": {"image_id": "dashboard", "condition": "appear", "timeout_ms": 10000, "poll_interval_ms": 300}, "position": {"x": 460.0, "y": 340.0}},
                    {"id": "end_1", "type": "END", "name": "Done", "params": {}, "position": {"x": 160.0, "y": 490.0}},
                    {"id": "end_2", "type": "END", "name": "Wait completed", "params": {}, "position": {"x": 460.0, "y": 490.0}},
                ],
                "edges": [
                    {"id": "edge_1", "source": "start_1", "source_port": "next", "target": "check_1", "target_port": "in"},
                    {"id": "edge_2", "source": "check_1", "source_port": "true", "target": "click_1", "target_port": "in"},
                    {"id": "edge_3", "source": "check_1", "source_port": "false", "target": "wait_1", "target_port": "in"},
                    {"id": "edge_4", "source": "click_1", "source_port": "success", "target": "end_1", "target_port": "in"},
                    {"id": "edge_5", "source": "wait_1", "source_port": "success", "target": "end_2", "target_port": "in"},
                ],
                "view": {"zoom": 1.0, "pan_x": 50.0, "pan_y": 30.0},
            }
            sample_path.write_text(json.dumps(sample_content, indent=2), encoding="utf-8")
        return sample_path

    def list_workflows(self) -> list[WorkflowSummary]:
        """List all workflow files in base_dir.

        Corrupted files are reported with is_corrupted=True without crashing.
        """
        summaries: list[WorkflowSummary] = []
        for file_path in sorted(self.base_dir.glob("*.json")):
            if file_path.name.startswith(".tmp_"):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("Root JSON is not an object")

                wf_meta = data.get("workflow", {})
                if not isinstance(wf_meta, dict):
                    raise ValueError("'workflow' field is not an object")

                wf_id = wf_meta.get("id", "")
                name = wf_meta.get("name", file_path.stem)
                desc = wf_meta.get("description", "")
                created_at = wf_meta.get("created_at", "")
                updated_at = wf_meta.get("updated_at", "")

                summaries.append(
                    WorkflowSummary(
                        file_path=file_path,
                        id=str(wf_id),
                        name=str(name),
                        description=str(desc),
                        created_at=str(created_at),
                        updated_at=str(updated_at),
                        is_corrupted=False,
                    )
                )
            except Exception as err:
                summaries.append(
                    WorkflowSummary(
                        file_path=file_path,
                        name=file_path.stem,
                        is_corrupted=True,
                        error_message=f"Failed to read workflow: {err}",
                    )
                )

        return summaries

    def load(self, file_path: Path | str) -> Workflow:
        """Load and parse a workflow JSON file.

        Raises WorkflowNotFoundError if file does not exist.
        Raises CorruptWorkflowError if content is malformed or invalid schema.
        """
        path = Path(file_path).resolve()
        if not path.is_file():
            raise WorkflowNotFoundError(f"Workflow file not found: '{path}'")

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as err:
            raise CorruptWorkflowError(f"Cannot read file '{path.name}': {err}") from err

        try:
            return Workflow.from_json(content)
        except (json.JSONDecodeError, ModelError) as err:
            raise CorruptWorkflowError(
                f"Corrupt or invalid workflow file '{path.name}': {err}"
            ) from err

    def save(
        self,
        workflow: Workflow,
        file_path: Optional[Path | str] = None,
        allow_overwrite_same_id: bool = True,
    ) -> Path:
        """Save workflow atomically using temporary file + replace.

        Updates updated_at timestamp.
        Prevents silently overwriting a file belonging to another workflow ID.
        """
        if file_path is None:
            target_path = self.get_path_for_name(workflow.workflow.name)
        else:
            target_path = Path(file_path).resolve()

        # Collision detection: if file already exists, check who it belongs to
        if target_path.is_file():
            if not allow_overwrite_same_id:
                raise WorkflowCollisionError(
                    f"File '{target_path.name}' already exists and overwrite is disabled"
                )

            # Check if target file contains a different workflow ID
            try:
                existing_content = target_path.read_text(encoding="utf-8")
                existing_data = json.loads(existing_content)
                existing_id = (
                    existing_data.get("workflow", {}).get("id")
                    if isinstance(existing_data, dict)
                    else None
                )
                if existing_id and existing_id != workflow.workflow.id:
                    raise WorkflowCollisionError(
                        f"Target file '{target_path.name}' already belongs to another workflow (ID: {existing_id}). "
                        "Cannot overwrite."
                    )
            except WorkflowCollisionError:
                raise
            except Exception:
                # If existing file is corrupt, allow overwriting with valid save
                pass

        # Update updated_at timestamp on save
        workflow.workflow.updated_at = current_iso_timestamp()
        content = workflow.to_json(indent=2)

        # Atomic write via temporary file in same directory
        temp_path = target_path.parent / f".tmp_{uuid.uuid4().hex}_{target_path.name}"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            # Atomic replace
            os.replace(temp_path, target_path)
            return target_path
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def rename(
        self,
        file_path: Path | str,
        new_name: str,
        workflow: Optional[Workflow] = None,
    ) -> tuple[Path, Workflow]:
        """Rename a workflow and its corresponding file without colliding."""
        source_path = Path(file_path).resolve()
        if not source_path.is_file():
            raise WorkflowNotFoundError(f"Workflow file not found: '{source_path}'")

        if workflow is None:
            workflow = self.load(source_path)

        new_target_path = self.get_path_for_name(new_name)

        if new_target_path == source_path:
            workflow.workflow.name = new_name
            self.save(workflow, source_path)
            return source_path, workflow

        if new_target_path.is_file():
            raise WorkflowCollisionError(
                f"Cannot rename: target file '{new_target_path.name}' already exists."
            )

        workflow.workflow.name = new_name
        # Save to new path
        self.save(workflow, new_target_path)
        # Remove old path
        try:
            source_path.unlink()
        except OSError:
            pass

        return new_target_path, workflow

    def delete(self, file_path: Path | str) -> None:
        """Delete a workflow file from disk."""
        target_path = Path(file_path).resolve()
        if not target_path.is_file():
            raise WorkflowNotFoundError(f"Cannot delete non-existent file: '{target_path}'")
        target_path.unlink()
