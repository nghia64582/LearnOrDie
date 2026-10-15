"""Graph validation engine.

Performs static analysis on workflow models: structure, ports, cardinality,
parameters, reachability, path-to-END, and cycle detection.
Independent of UI and Tkinter.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Optional

from models.node_definitions import (
    NODE_DEFINITIONS,
    NODE_TYPE_CHECK_IMAGE,
    NODE_TYPE_CLICK_IMAGE,
    NODE_TYPE_END,
    NODE_TYPE_PRESS_KEY,
    NODE_TYPE_START,
    NODE_TYPE_TYPE_TEXT,
    NODE_TYPE_WAIT_IMAGE,
    NODE_TYPE_WAIT_TIME,
    get_input_ports,
    get_node_definition,
    get_output_ports,
    is_valid_node_type,
)
from models.workflow import Workflow

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

# Error Codes
CODE_MISSING_START = "MISSING_START"
CODE_MULTIPLE_STARTS = "MULTIPLE_STARTS"
CODE_DUPLICATE_NODE_ID = "DUPLICATE_NODE_ID"
CODE_DUPLICATE_EDGE_ID = "DUPLICATE_EDGE_ID"
CODE_UNKNOWN_NODE_TYPE = "UNKNOWN_NODE_TYPE"
CODE_DANGLING_SOURCE = "DANGLING_SOURCE"
CODE_DANGLING_TARGET = "DANGLING_TARGET"
CODE_INVALID_SOURCE_PORT = "INVALID_SOURCE_PORT"
CODE_INVALID_TARGET_PORT = "INVALID_TARGET_PORT"
CODE_DUPLICATE_EDGE = "DUPLICATE_EDGE"
CODE_OUTPUT_CARDINALITY_EXCEEDED = "OUTPUT_CARDINALITY_EXCEEDED"
CODE_START_HAS_INCOMING_EDGE = "START_HAS_INCOMING_EDGE"
CODE_END_HAS_OUTGOING_EDGE = "END_HAS_OUTGOING_EDGE"
CODE_MISSING_REQUIRED_PARAM = "MISSING_REQUIRED_PARAM"
CODE_INVALID_PARAM_TYPE = "INVALID_PARAM_TYPE"
CODE_PARAM_OUT_OF_RANGE = "PARAM_OUT_OF_RANGE"
CODE_INVALID_PARAM_VALUE = "INVALID_PARAM_VALUE"
CODE_MISSING_REQUIRED_BRANCH = "MISSING_REQUIRED_BRANCH"

# Warning Codes
CODE_UNREACHABLE_NODE = "UNREACHABLE_NODE"
CODE_NO_PATH_TO_END = "NO_PATH_TO_END"
CODE_CYCLE_DETECTED = "CYCLE_DETECTED"


@dataclass(frozen=True)
class ValidationIssue:
    """Represents a single structural or logical validation issue."""

    severity: str  # "error" | "warning"
    code: str
    message: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert issue to JSON-compatible dictionary."""
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "edge_id": self.edge_id,
        }


