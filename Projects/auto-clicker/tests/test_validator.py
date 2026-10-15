"""Unit tests for Milestone 5: Graph Validator."""

import sys
import unittest

from engine.validator import (
    CODE_CYCLE_DETECTED,
    CODE_DANGLING_SOURCE,
    CODE_DANGLING_TARGET,
    CODE_DUPLICATE_EDGE,
    CODE_DUPLICATE_EDGE_ID,
    CODE_DUPLICATE_NODE_ID,
    CODE_END_HAS_OUTGOING_EDGE,
    CODE_INVALID_PARAM_TYPE,
    CODE_INVALID_PARAM_VALUE,
    CODE_INVALID_SOURCE_PORT,
    CODE_INVALID_TARGET_PORT,
    CODE_MISSING_REQUIRED_BRANCH,
    CODE_MISSING_REQUIRED_PARAM,
    CODE_MISSING_START,
    CODE_MULTIPLE_STARTS,
    CODE_NO_PATH_TO_END,
    CODE_OUTPUT_CARDINALITY_EXCEEDED,
    CODE_PARAM_OUT_OF_RANGE,
    CODE_START_HAS_INCOMING_EDGE,
    CODE_UNKNOWN_NODE_TYPE,
    CODE_UNREACHABLE_NODE,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    is_valid_workflow,
    validate_workflow,
)
from models.edge import Edge
from models.node import Node, Position
from models.node_definitions import (
    NODE_TYPE_CHECK_IMAGE,
    NODE_TYPE_CLICK_IMAGE,
    NODE_TYPE_END,
    NODE_TYPE_START,
    NODE_TYPE_WAIT_IMAGE,
    NODE_TYPE_WAIT_TIME,
)
from models.workflow import ViewState, Workflow, WorkflowMeta


class TestValidatorNoTkinter(unittest.TestCase):
    """Verify that validator has zero Tkinter dependencies."""

    def test_no_tkinter_in_sys_modules(self) -> None:
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import engine.validator, sys; assert 'tkinter' not in sys.modules",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Importing engine.validator pulled in Tkinter: {result.stderr}",
        )


