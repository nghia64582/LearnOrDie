# Implementation Plan

Implement incrementally. Keep every milestone runnable and tested before
proceeding.

## Milestone 1 --- Models and node catalog

Files: - `models/node.py` - `models/edge.py` - `models/workflow.py` -
`models/node_definitions.py` - `tests/test_models.py`

Tasks: - Define dataclasses or equivalent simple typed models. - Use
UUIDs for generated IDs. - Implement `to_dict` / `from_dict`. -
Centralize port and parameter definitions. - Ensure models have no
Tkinter imports.

Acceptance: - Can create a branching graph in a unit test. -
Serialization round-trip preserves data. - Unknown node types and
malformed structures raise clear domain errors.

## Milestone 2 --- Repository and service

Files: - `storage/workflow_repository.py` -
`services/workflow_service.py` - `tests/test_repository.py` -
`tests/test_workflow_service.py`

Tasks: - List/create/load/save/rename/duplicate/delete workflows. - Use
one JSON file per workflow. - Save atomically using temporary file plus
replace. - Sanitize filenames and handle collisions. - Mark workflow
clean only after successful save.

Acceptance: - Save/load round-trip. - Corrupt JSON produces actionable
error. - Rename and duplicate don't silently overwrite another workflow.

## Milestone 3 --- App shell and canvas

Files: - `main.py` - `app/main_window.py` - `app/app_state.py` -
`ui/workflow_list.py` - `ui/workflow_editor.py` -
`ui/workflow_canvas.py` - `ui/node_toolbox.py`

Tasks: - Main window with workflow list and editor. - Add node, select
node/edge, drag node. - Draw edges with arrows and port labels. -
Repaint edges when node moves. - Implement pan/zoom and save view state.

Acceptance: - Can create and visually arrange a graph. - Canvas does not
own a separate copy of graph state.

## Milestone 4 --- Connection interaction and properties

Files: - `ui/workflow_canvas.py` - `ui/properties_panel.py` -
`ui/dialogs.py`

Tasks: - Drag output port to target node. - Alternative connect mode:
click output port then target node. - Escape cancels pending
connection. - Enforce port/cardinality rules at connection time. - Edit
node name and typed params. - Delete edge; delete node with cascade.

Acceptance: - Invalid connections are rejected clearly. - Both
connection methods work. - Parameter changes mark workflow dirty.

## Milestone 5 --- Validator

Files: - `engine/validator.py` - `ui/validation_panel.py` -
`tests/test_validator.py`

Tasks: - Validate structure, ports, cardinality and parameters. - Find
unreachable nodes and no-path-to-END warnings. - Detect cycles. - Return
structured issues.

Acceptance: - Tests cover each major error/warning. - Validator has no
Tkinter dependencies.

## Milestone 6 --- Sample, polish, and QA

Tasks: - Include `data/workflows/login_dashboard.json` or a
sample-generation routine. - Validate sample workflow. - Add dirty-state
prompts. - Test all CRUD paths and UI basics. - Write user-facing README
and troubleshooting notes.

Acceptance: - All Phase 1 acceptance criteria in `SPEC.md` pass.

## Recommended implementation order

Start with Milestones 1 and 2, then build the Canvas. Do not start with
a giant all-in-one Tkinter file. Prefer small commits and run tests
after each milestone.
