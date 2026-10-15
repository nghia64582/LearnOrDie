"""Unit tests for WorkflowService."""

from pathlib import Path
import tempfile
import unittest

from models.node import Node, Position
from models.node_definitions import NODE_TYPE_CLICK_IMAGE
from models.workflow import Workflow
from services.workflow_service import WorkflowService
from storage.exceptions import WorkflowCollisionError
from storage.workflow_repository import WorkflowRepository


class TestWorkflowService(unittest.TestCase):
    """Test suite for WorkflowService."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.temp_dir.name)
        self.repo = WorkflowRepository(self.repo_dir)
        self.service = WorkflowService(self.repo)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initial_state(self) -> None:
        self.assertIsNone(self.service.current_workflow)
        self.assertIsNone(self.service.current_file_path)
        self.assertFalse(self.service.is_dirty)

    def test_create_workflow(self) -> None:
        wf = self.service.create_workflow("My Flow", "Flow Description")
        self.assertIsNotNone(wf)
        self.assertEqual(self.service.current_workflow, wf)
        self.assertIsNone(self.service.current_file_path)
        self.assertTrue(self.service.is_dirty)
        self.assertEqual(len(wf.nodes), 1)
        self.assertEqual(wf.nodes[0].type, "START")

    def test_save_marks_clean_only_after_successful_save(self) -> None:
        self.service.create_workflow("Flow 1")
        self.assertTrue(self.service.is_dirty)

        saved_path = self.service.save_workflow()
        self.assertEqual(saved_path.name, "Flow_1.json")
        self.assertFalse(self.service.is_dirty)
        self.assertEqual(self.service.current_file_path, saved_path)

        # Mark dirty again after modification
        self.service.current_workflow.add_node(
            Node.create(NODE_TYPE_CLICK_IMAGE, position=Position(100, 100))
        )
        self.service.mark_dirty()
        self.assertTrue(self.service.is_dirty)

        # Save again
        self.service.save_workflow()
        self.assertFalse(self.service.is_dirty)

    def test_open_workflow(self) -> None:
        # Save a workflow first
        wf = Workflow.create_default("Stored Flow")
        file_path = self.repo.save(wf)

        opened = self.service.open_workflow(file_path)
        self.assertEqual(opened.workflow.id, wf.workflow.id)
        self.assertEqual(self.service.current_workflow, opened)
        self.assertEqual(self.service.current_file_path, file_path)
        self.assertFalse(self.service.is_dirty)

    def test_save_as_creates_new_id_and_does_not_overwrite(self) -> None:
        self.service.create_workflow("Original Flow")
        orig_path = self.service.save_workflow()
        orig_id = self.service.current_workflow.workflow.id

        # Save As with new name
        save_as_path = self.service.save_as("Cloned Flow")
        self.assertTrue(orig_path.is_file())
        self.assertTrue(save_as_path.is_file())
        self.assertNotEqual(orig_path, save_as_path)

        # ID must be different
        self.assertNotEqual(self.service.current_workflow.workflow.id, orig_id)
        self.assertEqual(self.service.current_workflow.workflow.name, "Cloned Flow")
        self.assertFalse(self.service.is_dirty)

        # Trying to Save As to an existing file name must raise collision
        with self.assertRaises(WorkflowCollisionError):
            self.service.save_as("Original Flow")

    def test_rename_workflow_persisted(self) -> None:
        self.service.create_workflow("First Name")
        first_path = self.service.save_workflow()

        new_path = self.service.rename_workflow("Second Name")
        self.assertFalse(first_path.exists())
        self.assertTrue(new_path.exists())
        self.assertEqual(new_path.name, "Second_Name.json")
        self.assertEqual(self.service.current_workflow.workflow.name, "Second Name")
        self.assertFalse(self.service.is_dirty)

    def test_rename_workflow_collision_rejected(self) -> None:
        # Create flow 1
        wf1 = Workflow.create_default("Existing Target")
        self.repo.save(wf1)

        # Create flow 2 in service
        self.service.create_workflow("Flow To Rename")
        self.service.save_workflow()

        with self.assertRaises(WorkflowCollisionError):
            self.service.rename_workflow("Existing Target")

    def test_rename_unsaved_workflow(self) -> None:
        self.service.create_workflow("Unsaved Flow")
        result = self.service.rename_workflow("Renamed Unsaved")
        self.assertIsNone(result)
        self.assertEqual(self.service.current_workflow.workflow.name, "Renamed Unsaved")
        self.assertTrue(self.service.is_dirty)

    def test_duplicate_workflow(self) -> None:
        wf = Workflow.create_default("Template Flow")
        tpl_path = self.repo.save(wf)

        dup_path = self.service.duplicate_workflow(tpl_path, "Instance Flow")
        self.assertTrue(tpl_path.exists())
        self.assertTrue(dup_path.exists())

        loaded_dup = self.repo.load(dup_path)
        self.assertNotEqual(loaded_dup.workflow.id, wf.workflow.id)
        self.assertEqual(loaded_dup.workflow.name, "Instance Flow")

        # Duplicate to existing name raises collision error
        with self.assertRaises(WorkflowCollisionError):
            self.service.duplicate_workflow(tpl_path, "Instance Flow")

    def test_delete_workflow_active(self) -> None:
        self.service.create_workflow("Active To Delete")
        saved_path = self.service.save_workflow()

        self.service.delete_workflow(saved_path)
        self.assertFalse(saved_path.exists())
        self.assertIsNone(self.service.current_workflow)
        self.assertIsNone(self.service.current_file_path)
        self.assertFalse(self.service.is_dirty)


if __name__ == "__main__":
    unittest.main()
