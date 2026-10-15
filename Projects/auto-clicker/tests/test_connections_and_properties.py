"""Unit tests for Milestone 4: Connection interaction and Properties panel."""

import tkinter as tk
import unittest

from app.app_state import AppState
from models.edge import Edge
from models.node import Node, Position
from models.node_definitions import (
    NODE_TYPE_CHECK_IMAGE,
    NODE_TYPE_CLICK_IMAGE,
    NODE_TYPE_END,
    NODE_TYPE_START,
    NODE_TYPE_WAIT_IMAGE,
)
from models.workflow import Workflow
from services.workflow_service import WorkflowService
from storage.workflow_repository import WorkflowRepository
from ui.properties_panel import PropertiesPanel
from ui.workflow_canvas import WorkflowCanvas


class TestConnectionLogic(unittest.TestCase):
    """Test connection validation and cardinality rules on the canvas."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.repo = WorkflowRepository("data/workflows")
        self.service = WorkflowService(self.repo)
        self.app_state = AppState(self.service)
        self.wf = self.service.create_workflow("Connection Test")
        self.service.mark_clean()
        self.canvas = WorkflowCanvas(self.root, app_state=self.app_state)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_valid_connection_adds_edge_and_marks_dirty(self) -> None:
        start_node = self.wf.nodes[0]
        check_node = Node.create(NODE_TYPE_CHECK_IMAGE, position=Position(300, 200))
        self.wf.add_node(check_node)

        self.assertFalse(self.app_state.is_dirty)
        success = self.canvas.try_connect(start_node.id, "next", check_node.id, "in")
        self.assertTrue(success)
        self.assertEqual(len(self.wf.edges), 1)

        edge = self.wf.edges[0]
        self.assertEqual(edge.source, start_node.id)
        self.assertEqual(edge.source_port, "next")
        self.assertEqual(edge.target, check_node.id)
        self.assertEqual(edge.target_port, "in")

        # Connection should mark workflow dirty and select edge
        self.assertTrue(self.app_state.is_dirty)
        self.assertEqual(self.app_state.selected_edge_id, edge.id)

    def test_reject_self_connection(self) -> None:
        check_node = Node.create(NODE_TYPE_CHECK_IMAGE, position=Position(100, 100))
        self.wf.add_node(check_node)

        success = self.canvas.try_connect(check_node.id, "true", check_node.id, "in")
        self.assertFalse(success)
        self.assertEqual(len(self.wf.edges), 0)

    def test_reject_connecting_to_start_node(self) -> None:
        start_node = self.wf.nodes[0]
        click_node = Node.create(NODE_TYPE_CLICK_IMAGE, position=Position(100, 100))
        self.wf.add_node(click_node)

        # START has no input port, so trying to connect into START must fail
        success = self.canvas.try_connect(click_node.id, "success", start_node.id, "in")
        self.assertFalse(success)
        self.assertEqual(len(self.wf.edges), 0)

    def test_reject_cardinality_exceeded(self) -> None:
        start_node = self.wf.nodes[0]
        check1 = Node.create(NODE_TYPE_CHECK_IMAGE, position=Position(200, 200))
        check2 = Node.create(NODE_TYPE_CHECK_IMAGE, position=Position(400, 200))
        self.wf.add_node(check1)
        self.wf.add_node(check2)

        # First connection from start_node.next -> check1.in succeeds
        first = self.canvas.try_connect(start_node.id, "next", check1.id, "in")
        self.assertTrue(first)

        # Second connection from same start_node.next -> check2.in must be rejected
        second = self.canvas.try_connect(start_node.id, "next", check2.id, "in")
        self.assertFalse(second)
        self.assertEqual(len(self.wf.edges), 1)

    def test_reject_duplicate_connection(self) -> None:
        start_node = self.wf.nodes[0]
        end_node = Node.create(NODE_TYPE_END, position=Position(300, 200))
        self.wf.add_node(end_node)

        first = self.canvas.try_connect(start_node.id, "next", end_node.id, "in")
        self.assertTrue(first)

        # Exact duplicate
        second = self.canvas.try_connect(start_node.id, "next", end_node.id, "in")
        self.assertFalse(second)
        self.assertEqual(len(self.wf.edges), 1)

    def test_escape_cancels_connecting_mode(self) -> None:
        self.canvas._connecting_source = ("some_id", "next")
        self.canvas._preview_wire_pos = (100.0, 150.0)

        # Trigger escape
        event = tk.Event()
        self.canvas._on_escape_key(event)

        self.assertIsNone(self.canvas._connecting_source)
        self.assertIsNone(self.canvas._preview_wire_pos)


class TestPropertiesPanel(unittest.TestCase):
    """Test PropertiesPanel editing and cascade actions."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.repo = WorkflowRepository("data/workflows")
        self.service = WorkflowService(self.repo)
        self.app_state = AppState(self.service)
        self.wf = self.service.create_workflow("Properties Test")
        self.service.mark_clean()
        self.panel = PropertiesPanel(self.root, app_state=self.app_state)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_edit_node_name_updates_model_and_marks_dirty(self) -> None:
        node = self.wf.nodes[0]
        self.app_state.select_node(node.id)
        self.panel.refresh()

        self.panel.name_var.set("Renamed Start")
        self.panel._on_name_commit(node)

        self.assertEqual(node.name, "Renamed Start")
        self.assertTrue(self.app_state.is_dirty)

    def test_edit_typed_params_updates_model(self) -> None:
        check_node = Node.create(
            NODE_TYPE_CHECK_IMAGE,
            params={"image_id": "btn.png", "threshold": 0.85},
        )
        self.wf.add_node(check_node)
        self.app_state.select_node(check_node.id)
        self.panel.refresh()

        defn = check_node.type
        # Modify string param
        self.panel._param_vars["image_id"].set("logo.png")
        self.panel._on_param_commit(
            check_node,
            "image_id",
            self.panel.app_state.get_selected_node().__class__,  # dummy
        )
        from models.node_definitions import get_node_definition

        check_defn = get_node_definition(NODE_TYPE_CHECK_IMAGE)
        self.panel._on_param_commit(
            check_node, "image_id", check_defn.parameters["image_id"]
        )
        self.assertEqual(check_node.params["image_id"], "logo.png")

        # Modify float param with clamping
        self.panel._param_vars["threshold"].set("0.95")
        self.panel._on_param_commit(
            check_node, "threshold", check_defn.parameters["threshold"]
        )
        self.assertEqual(check_node.params["threshold"], 0.95)

    def test_delete_edge_via_properties(self) -> None:
        start_node = self.wf.nodes[0]
        end_node = Node.create(NODE_TYPE_END)
        self.wf.add_node(end_node)
        edge = Edge(source=start_node.id, source_port="next", target=end_node.id)
        self.wf.add_edge(edge)

        self.app_state.select_edge(edge.id)
        self.panel.refresh()

        self.panel._on_delete_edge(edge)
        self.assertEqual(len(self.wf.edges), 0)
        self.assertIsNone(self.app_state.selected_edge_id)
        self.assertTrue(self.app_state.is_dirty)


if __name__ == "__main__":
    unittest.main()