class TestValidatorStructure(unittest.TestCase):
    """Test validation of graph structure and nodes."""

    def test_valid_sample_workflow(self) -> None:
        sample_json = """{
  "schema_version": 1,
  "workflow": {
    "id": "wf_sample",
    "name": "Sample Flow",
    "description": "",
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
        # Note: click_1 is missing 'failure' branch and wait_1 is missing 'timeout' branch according to strict policy
        issues = validate_workflow(wf)
        codes = [i.code for i in issues]
        self.assertIn(CODE_MISSING_REQUIRED_BRANCH, codes)

        # Now fully connect the failure/timeout branches
        end_err = Node.create(NODE_TYPE_END, node_id="end_err", name="Error End")
        wf.add_node(end_err)
        wf.add_edge(Edge(id="e_fail1", source="click_1", source_port="failure", target="end_err", target_port="in"))
        wf.add_edge(Edge(id="e_timeout", source="wait_1", source_port="timeout", target="end_err", target_port="in"))

        clean_issues = validate_workflow(wf)
        errors = [i for i in clean_issues if i.severity == SEVERITY_ERROR]
        self.assertEqual(len(errors), 0)
        self.assertTrue(is_valid_workflow(wf))

    def test_missing_start_and_multiple_starts(self) -> None:
        wf = Workflow.create_default()
        wf.remove_node(wf.nodes[0].id)  # Remove the only start
        issues = validate_workflow(wf)
        self.assertTrue(any(i.code == CODE_MISSING_START for i in issues))

        # Multiple starts
        wf.add_node(Node.create(NODE_TYPE_START, node_id="s1"))
        wf.add_node(Node.create(NODE_TYPE_START, node_id="s2"))
        issues = validate_workflow(wf)
        self.assertTrue(any(i.code == CODE_MULTIPLE_STARTS for i in issues))

    def test_duplicate_ids(self) -> None:
        wf = Workflow.create_default()
        # Manually inject duplicate IDs to bypass add_node check
        n2 = Node.create(NODE_TYPE_END, node_id=wf.nodes[0].id)
        wf.nodes.append(n2)
        issues = validate_workflow(wf)
        self.assertTrue(any(i.code == CODE_DUPLICATE_NODE_ID for i in issues))

    def test_dangling_edge(self) -> None:
        wf = Workflow.create_default()
        wf.edges.append(Edge(id="bad_e", source="ghost_1", source_port="next", target="ghost_2", target_port="in"))
        issues = validate_workflow(wf)
        codes = [i.code for i in issues]
        self.assertIn(CODE_DANGLING_SOURCE, codes)
        self.assertIn(CODE_DANGLING_TARGET, codes)

    def test_invalid_ports(self) -> None:
        wf = Workflow.create_default()
        end_node = Node.create(NODE_TYPE_END)
        wf.add_node(end_node)
        wf.edges.append(
            Edge(
                id="e1",
                source=wf.nodes[0].id,
                source_port="invalid_out",
                target=end_node.id,
                target_port="invalid_in",
            )
        )
        issues = validate_workflow(wf)
        codes = [i.code for i in issues]
        self.assertIn(CODE_INVALID_SOURCE_PORT, codes)
        self.assertIn(CODE_INVALID_TARGET_PORT, codes)

    def test_start_incoming_and_end_outgoing(self) -> None:
        wf = Workflow.create_default()
        start_id = wf.nodes[0].id
        end_node = Node.create(NODE_TYPE_END)
        wf.add_node(end_node)

        # Incoming edge to START
        wf.edges.append(Edge(id="e_in_start", source=end_node.id, source_port="next", target=start_id, target_port="in"))
        issues = validate_workflow(wf)
        codes = [i.code for i in issues]
        self.assertIn(CODE_START_HAS_INCOMING_EDGE, codes)
        self.assertIn(CODE_END_HAS_OUTGOING_EDGE, codes)

    def test_cardinality_and_duplicate_edges(self) -> None:
        wf = Workflow.create_default()
        s_id = wf.nodes[0].id
        end1 = Node.create(NODE_TYPE_END, node_id="end1")
        end2 = Node.create(NODE_TYPE_END, node_id="end2")
        wf.add_node(end1)
        wf.add_node(end2)

        # Two outgoing edges from same source port
        wf.edges.append(Edge(id="e1", source=s_id, source_port="next", target=end1.id, target_port="in"))
        wf.edges.append(Edge(id="e2", source=s_id, source_port="next", target=end2.id, target_port="in"))
        issues = validate_workflow(wf)
        codes = [i.code for i in issues]
        self.assertIn(CODE_OUTPUT_CARDINALITY_EXCEEDED, codes)

        # Duplicate edge
        wf.edges.append(Edge(id="e3", source=s_id, source_port="next", target=end1.id, target_port="in"))
        issues = validate_workflow(wf)
        codes = [i.code for i in issues]
        self.assertIn(CODE_DUPLICATE_EDGE, codes)


class TestValidatorParameters(unittest.TestCase):
    """Test parameter validation rules."""

    def test_missing_required_param(self) -> None:
        wf = Workflow.create_default()
        check_node = Node.create(NODE_TYPE_CHECK_IMAGE, params={"image_id": ""})
        wf.add_node(check_node)
        issues = validate_workflow(wf)
        self.assertTrue(any(i.code == CODE_MISSING_REQUIRED_PARAM for i in issues))

    def test_param_out_of_range(self) -> None:
        wf = Workflow.create_default()
        check_node = Node.create(
            NODE_TYPE_CHECK_IMAGE, params={"image_id": "img", "threshold": 1.5}
        )
        wf.add_node(check_node)
        issues = validate_workflow(wf)
        self.assertTrue(any(i.code == CODE_PARAM_OUT_OF_RANGE for i in issues))

    def test_invalid_param_value(self) -> None:
        wf = Workflow.create_default()
        wait_node = Node.create(
            NODE_TYPE_WAIT_IMAGE, params={"image_id": "img", "condition": "unknown_cond"}
        )
        wf.add_node(wait_node)
        issues = validate_workflow(wf)
        self.assertTrue(any(i.code == CODE_INVALID_PARAM_VALUE for i in issues))


class TestValidatorWarnings(unittest.TestCase):
    """Test reachability, path-to-end, and cycle warnings."""

    def test_unreachable_node(self) -> None:
        wf = Workflow.create_default()
        orphan = Node.create(NODE_TYPE_END, name="Orphan End")
        wf.add_node(orphan)
        issues = validate_workflow(wf)
        unreachables = [i for i in issues if i.code == CODE_UNREACHABLE_NODE]
        self.assertEqual(len(unreachables), 1)
        self.assertEqual(unreachables[0].node_id, orphan.id)
        self.assertEqual(unreachables[0].severity, SEVERITY_WARNING)

    def test_no_path_to_end(self) -> None:
        wf = Workflow.create_default()
        s_id = wf.nodes[0].id
        wait_node = Node.create(NODE_TYPE_WAIT_TIME)
        wf.add_node(wait_node)
        wf.add_edge(Edge(source=s_id, source_port="next", target=wait_node.id, target_port="in"))
        # Reachable from start, but no path to any END (both start and wait_node have no path to END)
        issues = validate_workflow(wf)
        no_ends = [i for i in issues if i.code == CODE_NO_PATH_TO_END]
        no_end_ids = {i.node_id for i in no_ends}
        self.assertIn(wait_node.id, no_end_ids)
        self.assertIn(s_id, no_end_ids)

    def test_cycle_detected(self) -> None:
        wf = Workflow.create_default()
        s_id = wf.nodes[0].id
        n1 = Node.create(NODE_TYPE_WAIT_TIME, node_id="n1")
        n2 = Node.create(NODE_TYPE_WAIT_TIME, node_id="n2")
        wf.add_node(n1)
        wf.add_node(n2)

        # START -> n1 -> n2 -> n1 (cycle!)
        wf.add_edge(Edge(source=s_id, source_port="next", target=n1.id, target_port="in"))
        wf.add_edge(Edge(source=n1.id, source_port="success", target=n2.id, target_port="in"))
        wf.add_edge(Edge(source=n2.id, source_port="success", target=n1.id, target_port="in"))

        issues = validate_workflow(wf)
        cycles = [i for i in issues if i.code == CODE_CYCLE_DETECTED]
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0].severity, SEVERITY_WARNING)


if __name__ == "__main__":
    unittest.main()
