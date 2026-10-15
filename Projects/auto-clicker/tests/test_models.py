"""Unit tests for Milestone 1: Models and node catalog."""

import json
import sys
import unittest
import uuid

from models import (
    CURRENT_SCHEMA_VERSION,
    DuplicateIdError,
    Edge,
    InvalidEdgeError,
    InvalidNodeError,
    InvalidSchemaVersionError,
    ModelError,
    Node,
    Position,
    ViewState,
    Workflow,
    WorkflowMeta,
    get_default_params,
    get_input_ports,
    get_node_definition,
    get_output_ports,
    is_valid_node_type,
)
from models.node_definitions import (
    GROUP_ACTION,
    GROUP_CONDITION,
    GROUP_FLOW,
    NODE_DEFINITIONS,
    NODE_TYPE_CHECK_IMAGE,
    NODE_TYPE_CLICK_IMAGE,
    NODE_TYPE_END,
    NODE_TYPE_PRESS_KEY,
    NODE_TYPE_START,
    NODE_TYPE_TYPE_TEXT,
    NODE_TYPE_WAIT_IMAGE,
    NODE_TYPE_WAIT_TIME,
)


class TestNoTkinterImport(unittest.TestCase):
    """Verify that models package does not import Tkinter."""

    def test_no_tkinter_in_sys_modules(self) -> None:
        import subprocess

        result = subprocess.run(
            [sys.executable, "-c", "import models, sys; assert 'tkinter' not in sys.modules"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Importing models pulled in Tkinter: {result.stderr}",
        )


class TestNodeDefinitions(unittest.TestCase):
    """Test node catalog completeness and correctness."""

    def test_all_catalog_node_types_present(self) -> None:
        expected_types = {
            NODE_TYPE_START,
            NODE_TYPE_END,
            NODE_TYPE_WAIT_IMAGE,
            NODE_TYPE_CLICK_IMAGE,
            NODE_TYPE_TYPE_TEXT,
            NODE_TYPE_PRESS_KEY,
            NODE_TYPE_WAIT_TIME,
            NODE_TYPE_CHECK_IMAGE,
        }
        self.assertEqual(set(NODE_DEFINITIONS.keys()), expected_types)
        for node_type in expected_types:
            self.assertTrue(is_valid_node_type(node_type))

    def test_invalid_node_type(self) -> None:
        self.assertFalse(is_valid_node_type("NON_EXISTENT_TYPE"))
        with self.assertRaises(KeyError):
            get_node_definition("NON_EXISTENT_TYPE")

    def test_start_node_ports_and_group(self) -> None:
        defn = get_node_definition(NODE_TYPE_START)
        self.assertEqual(defn.group, GROUP_FLOW)
        self.assertEqual(defn.input_ports, ())
        self.assertEqual(defn.output_ports, ("next",))
        self.assertEqual(defn.parameters, {})

    def test_end_node_ports_and_group(self) -> None:
        defn = get_node_definition(NODE_TYPE_END)
        self.assertEqual(defn.group, GROUP_FLOW)
        self.assertEqual(defn.input_ports, ("in",))
        self.assertEqual(defn.output_ports, ())
        self.assertEqual(defn.parameters, {})

    def test_check_image_condition_ports_and_params(self) -> None:
        defn = get_node_definition(NODE_TYPE_CHECK_IMAGE)
        self.assertEqual(defn.group, GROUP_CONDITION)
        self.assertEqual(defn.input_ports, ("in",))
        self.assertEqual(defn.output_ports, ("true", "false"))
        self.assertIn("image_id", defn.parameters)
        self.assertIn("threshold", defn.parameters)
        defaults = get_default_params(NODE_TYPE_CHECK_IMAGE)
        self.assertEqual(defaults["threshold"], 0.85)

    def test_wait_image_ports_and_params(self) -> None:
        defn = get_node_definition(NODE_TYPE_WAIT_IMAGE)
        self.assertEqual(defn.group, GROUP_ACTION)
        self.assertEqual(defn.output_ports, ("success", "timeout"))
        defaults = get_default_params(NODE_TYPE_WAIT_IMAGE)
        self.assertEqual(defaults["condition"], "appear")
        self.assertEqual(defaults["timeout_ms"], 10000)
        self.assertEqual(defaults["poll_interval_ms"], 300)

    def test_action_nodes_have_success_failure_ports(self) -> None:
        action_types = [
            NODE_TYPE_CLICK_IMAGE,
            NODE_TYPE_TYPE_TEXT,
            NODE_TYPE_PRESS_KEY,
            NODE_TYPE_WAIT_TIME,
        ]
        for node_type in action_types:
            self.assertEqual(get_input_ports(node_type), ("in",))
            self.assertEqual(get_output_ports(node_type), ("success", "failure"))


class TestNodeModel(unittest.TestCase):
    """Test Node and Position models."""

    def test_create_node_with_defaults(self) -> None:
        node = Node.create(NODE_TYPE_WAIT_TIME)
        self.assertEqual(node.type, NODE_TYPE_WAIT_TIME)
        self.assertEqual(node.name, "Wait Time")
        self.assertEqual(node.params["duration_ms"], 1000)
        self.assertEqual(node.position.x, 0.0)
        self.assertEqual(node.position.y, 0.0)
        # Check valid UUID
        uuid_obj = uuid.UUID(node.id)
        self.assertEqual(str(uuid_obj), node.id)

    def test_create_node_with_custom_values(self) -> None:
        pos = Position(120.5, 340.0)
        node = Node.create(
            NODE_TYPE_TYPE_TEXT,
            name="Type Username",
            position=pos,
            params={"text": "admin"},
        )
        self.assertEqual(node.name, "Type Username")
        self.assertEqual(node.params["text"], "admin")
        self.assertEqual(node.position.x, 120.5)
        self.assertEqual(node.position.y, 340.0)

    def test_create_unknown_node_type_raises(self) -> None:
        with self.assertRaises(InvalidNodeError):
            Node.create("FLY_TO_MOON")

    def test_node_to_dict_and_from_dict_roundtrip(self) -> None:
        node = Node.create(
            NODE_TYPE_CHECK_IMAGE,
            name="Is Logged In?",
            position=Position(300.0, 180.0),
            params={"image_id": "avatar.png", "threshold": 0.9},
        )
        data = node.to_dict()
        restored = Node.from_dict(data)
        self.assertEqual(restored.id, node.id)
        self.assertEqual(restored.type, node.type)
        self.assertEqual(restored.name, node.name)
        self.assertEqual(restored.params, node.params)
        self.assertEqual(restored.position.x, node.position.x)
        self.assertEqual(restored.position.y, node.position.y)

    def test_node_from_dict_malformed_structures(self) -> None:
        # Non-dict data
        with self.assertRaises(InvalidNodeError):
            Node.from_dict("not-a-dict")

        # Missing id
        with self.assertRaises(InvalidNodeError):
            Node.from_dict({"type": "START", "name": "S", "params": {}, "position": {"x": 0, "y": 0}})

        # Unknown type
        with self.assertRaises(InvalidNodeError):
            Node.from_dict({"id": "n1", "type": "INVALID", "name": "X", "params": {}, "position": {"x": 0, "y": 0}})

        # Non-numeric position
        with self.assertRaises(InvalidNodeError):
            Node.from_dict({"id": "n1", "type": "START", "name": "S", "params": {}, "position": {"x": "bad", "y": 0}})

        # Non-dict params
        with self.assertRaises(InvalidNodeError):
            Node.from_dict({"id": "n1", "type": "START", "name": "S", "params": "string", "position": {"x": 0, "y": 0}})


class TestEdgeModel(unittest.TestCase):
    """Test Edge model."""

    def test_edge_creation_and_defaults(self) -> None:
        edge = Edge(source="node-1", source_port="next", target="node-2")
        self.assertEqual(edge.source, "node-1")
        self.assertEqual(edge.source_port, "next")
        self.assertEqual(edge.target, "node-2")
        self.assertEqual(edge.target_port, "in")
        uuid_obj = uuid.UUID(edge.id)
        self.assertEqual(str(uuid_obj), edge.id)

    def test_edge_to_dict_and_from_dict_roundtrip(self) -> None:
        edge = Edge(id="edge-123", source="n1", source_port="true", target="n2", target_port="in")
        d = edge.to_dict()
        restored = Edge.from_dict(d)
        self.assertEqual(restored.id, "edge-123")
        self.assertEqual(restored.source, "n1")
        self.assertEqual(restored.source_port, "true")
        self.assertEqual(restored.target, "n2")
        self.assertEqual(restored.target_port, "in")

    def test_edge_from_dict_malformed_structures(self) -> None:
        with self.assertRaises(InvalidEdgeError):
            Edge.from_dict("not-a-dict")

        # Missing required fields
        with self.assertRaises(InvalidEdgeError):
            Edge.from_dict({"id": "e1", "source": "n1", "target": "n2"})  # missing ports


class TestWorkflowModel(unittest.TestCase):
    """Test Workflow model and operations."""

    def test_create_default_workflow(self) -> None:
        wf = Workflow.create_default("My Workflow", "A test description")
        self.assertEqual(wf.schema_version, 1)
        self.assertEqual(wf.workflow.name, "My Workflow")
        self.assertEqual(wf.workflow.description, "A test description")
        self.assertEqual(len(wf.nodes), 1)
        self.assertEqual(wf.nodes[0].type, NODE_TYPE_START)
        self.assertEqual(wf.nodes[0].name, "Start")
        self.assertEqual(len(wf.edges), 0)

    def test_add_and_remove_node(self) -> None:
        wf = Workflow.create_default()
        n2 = Node.create(NODE_TYPE_END, position=Position(300, 200))
        wf.add_node(n2)
        self.assertEqual(len(wf.nodes), 2)
        self.assertIsNotNone(wf.get_node(n2.id))

        # Adding same node ID raises DuplicateIdError
        dup_node = Node.create(NODE_TYPE_END, node_id=n2.id)
        with self.assertRaises(DuplicateIdError):
            wf.add_node(dup_node)

        removed = wf.remove_node(n2.id)
        self.assertTrue(removed)
        self.assertIsNone(wf.get_node(n2.id))
        self.assertEqual(len(wf.nodes), 1)

    def test_remove_node_cascades_edges(self) -> None:
        wf = Workflow.create_default()
        start_id = wf.nodes[0].id
        check_node = Node.create(NODE_TYPE_CHECK_IMAGE, position=Position(300, 150))
        end_node = Node.create(NODE_TYPE_END, position=Position(300, 300))
        wf.add_node(check_node)
        wf.add_node(end_node)

        e1 = Edge(source=start_id, source_port="next", target=check_node.id, target_port="in")
        e2 = Edge(source=check_node.id, source_port="true", target=end_node.id, target_port="in")
        wf.add_edge(e1)
        wf.add_edge(e2)
        self.assertEqual(len(wf.edges), 2)

        # Deleting check_node cascades to both e1 (target) and e2 (source)
        wf.remove_node(check_node.id)
        self.assertEqual(len(wf.nodes), 2)
        self.assertEqual(len(wf.edges), 0)

    def test_add_edge_strict_validation(self) -> None:
        wf = Workflow.create_default()
        start_id = wf.nodes[0].id
        click_node = Node.create(NODE_TYPE_CLICK_IMAGE, position=Position(300, 150))
        wf.add_node(click_node)

        # Valid connection
        valid_edge = Edge(source=start_id, source_port="next", target=click_node.id, target_port="in")
        wf.add_edge(valid_edge, strict=True)

        # Output port cardinality: adding second edge from start_id.next must fail
        another_target = Node.create(NODE_TYPE_END, position=Position(100, 150))
        wf.add_node(another_target)
        second_edge = Edge(source=start_id, source_port="next", target=another_target.id, target_port="in")
        with self.assertRaises(InvalidEdgeError):
            wf.add_edge(second_edge, strict=True)

        # Invalid source port
        invalid_port_edge = Edge(
            source=start_id,
            source_port="invalid_port",
            target=another_target.id,
            target_port="in",
        )
        with self.assertRaises(InvalidEdgeError):
            wf.add_edge(invalid_port_edge, strict=True)

        # Non-existent node
        dangling_edge = Edge(
            source=start_id,
            source_port="next",
            target="missing_node_id",
            target_port="in",
        )
        with self.assertRaises(InvalidEdgeError):
            wf.add_edge(dangling_edge, strict=True)

    def test_duplicate_identical_edge_rejected(self) -> None:
        wf = Workflow.create_default()
        start_id = wf.nodes[0].id
        end_node = Node.create(NODE_TYPE_END, position=Position(300, 200))
        wf.add_node(end_node)

        e1 = Edge(id="e1", source=start_id, source_port="next", target=end_node.id, target_port="in")
        wf.add_edge(e1)

        # Same endpoints with different ID
        e2 = Edge(id="e2", source=start_id, source_port="next", target=end_node.id, target_port="in")
        with self.assertRaises(InvalidEdgeError):
            wf.add_edge(e2)

    def test_create_branching_graph_in_unit_test(self) -> None:
        """Milestone 1 Acceptance: Can create a branching graph in a unit test."""
        wf = Workflow(
            schema_version=1,
            workflow=WorkflowMeta(
                id="wf_branching_test",
                name="Branching Test",
                description="Testing branch logic",
                created_at="2026-10-15T10:00:00+07:00",
                updated_at="2026-10-15T10:00:00+07:00",
            ),
            nodes=[
                Node.create(NODE_TYPE_START, node_id="start_1", position=Position(300, 60)),
                Node.create(
                    NODE_TYPE_CHECK_IMAGE,
                    node_id="check_1",
                    name="Is Logged In?",
                    position=Position(300, 180),
                    params={"image_id": "dashboard.png", "threshold": 0.85},
                ),
                Node.create(
                    NODE_TYPE_CLICK_IMAGE,
                    node_id="click_1",
                    name="Click Profile",
                    position=Position(160, 340),
                    params={"image_id": "profile.png", "offset_x": 0.0, "offset_y": 0.0},
                ),
                Node.create(
                    NODE_TYPE_WAIT_IMAGE,
                    node_id="wait_1",
                    name="Wait For Dashboard",
                    position=Position(460, 340),
                    params={
                        "image_id": "dashboard.png",
                        "condition": "appear",
                        "timeout_ms": 10000,
                        "poll_interval_ms": 300,
                    },
                ),
                Node.create(NODE_TYPE_END, node_id="end_true", name="Done True", position=Position(160, 490)),
                Node.create(NODE_TYPE_END, node_id="end_false", name="Done False", position=Position(460, 490)),
            ],
            edges=[
                Edge(id="e1", source="start_1", source_port="next", target="check_1", target_port="in"),
                Edge(id="e2_true", source="check_1", source_port="true", target="click_1", target_port="in"),
                Edge(id="e3_false", source="check_1", source_port="false", target="wait_1", target_port="in"),
                Edge(id="e4", source="click_1", source_port="success", target="end_true", target_port="in"),
                Edge(id="e5", source="wait_1", source_port="success", target="end_false", target_port="in"),
            ],
            view=ViewState(zoom=1.2, pan_x=50.0, pan_y=20.0),
        )

        self.assertEqual(len(wf.nodes), 6)
        self.assertEqual(len(wf.edges), 5)

        # Check true and false branching edges
        check_outgoing = wf.find_outgoing_edges("check_1")
        self.assertEqual(len(check_outgoing), 2)
        ports = {e.source_port for e in check_outgoing}
        self.assertEqual(ports, {"true", "false"})

        # Serialization round-trip preserves data
        json_output = wf.to_json()
        restored_wf = Workflow.from_json(json_output)

        self.assertEqual(restored_wf.schema_version, 1)
        self.assertEqual(restored_wf.workflow.id, "wf_branching_test")
        self.assertEqual(restored_wf.workflow.name, "Branching Test")
        self.assertEqual(len(restored_wf.nodes), 6)
        self.assertEqual(len(restored_wf.edges), 5)
        self.assertEqual(restored_wf.view.zoom, 1.2)
        self.assertEqual(restored_wf.view.pan_x, 50.0)
        self.assertEqual(restored_wf.view.pan_y, 20.0)

        # Check node parameters preserved
        check_restored = restored_wf.get_node("check_1")
        self.assertIsNotNone(check_restored)
        self.assertEqual(check_restored.params["threshold"], 0.85)
        self.assertEqual(check_restored.params["image_id"], "dashboard.png")

    def test_sample_workflow_from_spec_deserialization(self) -> None:
        """Test round-trip on the exact sample workflow in DATA_MODEL.md section 6."""
        sample_json = """{
  "schema_version": 1,
  "workflow": {
    "id": "wf_login_dashboard",
    "name": "Login and Check Dashboard",
    "description": "Example branching workflow",
    "created_at": "2026-10-15T10:00:00+07:00",
    "updated_at": "2026-10-15T10:00:00+07:00"
  },
  "nodes": [
    {"id":"start_1","type":"START","name":"Start","params":{},"position":{"x":300,"y":60}},
    {"id":"check_1","type":"CHECK_IMAGE","name":"Dashboard visible?","params":{"image_id":"dashboard","threshold":0.85},"position":{"x":300,"y":180}},
    {"id":"click_1","type":"CLICK_IMAGE","name":"Click dashboard","params":{"image_id":"dashboard","offset_x":0,"offset_y":0},"position":{"x":160,"y":340}},
    {"id":"wait_1","type":"WAIT_IMAGE","name":"Wait for dashboard","params":{"image_id":"dashboard","condition":"appear","timeout_ms":10000,"poll_interval_ms":300},"position":{"x":460,"y":340}},
    {"id":"end_1","type":"END","name":"Done","params":{},"position":{"x":160,"y":490}},
    {"id":"end_2","type":"END","name":"Wait completed","params":{},"position":{"x":460,"y":490}}
  ],
  "edges": [
    {"id":"edge_1","source":"start_1","source_port":"next","target":"check_1","target_port":"in"},
    {"id":"edge_2","source":"check_1","source_port":"true","target":"click_1","target_port":"in"},
    {"id":"edge_3","source":"check_1","source_port":"false","target":"wait_1","target_port":"in"},
    {"id":"edge_4","source":"click_1","source_port":"success","target":"end_1","target_port":"in"},
    {"id":"edge_5","source":"wait_1","source_port":"success","target":"end_2","target_port":"in"}
  ],
  "view": {"zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0}
}"""
        wf = Workflow.from_json(sample_json)
        self.assertEqual(wf.workflow.id, "wf_login_dashboard")
        self.assertEqual(len(wf.nodes), 6)
        self.assertEqual(len(wf.edges), 5)
        self.assertEqual(wf.get_node("click_1").params["offset_x"], 0.0)

        # Roundtrip to dict
        d = wf.to_dict()
        re_wf = Workflow.from_dict(d)
        self.assertEqual(re_wf.to_dict(), d)

    def test_unsupported_schema_version_rejected(self) -> None:
        data = {
            "schema_version": 999,
            "workflow": {"id": "1", "name": "t", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
            "nodes": [],
            "edges": [],
        }
        with self.assertRaises(InvalidSchemaVersionError):
            Workflow.from_dict(data)

    def test_missing_schema_version_rejected(self) -> None:
        data = {
            "workflow": {"id": "1", "name": "t", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
            "nodes": [],
            "edges": [],
        }
        with self.assertRaises(InvalidSchemaVersionError):
            Workflow.from_dict(data)

    def test_duplicate_node_ids_in_dict_rejected(self) -> None:
        data = {
            "schema_version": 1,
            "workflow": {"id": "1", "name": "t", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
            "nodes": [
                {"id": "n1", "type": "START", "name": "S", "params": {}, "position": {"x": 0, "y": 0}},
                {"id": "n1", "type": "END", "name": "E", "params": {}, "position": {"x": 10, "y": 10}},
            ],
            "edges": [],
        }
        with self.assertRaises(DuplicateIdError):
            Workflow.from_dict(data)

    def test_duplicate_edge_ids_in_dict_rejected(self) -> None:
        data = {
            "schema_version": 1,
            "workflow": {"id": "1", "name": "t", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
            "nodes": [
                {"id": "n1", "type": "START", "name": "S", "params": {}, "position": {"x": 0, "y": 0}},
                {"id": "n2", "type": "END", "name": "E", "params": {}, "position": {"x": 10, "y": 10}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "source_port": "next", "target": "n2", "target_port": "in"},
                {"id": "e1", "source": "n1", "source_port": "next", "target": "n2", "target_port": "in"},
            ],
        }
        with self.assertRaises(DuplicateIdError):
            Workflow.from_dict(data)

    def test_invalid_json_string_raises_model_error(self) -> None:
        with self.assertRaises(ModelError):
            Workflow.from_json("not valid json {")


if __name__ == "__main__":
    unittest.main()
