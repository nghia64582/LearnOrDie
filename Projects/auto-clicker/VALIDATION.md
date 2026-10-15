# Graph Validation Rules

## 1. API contract

Validator should accept a `Workflow` model and return a list of
structured issues. It must not import Tkinter or show dialogs.

Recommended issue shape:

``` python
{
    "severity": "error",  # "error" | "warning"
    "code": "MISSING_START",
    "message": "Workflow must contain exactly one START node.",
    "node_id": None,
    "edge_id": None
}
```

A dataclass such as `ValidationIssue` is preferred. The UI uses IDs to
select the relevant item.

## 2. Errors

-   `MISSING_START`: no START.
-   `MULTIPLE_STARTS`: more than one START.
-   `DUPLICATE_NODE_ID`.
-   `DUPLICATE_EDGE_ID`.
-   `UNKNOWN_NODE_TYPE`.
-   `DANGLING_SOURCE` / `DANGLING_TARGET`.
-   `INVALID_SOURCE_PORT`.
-   `INVALID_TARGET_PORT`.
-   `DUPLICATE_EDGE`.
-   `OUTPUT_CARDINALITY_EXCEEDED`: more than one edge from the same node
    output port.
-   `START_HAS_INCOMING_EDGE`.
-   `END_HAS_OUTGOING_EDGE`.
-   `MISSING_REQUIRED_PARAM`.
-   `INVALID_PARAM_TYPE`.
-   `PARAM_OUT_OF_RANGE`.
-   `INVALID_PARAM_VALUE`.
-   `MISSING_REQUIRED_BRANCH`: a required output port has no outgoing
    edge.

Required branch policy for complete validation: - `START.next`
required. - Both `CHECK_IMAGE.true` and `CHECK_IMAGE.false` required. -
`WAIT_IMAGE.success` and `WAIT_IMAGE.timeout` required. - Action
`success` and `failure` ports required for `CLICK_IMAGE`, `TYPE_TEXT`,
`PRESS_KEY`, and `WAIT_TIME`.

This means a newly created or partially designed workflow may have
errors until fully connected. Saving drafts is still allowed.

## 3. Warnings

-   `UNREACHABLE_NODE`: node cannot be reached from START.
-   `NO_PATH_TO_END`: reachable node has no path to any END.
-   `CYCLE_DETECTED`: graph contains a cycle; this is a warning in phase
    1.
-   `EMPTY_WORKFLOW_DESCRIPTION` is not necessary; avoid noisy warnings
    for optional metadata.

## 4. Reachability algorithm

-   Build adjacency from valid edges only.
-   DFS/BFS from START to determine reachable nodes.
-   For each reachable node, determine if there is a path to any END
    (reverse traversal from all END nodes is useful).
-   Detect cycle with DFS color states or strongly connected components.
-   Avoid reporting a cascade of misleading issues when an edge already
    references a missing node.

## 5. Validation timing

-   Validate on explicit Validate command.
-   Optional lightweight validation after edits is allowed, but do not
    show modal dialogs for every incomplete edit.
-   Validation panel should retain issue list until re-validation or
    model changes according to a documented policy.
-   Clicking an issue selects and scrolls to its node/edge.

## 6. Editor vs execution

-   Validation is structural only; no image recognition, screenshot,
    input injection, or workflow execution.
-   Missing image ID is a parameter error, not an image lookup attempt.
-   A warning is not automatically a reason to block saving.
