"""Unit tests for canvas coordinate math, port geometry, and AppState."""

import unittest

from app.app_state import AppState
from models.edge import Edge
from models.node import Node, Position
from models.node_definitions import (
    NODE_TYPE_CHECK_IMAGE,
    NODE_TYPE_END,
    NODE_TYPE_START,
    NODE_TYPE_WAIT_IMAGE,
)
from models.workflow import Workflow
from services.workflow_service import WorkflowService
from storage.workflow_repository import WorkflowRepository
from ui.workflow_canvas import (
    NODE_MIN_HEIGHT,
    NODE_WIDTH,
    WorkflowCanvas,
)


class TestAppState(unittest.TestCase):
    """Test AppState event dispatch and selection tracking."""

    def setUp(self) -> None:
        # Dummy repository
        repo = WorkflowRepository("data/workflows")
        self.service = WorkflowService(repo)
        self.app_state = AppState(self.service)

    def test_selection_node_and_edge(self) -> None:
        wf = self.service.create_workflow("Test Flow")
        node = wf.nodes[0]
        edge = Edge(id="e1", source=node.id, source_port="next", target="n2")
        wf.add_edge(edge)

        events_received = []
        self.app_state.add_listener(
            "selection_changed", lambda nid, eid: events_received.append((nid, eid))
        )

        # Select node
        self.app_state.select_node(node.id)
        self.assertEqual(self.app_state.selected_node_id, node.id)
        self.assertIsNone(self.app_state.selected_edge_id)
        self.assertEqual(self.app_state.get_selected_node(), node)
        self.assertEqual(events_received[-1], (node.id, None))

        # Select edge
        self.app_state.select_edge(edge.id)
        self.assertEqual(self.app_state.selected_edge_id, edge.id)
        self.assertIsNone(self.app_state.selected_node_id)
        self.assertEqual(self.app_state.get_selected_edge(), edge)
        self.assertEqual(events_received[-1], (None, edge.id))

        # Clear selection
        self.app_state.clear_selection()
        self.assertIsNone(self.app_state.selected_node_id)
        self.assertIsNone(self.app_state.selected_edge_id)
        self.assertEqual(events_received[-1], (None, None))

    def test_toolbox_pending_node(self) -> None:
        events = []
        self.app_state.add_listener("toolbox_changed", lambda t: events.append(t))

        self.app_state.set_pending_node_type(NODE_TYPE_CHECK_IMAGE)
        self.assertEqual(self.app_state.pending_node_type, NODE_TYPE_CHECK_IMAGE)
        self.assertEqual(events[-1], NODE_TYPE_CHECK_IMAGE)

        self.app_state.set_pending_node_type(None)
        self.assertIsNone(self.app_state.pending_node_type)
        self.assertEqual(events[-1], None)

    def test_dirty_notification(self) -> None:
        self.service.create_workflow("Test Dirty")
        self.service.mark_clean()

        dirty_events = []
        self.app_state.add_listener("dirty_changed", lambda d: dirty_events.append(d))

        self.app_state.notify_workflow_modified()
        self.assertTrue(self.app_state.is_dirty)
        self.assertEqual(dirty_events, [True])


class TestCanvasGeometryMath(unittest.TestCase):
    """Test canvas coordinate transforms and port calculations."""

    def test_coordinate_transforms(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            repo = WorkflowRepository("data/workflows")
            service = WorkflowService(repo)
            state = AppState(service)
            wf = service.create_workflow()
            wf.view.zoom = 1.5
            wf.view.pan_x = 100.0
            wf.view.pan_y = 50.0

            canvas = WorkflowCanvas(root, app_state=state)

            # Logic to Screen
            sx, sy = canvas.logic_to_screen(200.0, 100.0)
            self.assertEqual(sx, 200.0 * 1.5 + 100.0)  # 400.0
            self.assertEqual(sy, 100.0 * 1.5 + 50.0)   # 200.0

            # Screen to Logic
            lx, ly = canvas.screen_to_logic(sx, sy)
            self.assertAlmostEqual(lx, 200.0)
            self.assertAlmostEqual(ly, 100.0)

            # Node height
            start_node = wf.nodes[0]
            self.assertGreaterEqual(canvas.get_node_height(start_node), NODE_MIN_HEIGHT)

            # Port calculations
            # Output 'next' port on START node (right edge)
            out_pos = canvas.get_port_logic_pos(start_node.id, "next", is_output=True)
            self.assertIsNotNone(out_pos)
            self.assertEqual(out_pos[0], start_node.position.x + NODE_WIDTH)

            # Check Condition node ports
            check_node = Node.create(
                NODE_TYPE_CHECK_IMAGE, position=Position(100.0, 200.0)
            )
            wf.add_node(check_node)

            in_pos = canvas.get_port_logic_pos(check_node.id, "in", is_output=False)
            self.assertIsNotNone(in_pos)
            self.assertEqual(in_pos[0], 100.0)  # Left edge

            true_pos = canvas.get_port_logic_pos(check_node.id, "true", is_output=True)
            false_pos = canvas.get_port_logic_pos(check_node.id, "false", is_output=True)
            self.assertIsNotNone(true_pos)
            self.assertIsNotNone(false_pos)
            self.assertEqual(true_pos[0], 100.0 + NODE_WIDTH)
            self.assertEqual(false_pos[0], 100.0 + NODE_WIDTH)
            # 'true' should be above 'false' in vertical order
            self.assertLess(true_pos[1], false_pos[1])
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