def validate_workflow(workflow: Workflow) -> list[ValidationIssue]:
    """Validate a workflow graph model and return a list of structured issues.

    Pure function, does not modify workflow and has no UI dependencies.
    """
    issues: list[ValidationIssue] = []

    nodes_by_id: dict[str, Any] = {}
    seen_node_ids: set[str] = set()
    start_nodes: list[Any] = []
    end_nodes: list[Any] = []

    # 1. Node validation
    for node in workflow.nodes:
        if node.id in seen_node_ids:
            issues.append(
                ValidationIssue(
                    severity=SEVERITY_ERROR,
                    code=CODE_DUPLICATE_NODE_ID,
                    message=f"Duplicate node ID '{node.id}'.",
                    node_id=node.id,
                )
            )
        seen_node_ids.add(node.id)
        nodes_by_id[node.id] = node

        if not is_valid_node_type(node.type):
            issues.append(
                ValidationIssue(
                    severity=SEVERITY_ERROR,
                    code=CODE_UNKNOWN_NODE_TYPE,
                    message=f"Unknown node type '{node.type}' on node '{node.name}'.",
                    node_id=node.id,
                )
            )
            continue

        if node.type == NODE_TYPE_START:
            start_nodes.append(node)
        elif node.type == NODE_TYPE_END:
            end_nodes.append(node)

        # Parameter validation
        defn = get_node_definition(node.type)
        for p_name, p_def in defn.parameters.items():
            val = node.params.get(p_name)

            # Check required
            if p_def.required:
                if val is None or (isinstance(val, str) and not val.strip()):
                    issues.append(
                        ValidationIssue(
                            severity=SEVERITY_ERROR,
                            code=CODE_MISSING_REQUIRED_PARAM,
                            message=f"Parameter '{p_def.display_name or p_name}' is required for '{node.name}'.",
                            node_id=node.id,
                        )
                    )
                    continue

            if val is not None:
                # Type checking
                if p_def.type == "int":
                    if isinstance(val, bool) or not isinstance(val, int):
                        issues.append(
                            ValidationIssue(
                                severity=SEVERITY_ERROR,
                                code=CODE_INVALID_PARAM_TYPE,
                                message=f"Parameter '{p_name}' on '{node.name}' must be an integer.",
                                node_id=node.id,
                            )
                        )
                    else:
                        if p_def.min_value is not None and val < p_def.min_value:
                            issues.append(
                                ValidationIssue(
                                    severity=SEVERITY_ERROR,
                                    code=CODE_PARAM_OUT_OF_RANGE,
                                    message=f"Parameter '{p_name}' on '{node.name}' must be >= {p_def.min_value}.",
                                    node_id=node.id,
                                )
                            )
                        if p_def.max_value is not None and val > p_def.max_value:
                            issues.append(
                                ValidationIssue(
                                    severity=SEVERITY_ERROR,
                                    code=CODE_PARAM_OUT_OF_RANGE,
                                    message=f"Parameter '{p_name}' on '{node.name}' must be <= {p_def.max_value}.",
                                    node_id=node.id,
                                )
                            )

                elif p_def.type == "float":
                    if isinstance(val, bool) or not isinstance(val, (int, float)):
                        issues.append(
                            ValidationIssue(
                                severity=SEVERITY_ERROR,
                                code=CODE_INVALID_PARAM_TYPE,
                                message=f"Parameter '{p_name}' on '{node.name}' must be a number.",
                                node_id=node.id,
                            )
                        )
                    else:
                        f_val = float(val)
                        if p_def.min_value is not None and f_val < p_def.min_value:
                            issues.append(
                                ValidationIssue(
                                    severity=SEVERITY_ERROR,
                                    code=CODE_PARAM_OUT_OF_RANGE,
                                    message=f"Parameter '{p_name}' on '{node.name}' must be >= {p_def.min_value}.",
                                    node_id=node.id,
                                )
                            )
                        if p_def.max_value is not None and f_val > p_def.max_value:
                            issues.append(
                                ValidationIssue(
                                    severity=SEVERITY_ERROR,
                                    code=CODE_PARAM_OUT_OF_RANGE,
                                    message=f"Parameter '{p_name}' on '{node.name}' must be <= {p_def.max_value}.",
                                    node_id=node.id,
                                )
                            )

                elif p_def.type == "enum":
                    if val not in p_def.options:
                        issues.append(
                            ValidationIssue(
                                severity=SEVERITY_ERROR,
                                code=CODE_INVALID_PARAM_VALUE,
                                message=f"Invalid value '{val}' for parameter '{p_name}' on '{node.name}'. "
                                f"Must be one of: {list(p_def.options)}.",
                                node_id=node.id,
                            )
                        )

    # 2. START node count check
    if len(start_nodes) == 0:
        issues.append(
            ValidationIssue(
                severity=SEVERITY_ERROR,
                code=CODE_MISSING_START,
                message="Workflow must contain exactly one START node.",
            )
        )
    elif len(start_nodes) > 1:
        for sn in start_nodes[1:]:
            issues.append(
                ValidationIssue(
                    severity=SEVERITY_ERROR,
                    code=CODE_MULTIPLE_STARTS,
                    message=f"Multiple START nodes detected. Found additional START node '{sn.name}'.",
                    node_id=sn.id,
                )
            )

    # 3. Edge validation
    seen_edge_ids: set[str] = set()
    edge_signatures: set[tuple[str, str, str, str]] = set()
    outgoing_counts: dict[tuple[str, str], int] = defaultdict(int)
    outgoing_by_node: dict[str, set[str]] = defaultdict(set)
    valid_edges: list[Any] = []

    for edge in workflow.edges:
        if edge.id in seen_edge_ids:
            issues.append(
                ValidationIssue(
                    severity=SEVERITY_ERROR,
                    code=CODE_DUPLICATE_EDGE_ID,
                    message=f"Duplicate edge ID '{edge.id}'.",
                    edge_id=edge.id,
                )
            )
        seen_edge_ids.add(edge.id)

        # Check dangling endpoints
        src_node = nodes_by_id.get(edge.source)
        tgt_node = nodes_by_id.get(edge.target)

        if src_node is None:
            issues.append(
                ValidationIssue(
                    severity=SEVERITY_ERROR,
                    code=CODE_DANGLING_SOURCE,
                    message=f"Edge references non-existent source node ID '{edge.source}'.",
                    edge_id=edge.id,
                )
            )
        if tgt_node is None:
            issues.append(
                ValidationIssue(
                    severity=SEVERITY_ERROR,
                    code=CODE_DANGLING_TARGET,
                    message=f"Edge references non-existent target node ID '{edge.target}'.",
                    edge_id=edge.id,
                )
            )

        if src_node and tgt_node:
            # Check ports
            src_outputs = get_output_ports(src_node.type)
            if edge.source_port not in src_outputs:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_ERROR,
                        code=CODE_INVALID_SOURCE_PORT,
                        message=f"Port '{edge.source_port}' is not a valid output port for node '{src_node.name}' ({src_node.type}).",
                        node_id=src_node.id,
                        edge_id=edge.id,
                    )
                )

            tgt_inputs = get_input_ports(tgt_node.type)
            if edge.target_port not in tgt_inputs:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_ERROR,
                        code=CODE_INVALID_TARGET_PORT,
                        message=f"Port '{edge.target_port}' is not a valid input port for node '{tgt_node.name}' ({tgt_node.type}).",
                        node_id=tgt_node.id,
                        edge_id=edge.id,
                    )
                )

            # Target is START
            if tgt_node.type == NODE_TYPE_START:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_ERROR,
                        code=CODE_START_HAS_INCOMING_EDGE,
                        message="START node cannot have incoming edges.",
                        node_id=tgt_node.id,
                        edge_id=edge.id,
                    )
                )

            # Source is END
            if src_node.type == NODE_TYPE_END:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_ERROR,
                        code=CODE_END_HAS_OUTGOING_EDGE,
                        message="END node cannot have outgoing edges.",
                        node_id=src_node.id,
                        edge_id=edge.id,
                    )
                )

            # Duplicate edge check
            sig = (edge.source, edge.source_port, edge.target, edge.target_port)
            if sig in edge_signatures:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_ERROR,
                        code=CODE_DUPLICATE_EDGE,
                        message=f"Duplicate edge between '{src_node.name}' ({edge.source_port}) and '{tgt_node.name}'.",
                        edge_id=edge.id,
                    )
                )
            else:
                edge_signatures.add(sig)

            # Cardinality check
            port_key = (edge.source, edge.source_port)
            outgoing_counts[port_key] += 1
            if outgoing_counts[port_key] > 1:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_ERROR,
                        code=CODE_OUTPUT_CARDINALITY_EXCEEDED,
                        message=f"Output port '{edge.source_port}' on '{src_node.name}' has multiple outgoing edges.",
                        node_id=src_node.id,
                        edge_id=edge.id,
                    )
                )

            outgoing_by_node[src_node.id].add(edge.source_port)
            valid_edges.append(edge)

    # 4. Required branches check
    for node in workflow.nodes:
        if not is_valid_node_type(node.type):
            continue

        connected_ports = outgoing_by_node.get(node.id, set())

        if node.type == NODE_TYPE_START:
            if "next" not in connected_ports:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_ERROR,
                        code=CODE_MISSING_REQUIRED_BRANCH,
                        message=f"START node '{node.name}' has no outgoing connection from port 'next'.",
                        node_id=node.id,
                    )
                )

        elif node.type == NODE_TYPE_CHECK_IMAGE:
            for req_port in ("true", "false"):
                if req_port not in connected_ports:
                    issues.append(
                        ValidationIssue(
                            severity=SEVERITY_ERROR,
                            code=CODE_MISSING_REQUIRED_BRANCH,
                            message=f"Condition node '{node.name}' is missing required branch '{req_port}'.",
                            node_id=node.id,
                        )
                    )

        elif node.type == NODE_TYPE_WAIT_IMAGE:
            for req_port in ("success", "timeout"):
                if req_port not in connected_ports:
                    issues.append(
                        ValidationIssue(
                            severity=SEVERITY_ERROR,
                            code=CODE_MISSING_REQUIRED_BRANCH,
                            message=f"Action node '{node.name}' is missing required branch '{req_port}'.",
                            node_id=node.id,
                        )
                    )

        elif node.type in (
            NODE_TYPE_CLICK_IMAGE,
            NODE_TYPE_TYPE_TEXT,
            NODE_TYPE_PRESS_KEY,
            NODE_TYPE_WAIT_TIME,
        ):
            for req_port in ("success", "failure"):
                if req_port not in connected_ports:
                    issues.append(
                        ValidationIssue(
                            severity=SEVERITY_ERROR,
                            code=CODE_MISSING_REQUIRED_BRANCH,
                            message=f"Action node '{node.name}' is missing required branch '{req_port}'.",
                            node_id=node.id,
                        )
                    )

    # 5. Reachability, Path to END, and Cycle detection (Warnings)
    if start_nodes:
        # Build adjacency maps from valid edges only
        adj: dict[str, list[str]] = defaultdict(list)
        rev_adj: dict[str, list[str]] = defaultdict(list)

        for edge in valid_edges:
            adj[edge.source].append(edge.target)
            rev_adj[edge.target].append(edge.source)

        # BFS from START to find reachable nodes
        primary_start = start_nodes[0]
        reachable: set[str] = set()
        queue = deque([primary_start.id])
        reachable.add(primary_start.id)

        while queue:
            curr = queue.popleft()
            for neighbor in adj.get(curr, []):
                if neighbor not in reachable and neighbor in nodes_by_id:
                    reachable.add(neighbor)
                    queue.append(neighbor)

        # Warn about unreachable nodes
        for node in workflow.nodes:
            if node.id not in reachable:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_WARNING,
                        code=CODE_UNREACHABLE_NODE,
                        message=f"Node '{node.name}' is unreachable from START.",
                        node_id=node.id,
                    )
                )

        # Reverse BFS from all END nodes to find which nodes can reach an END
        can_reach_end: set[str] = set()
        end_queue = deque([end.id for end in end_nodes if end.id in nodes_by_id])
        for end in end_nodes:
            can_reach_end.add(end.id)

        while end_queue:
            curr = end_queue.popleft()
            for pred in rev_adj.get(curr, []):
                if pred not in can_reach_end and pred in nodes_by_id:
                    can_reach_end.add(pred)
                    end_queue.append(pred)

        # Check reachable nodes that cannot reach an END
        for nid in reachable:
            node = nodes_by_id.get(nid)
            if node and node.type != NODE_TYPE_END and nid not in can_reach_end:
                issues.append(
                    ValidationIssue(
                        severity=SEVERITY_WARNING,
                        code=CODE_NO_PATH_TO_END,
                        message=f"Reachable node '{node.name}' has no path to any END node.",
                        node_id=nid,
                    )
                )

        # Cycle detection using 3-color DFS on reachable subgraph
        # 0 = WHITE (unvisited), 1 = GREY (visiting), 2 = BLACK (visited)
        color: dict[str, int] = {nid: 0 for nid in reachable}
        has_cycle = False
        cycle_node_id: Optional[str] = None

        def dfs_cycle(u: str) -> bool:
            nonlocal has_cycle, cycle_node_id
            color[u] = 1
            for v in adj.get(u, []):
                if v in reachable:
                    if color[v] == 1:
                        has_cycle = True
                        cycle_node_id = v
                        return True
                    elif color[v] == 0:
                        if dfs_cycle(v):
                            return True
            color[u] = 2
            return False

        for nid in reachable:
            if color[nid] == 0:
                if dfs_cycle(nid):
                    break

        if has_cycle:
            issues.append(
                ValidationIssue(
                    severity=SEVERITY_WARNING,
                    code=CODE_CYCLE_DETECTED,
                    message="Graph contains one or more cycles.",
                    node_id=cycle_node_id,
                )
            )

    return issues


def is_valid_workflow(workflow: Workflow) -> bool:
    """Return True if workflow contains zero error-severity issues."""
    issues = validate_workflow(workflow)
    return not any(i.severity == SEVERITY_ERROR for i in issues)
