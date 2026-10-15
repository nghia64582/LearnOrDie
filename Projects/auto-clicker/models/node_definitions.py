"""Node catalog definitions.

Single source of truth for node types, groups, ports, parameters, defaults,
and validation metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ParameterDefinition:
    """Metadata describing a single node parameter."""

    name: str
    type: str  # 'str', 'int', 'float', 'enum'
    default: Any
    options: tuple[str, ...] = ()
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = False
    display_name: str = ""
    description: str = ""


@dataclass(frozen=True)
class NodeDefinition:
    """Metadata describing a node type."""

    type: str
    group: str  # 'Flow', 'Action', 'Condition'
    display_name: str
    default_name: str
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    parameters: dict[str, ParameterDefinition] = field(default_factory=dict)


# Node type string constants
NODE_TYPE_START = "START"
NODE_TYPE_END = "END"
NODE_TYPE_WAIT_IMAGE = "WAIT_IMAGE"
NODE_TYPE_CLICK_IMAGE = "CLICK_IMAGE"
NODE_TYPE_TYPE_TEXT = "TYPE_TEXT"
NODE_TYPE_PRESS_KEY = "PRESS_KEY"
NODE_TYPE_WAIT_TIME = "WAIT_TIME"
NODE_TYPE_CHECK_IMAGE = "CHECK_IMAGE"

# Node groups
GROUP_FLOW = "Flow"
GROUP_ACTION = "Action"
GROUP_CONDITION = "Condition"

# Standard input port name
DEFAULT_INPUT_PORT = "in"

# Full catalog of node definitions
NODE_DEFINITIONS: dict[str, NodeDefinition] = {
    NODE_TYPE_START: NodeDefinition(
        type=NODE_TYPE_START,
        group=GROUP_FLOW,
        display_name="Start",
        default_name="Start",
        input_ports=(),
        output_ports=("next",),
        parameters={},
    ),
    NODE_TYPE_END: NodeDefinition(
        type=NODE_TYPE_END,
        group=GROUP_FLOW,
        display_name="End",
        default_name="End",
        input_ports=(DEFAULT_INPUT_PORT,),
        output_ports=(),
        parameters={},
    ),
    NODE_TYPE_WAIT_IMAGE: NodeDefinition(
        type=NODE_TYPE_WAIT_IMAGE,
        group=GROUP_ACTION,
        display_name="Wait Image",
        default_name="Wait Image",
        input_ports=(DEFAULT_INPUT_PORT,),
        output_ports=("success", "timeout"),
        parameters={
            "image_id": ParameterDefinition(
                name="image_id",
                type="str",
                default="",
                required=True,
                display_name="Image ID",
                description="Identifier or path of the target image",
            ),
            "condition": ParameterDefinition(
                name="condition",
                type="enum",
                default="appear",
                options=("appear", "disappear"),
                required=True,
                display_name="Condition",
                description="Wait until image appears or disappears",
            ),
            "timeout_ms": ParameterDefinition(
                name="timeout_ms",
                type="int",
                default=10000,
                min_value=1,
                required=True,
                display_name="Timeout (ms)",
                description="Maximum wait time in milliseconds",
            ),
            "poll_interval_ms": ParameterDefinition(
                name="poll_interval_ms",
                type="int",
                default=300,
                min_value=1,
                required=True,
                display_name="Poll Interval (ms)",
                description="Interval between screen checks in milliseconds",
            ),
        },
    ),
    NODE_TYPE_CLICK_IMAGE: NodeDefinition(
        type=NODE_TYPE_CLICK_IMAGE,
        group=GROUP_ACTION,
        display_name="Click Image",
        default_name="Click Image",
        input_ports=(DEFAULT_INPUT_PORT,),
        output_ports=("success", "failure"),
        parameters={
            "image_id": ParameterDefinition(
                name="image_id",
                type="str",
                default="",
                required=True,
                display_name="Image ID",
                description="Identifier or path of the image to click",
            ),
            "offset_x": ParameterDefinition(
                name="offset_x",
                type="float",
                default=0.0,
                required=False,
                display_name="Offset X",
                description="Horizontal pixel offset relative to image center",
            ),
            "offset_y": ParameterDefinition(
                name="offset_y",
                type="float",
                default=0.0,
                required=False,
                display_name="Offset Y",
                description="Vertical pixel offset relative to image center",
            ),
        },
    ),
    NODE_TYPE_TYPE_TEXT: NodeDefinition(
        type=NODE_TYPE_TYPE_TEXT,
        group=GROUP_ACTION,
        display_name="Type Text",
        default_name="Type Text",
        input_ports=(DEFAULT_INPUT_PORT,),
        output_ports=("success", "failure"),
        parameters={
            "text": ParameterDefinition(
                name="text",
                type="str",
                default="",
                required=False,
                display_name="Text",
                description="Text string to type",
            ),
        },
    ),
    NODE_TYPE_PRESS_KEY: NodeDefinition(
        type=NODE_TYPE_PRESS_KEY,
        group=GROUP_ACTION,
        display_name="Press Key",
        default_name="Press Key",
        input_ports=(DEFAULT_INPUT_PORT,),
        output_ports=("success", "failure"),
        parameters={
            "key": ParameterDefinition(
                name="key",
                type="str",
                default="Enter",
                required=True,
                display_name="Key",
                description="Key name (e.g. 'Enter', 'ctrl+c', 'tab')",
            ),
        },
    ),
    NODE_TYPE_WAIT_TIME: NodeDefinition(
        type=NODE_TYPE_WAIT_TIME,
        group=GROUP_ACTION,
        display_name="Wait Time",
        default_name="Wait Time",
        input_ports=(DEFAULT_INPUT_PORT,),
        output_ports=("success", "failure"),
        parameters={
            "duration_ms": ParameterDefinition(
                name="duration_ms",
                type="int",
                default=1000,
                min_value=0,
                required=True,
                display_name="Duration (ms)",
                description="Pause duration in milliseconds",
            ),
        },
    ),
    NODE_TYPE_CHECK_IMAGE: NodeDefinition(
        type=NODE_TYPE_CHECK_IMAGE,
        group=GROUP_CONDITION,
        display_name="Check Image",
        default_name="Check Image",
        input_ports=(DEFAULT_INPUT_PORT,),
        output_ports=("true", "false"),
        parameters={
            "image_id": ParameterDefinition(
                name="image_id",
                type="str",
                default="",
                required=True,
                display_name="Image ID",
                description="Identifier or path of the image to check",
            ),
            "threshold": ParameterDefinition(
                name="threshold",
                type="float",
                default=0.85,
                min_value=0.0,
                max_value=1.0,
                required=True,
                display_name="Threshold",
                description="Matching confidence threshold (0.0 to 1.0)",
            ),
        },
    ),
}


def is_valid_node_type(node_type: str) -> bool:
    """Return True if node_type is registered in the catalog."""
    return node_type in NODE_DEFINITIONS


def get_node_definition(node_type: str) -> NodeDefinition:
    """Retrieve the NodeDefinition for a given node_type.

    Raises KeyError if node_type is unknown.
    """
    if node_type not in NODE_DEFINITIONS:
        raise KeyError(f"Unknown node type: {node_type}")
    return NODE_DEFINITIONS[node_type]


def get_default_params(node_type: str) -> dict[str, Any]:
    """Return a dictionary of default parameter values for a node type."""
    definition = get_node_definition(node_type)
    return {name: param.default for name, param in definition.parameters.items()}


def get_input_ports(node_type: str) -> tuple[str, ...]:
    """Return allowed input ports for a node type."""
    return get_node_definition(node_type).input_ports


def get_output_ports(node_type: str) -> tuple[str, ...]:
    """Return allowed output ports for a node type."""
    return get_node_definition(node_type).output_ports
