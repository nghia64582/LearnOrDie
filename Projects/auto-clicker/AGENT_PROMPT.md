# Coding Agent Prompt

You are implementing Phase 1 of a Python Tkinter Workflow Graph Editor.
Read all project markdown files before coding, especially `SPEC.md`,
`ARCHITECTURE.md`, `DATA_MODEL.md`, `NODE_CATALOG.md`, `VALIDATION.md`,
and `IMPLEMENTATION_PLAN.md`.

## Goal

Build a runnable MVP that lets users create, edit, validate, save,
reopen, rename, duplicate, and delete graph workflows. The graph
supports branching conditions.

## Non-negotiable constraints

1.  Python 3.11+ and Tkinter; standard library only for core runtime.
2.  Do not implement image matching, screenshot capture, PyAutoGUI,
    desktop control, or workflow execution.
3.  Model must not import Tkinter.
4.  Centralize node types, ports, defaults and parameter metadata in
    `models/node_definitions.py`.
5.  Persist one readable UTF-8 JSON file per workflow with
    `schema_version: 1`.
6.  Save draft workflows even if validation reports errors.
7.  Implement both connection methods: drag wire and click output port
    then target node.
8.  Strict port validation; each output port can have at most one
    outgoing edge.
9.  Deleting a node cascades to all attached edges.
10. Undo/Redo is explicitly out of scope.
11. Include a branching sample workflow.
12. Add tests for models, persistence and validation.

## Working style

-   Inspect the repository before modifying it.
-   If the repository already contains code, preserve compatible
    conventions and avoid overwriting unrelated files.
-   Implement in milestones from `IMPLEMENTATION_PLAN.md`.
-   Before each milestone, briefly state intended files and design.
-   Keep functions focused and avoid giant monolithic modules.
-   Run available tests after each milestone; fix failures before moving
    on.
-   If dependencies or environment prevent running tests, state exactly
    what was not run.
-   Do not claim features work unless they were implemented and tested.
-   Update README when behavior or commands change.
-   Prefer robust error handling over silent recovery.
-   Do not add dependencies without a concrete need.

## Definition of done

-   App launches with `python main.py`.
-   Workflow CRUD works.
-   Graph editing supports node dragging and both connection modes.
-   Properties panel edits all node parameters.
-   Validation shows structured errors and warnings and can select the
    referenced node/edge.
-   JSON round-trip preserves workflow, nodes, edges, params, positions
    and viewport.
-   Sample graph demonstrates `CHECK_IMAGE` true/false branches.
-   Tests pass.
-   No desktop automation is performed.

## First action

Inspect the current repository. If empty, create the structure in
`ARCHITECTURE.md`. Implement Milestone 1 first, then Milestone 2. Do not
try to implement the entire application in one enormous pass.
