"""Workflow application service for managing workflow lifecycle and state."""

from __future__ import annotations

import copy
import uuid
from pathlib import Path
from typing import Optional

from models.workflow import Workflow, WorkflowMeta, current_iso_timestamp
from storage.exceptions import WorkflowCollisionError
from storage.workflow_repository import WorkflowRepository, WorkflowSummary


class WorkflowService:
    """Service layer managing active workflow state, persistence, and CRUD operations."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository
        self.current_workflow: Optional[Workflow] = None
        self.current_file_path: Optional[Path] = None
        self._is_dirty: bool = False

    @property
    def is_dirty(self) -> bool:
        """Return True if active workflow has unsaved changes."""
        return self._is_dirty

    def mark_dirty(self) -> None:
        """Mark active workflow as containing unsaved changes."""
        self._is_dirty = True

    def mark_clean(self) -> None:
        """Mark active workflow as clean (saved)."""
        self._is_dirty = False

    def list_workflows(self) -> list[WorkflowSummary]:
        """List all workflows available in the repository."""
        return self.repository.list_workflows()

    def create_workflow(self, name: str = "New Workflow", description: str = "") -> Workflow:
        """Create a new workflow with default START node and activate it."""
        wf = Workflow.create_default(name=name, description=description)
        self.current_workflow = wf
        self.current_file_path = None
        self._is_dirty = True
        return wf

    def open_workflow(self, file_path: Path | str) -> Workflow:
        """Load and activate a workflow from file."""
        resolved_path = Path(file_path).resolve()
        wf = self.repository.load(resolved_path)
        self.current_workflow = wf
        self.current_file_path = resolved_path
        self._is_dirty = False
        return wf

    def save_workflow(self, file_path: Optional[Path | str] = None) -> Path:
        """Save the active workflow to disk.

        Marks workflow clean only after successful save.
        """
        if self.current_workflow is None:
            raise ValueError("No active workflow to save")

        target_path = file_path if file_path is not None else self.current_file_path
        saved_path = self.repository.save(self.current_workflow, target_path)

        self.current_file_path = saved_path
        # Mark workflow clean ONLY after successful save
        self._is_dirty = False
        return saved_path

    def save_as(self, new_name: str) -> Path:
        """Save the active workflow as a new workflow with a new ID and name.

        Prevents overwriting another workflow file.
        """
        if self.current_workflow is None:
            raise ValueError("No active workflow to save as")

        target_path = self.repository.get_path_for_name(new_name)
        if target_path.is_file():
            raise WorkflowCollisionError(
                f"Cannot Save As: target file '{target_path.name}' already exists"
            )

        now = current_iso_timestamp()
        new_meta = WorkflowMeta(
            id=str(uuid.uuid4()),
            name=new_name,
            description=self.current_workflow.workflow.description,
            created_at=now,
            updated_at=now,
        )

        cloned_wf = Workflow(
            schema_version=self.current_workflow.schema_version,
            workflow=new_meta,
            nodes=copy.deepcopy(self.current_workflow.nodes),
            edges=copy.deepcopy(self.current_workflow.edges),
            view=copy.deepcopy(self.current_workflow.view),
        )

        saved_path = self.repository.save(cloned_wf, target_path)
        self.current_workflow = cloned_wf
        self.current_file_path = saved_path
        self._is_dirty = False
        return saved_path

    def rename_workflow(self, new_name: str) -> Optional[Path]:
        """Rename the active workflow and its file if already saved.

        Does not silently overwrite an existing workflow file.
        """
        if self.current_workflow is None:
            raise ValueError("No active workflow to rename")

        if self.current_file_path is not None:
            new_path, updated_wf = self.repository.rename(
                self.current_file_path, new_name, self.current_workflow
            )
            self.current_workflow = updated_wf
            self.current_file_path = new_path
            self._is_dirty = False
            return new_path
        else:
            self.current_workflow.workflow.name = new_name
            self._is_dirty = True
            return None

    def duplicate_workflow(self, file_path: Path | str, new_name: str) -> Path:
        """Duplicate a stored workflow to a new file with a fresh ID without overwriting."""
        source_path = Path(file_path).resolve()
        target_path = self.repository.get_path_for_name(new_name)

        if target_path.is_file():
            raise WorkflowCollisionError(
                f"Cannot duplicate: target file '{target_path.name}' already exists"
            )

        source_wf = self.repository.load(source_path)
        now = current_iso_timestamp()
        new_meta = WorkflowMeta(
            id=str(uuid.uuid4()),
            name=new_name,
            description=source_wf.workflow.description,
            created_at=now,
            updated_at=now,
        )

        cloned_wf = Workflow(
            schema_version=source_wf.schema_version,
            workflow=new_meta,
            nodes=copy.deepcopy(source_wf.nodes),
            edges=copy.deepcopy(source_wf.edges),
            view=copy.deepcopy(source_wf.view),
        )

        return self.repository.save(cloned_wf, target_path)

    def delete_workflow(self, file_path: Path | str) -> None:
        """Delete a workflow file and reset active state if it was open."""
        resolved = Path(file_path).resolve()
        self.repository.delete(resolved)

        if self.current_file_path and self.current_file_path.resolve() == resolved:
            self.current_workflow = None
            self.current_file_path = None
            self._is_dirty = False
