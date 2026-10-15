"""Unit tests for WorkflowRepository."""

import json
from pathlib import Path
import tempfile
import unittest

from models.node import Node, Position
from models.node_definitions import NODE_TYPE_CHECK_IMAGE, NODE_TYPE_START
from models.workflow import Workflow, WorkflowMeta
from storage.exceptions import (
    CorruptWorkflowError,
    WorkflowCollisionError,
    WorkflowNotFoundError,
)
from storage.workflow_repository import (
    WorkflowRepository,
    sanitize_filename,
)


class TestWorkflowRepository(unittest.TestCase):
    """Test suite for WorkflowRepository."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.temp_dir.name)
        self.repo = WorkflowRepository(self.repo_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_sanitize_filename(self) -> None:
        self.assertEqual(sanitize_filename("My:Cool/Workflow?*"), "My_Cool_Workflow__")
        self.assertEqual(sanitize_filename("   spaced   "), "spaced")
        self.assertEqual(sanitize_filename("...dots..."), "dots")
        self.assertEqual(sanitize_filename(""), "untitled_workflow")
        self.assertEqual(sanitize_filename("CON"), "_CON")
        self.assertEqual(sanitize_filename("NUL"), "_NUL")

    def test_save_and_load_roundtrip(self) -> None:
        wf = Workflow.create_default("Test Flow", "Description here")
        check_node = Node.create(
            NODE_TYPE_CHECK_IMAGE,
            name="Check It",
            position=Position(200, 150),
            params={"image_id": "btn.png", "threshold": 0.8},
        )
        wf.add_node(check_node)

        saved_path = self.repo.save(wf)
        self.assertTrue(saved_path.is_file())
        self.assertEqual(saved_path.name, "Test_Flow.json")

        # Ensure no temp files remained
        tmp_files = list(self.repo_dir.glob(".tmp_*"))
        self.assertEqual(len(tmp_files), 0)

        # Load back
        loaded_wf = self.repo.load(saved_path)
        self.assertEqual(loaded_wf.schema_version, 1)
        self.assertEqual(loaded_wf.workflow.id, wf.workflow.id)
        self.assertEqual(loaded_wf.workflow.name, "Test Flow")
        self.assertEqual(len(loaded_wf.nodes), 2)
        self.assertEqual(loaded_wf.get_node(check_node.id).params["threshold"], 0.8)

    def test_save_overwrites_same_workflow_id(self) -> None:
        wf = Workflow.create_default("Original Name")
        path1 = self.repo.save(wf)

        # Modify workflow
        wf.workflow.description = "Updated description"
        path2 = self.repo.save(wf, path1)

        self.assertEqual(path1, path2)
        reloaded = self.repo.load(path1)
        self.assertEqual(reloaded.workflow.description, "Updated description")

    def test_save_rejects_silent_overwrite_of_different_workflow(self) -> None:
        wf1 = Workflow.create_default("Shared Name")
        path1 = self.repo.save(wf1)

        wf2 = Workflow.create_default("Shared Name")  # different ID
        self.assertNotEqual(wf1.workflow.id, wf2.workflow.id)

        # Attempting to save wf2 to the same target file must raise collision
        with self.assertRaises(WorkflowCollisionError):
            self.repo.save(wf2, path1)

    def test_load_non_existent_file_raises_not_found(self) -> None:
        with self.assertRaises(WorkflowNotFoundError):
            self.repo.load(self.repo_dir / "non_existent.json")

    def test_corrupt_json_produces_actionable_error(self) -> None:
        bad_file = self.repo_dir / "broken.json"
        bad_file.write_text("{ this is invalid json : [", encoding="utf-8")

        with self.assertRaises(CorruptWorkflowError) as ctx:
            self.repo.load(bad_file)
        self.assertIn("broken.json", str(ctx.exception))

    def test_invalid_schema_in_json_produces_actionable_error(self) -> None:
        bad_schema = self.repo_dir / "bad_schema.json"
        bad_schema.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")

        with self.assertRaises(CorruptWorkflowError) as ctx:
            self.repo.load(bad_schema)
        self.assertIn("bad_schema.json", str(ctx.exception))

    def test_list_workflows_handles_corrupt_files_without_crashing(self) -> None:
        # Create 1 valid workflow
        wf = Workflow.create_default("Healthy Workflow")
        self.repo.save(wf)

        # Create 1 corrupt workflow
        bad_file = self.repo_dir / "corrupted.json"
        bad_file.write_text("not json content", encoding="utf-8")

        summaries = self.repo.list_workflows()
        self.assertEqual(len(summaries), 2)

        healthy = next(s for s in summaries if not s.is_corrupted)
        self.assertEqual(healthy.name, "Healthy Workflow")
        self.assertEqual(healthy.id, wf.workflow.id)

        corrupted = next(s for s in summaries if s.is_corrupted)
        self.assertEqual(corrupted.file_path.name, "corrupted.json")
        self.assertIsNotNone(corrupted.error_message)

    def test_rename_workflow(self) -> None:
        wf = Workflow.create_default("Old Name")
        old_path = self.repo.save(wf)

        new_path, updated_wf = self.repo.rename(old_path, "New Name")
        self.assertFalse(old_path.exists())
        self.assertTrue(new_path.exists())
        self.assertEqual(new_path.name, "New_Name.json")
        self.assertEqual(updated_wf.workflow.name, "New Name")

    def test_rename_rejects_collision_if_target_exists(self) -> None:
        wf1 = Workflow.create_default("Workflow Alpha")
        alpha_path = self.repo.save(wf1)

        wf2 = Workflow.create_default("Workflow Beta")
        self.repo.save(wf2)

        # Attempt to rename Alpha to Beta
        with self.assertRaises(WorkflowCollisionError):
            self.repo.rename(alpha_path, "Workflow Beta")

        # Verify Alpha still exists
        self.assertTrue(alpha_path.exists())

    def test_delete_workflow(self) -> None:
        wf = Workflow.create_default("To Be Deleted")
        saved_path = self.repo.save(wf)
        self.assertTrue(saved_path.exists())

        self.repo.delete(saved_path)
        self.assertFalse(saved_path.exists())

        # Deleting again raises WorkflowNotFoundError
        with self.assertRaises(WorkflowNotFoundError):
            self.repo.delete(saved_path)


if __name__ == "__main__":
    unittest.main()
