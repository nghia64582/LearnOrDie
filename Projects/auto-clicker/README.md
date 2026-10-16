# Workflow Graph Editor (MVP Phase 1)

Desktop automation workflow graph editor built with Python and Tkinter. Enables users to visually design, edit, validate, and persist branching graph workflows.

---

## Features

- **Visual Graph Canvas**:
  - Drag and arrange nodes freely with logic coordinate preservation.
  - Smooth pan (right-click / middle-click drag) and zoom centered at cursor (mouse wheel, `+`, `-` buttons).
  - Clear group color coding: **Flow** (Purple), **Action** (Teal), and **Condition** (Orange).
  - Dynamic visual feedback with context-sensitive cursors (move, connect, pointer).

- **Dual Connection Modes**:
  1. **Drag-to-connect**: Drag from an output port handle directly to a target node or its input port.
  2. **Click-to-connect**: Click an output port, move mouse to follow live dashed preview wire, then click the target node.
  - Press `Escape` anytime to cancel a pending connection.

- **Strict Port & Cardinality Rules**:
  - `START` node has no input and one output (`next`).
  - `END` node has one input (`in`) and no outputs.
  - Condition (`CHECK_IMAGE`) supports branching via `true` and `false` ports.
  - Action nodes support `success` and `failure` / `timeout` ports.
  - **Output cardinality limit**: Each output port can have at most one outgoing connection.
  - **Cascade deletion**: Deleting a node automatically removes all attached incoming and outgoing edges.

- **Properties Inspector**:
  - Live editing of node name and typed parameters (strings, integers with min/max, floats, dropdown enums).
  - Inspect connection endpoints and delete edges or nodes directly.
  - Edits mark workflow as dirty (`*`) immediately.

- **Static Graph Validator**:
  - Validates single START node, required parameters, port types, and mandatory branch coverage.
  - Graph diagnostics: detects unreachable nodes, nodes with no path to an `END`, and cycle detection using 3-color DFS.
  - **Interactive navigation**: Clicking any error or warning automatically selects and highlights the affected node/edge on the Canvas.
  - Allows saving draft workflows even when incomplete or reporting errors.

- **Atomic File Persistence**:
  - One human-readable UTF-8 JSON file per workflow (`schema_version: 1`).
  - Atomic write via temporary file replace (`.tmp_...` + `os.replace` + `fsync`).
  - Filename sanitization and collision prevention (prevents silent overwrites during Rename, Save As, and Duplicate).
  - Graceful handling of corrupted files without crashing the application.

- **Sample Branching Workflow**:
  - Includes `login_dashboard.json` demonstrating condition branching (`CHECK_IMAGE` $\rightarrow$ `true` / `false`).

---

## Requirements

- Python 3.11+
- Standard library only (`tkinter`, `json`, `uuid`, `dataclasses`, `pathlib`, `unittest`).
- No external dependencies, desktop control libraries, or image recognition libraries required in Phase 1.

---

## Getting Started

### Launch the Application

```bash
python main.py
```

### Run Automated Tests

Run the comprehensive unit test suite:

```bash
python -m unittest discover tests -v
```

---

## User Guide

### 1. Workflow Management
- **New Workflow** (`Ctrl+N`): Prompts for a name and initializes a new graph with a default `START` node.
- **Open**: Double-click or select a workflow and click **Open**.
- **Save** (`Ctrl+S`): Atomically saves the active workflow to its JSON file.
- **Save As**: Clones the current workflow with a fresh UUID and new name under a new file.
- **Rename**: Safely renames the workflow and its underlying `.json` file on disk.
- **Duplicate**: Creates a copy of any stored workflow with a distinct ID.
- **Delete**: Prompts for confirmation and permanently deletes the workflow file.

### 2. Canvas Controls & Shortcuts
| Action | Shortcut / Gesture |
| :--- | :--- |
| **Select Node / Edge** | Left-click on node or edge |
| **Move Node** | Left-click drag on node body |
| **Connect Ports (Drag)** | Drag from output port circle to target node |
| **Connect Ports (Click)** | Click output port, then click target node |
| **Cancel Action / Deselect** | `Escape` |
| **Delete Selected Node / Edge** | `Delete` or `Backspace` |
| **Pan Canvas** | Right-click drag or Middle-click drag |
| **Zoom In / Out** | Mouse wheel (or `🔍+` / `🔍-` toolbar buttons) |
| **Reset View** | `Reset View` toolbar button |
| **Save Workflow** | `Ctrl+S` |
| **Back to Workflows** | `Ctrl+W` or `← Workflows` button |

### 3. Adding Nodes
- **Click & Place**: Click a node type in the **Toolbox** on the left, then click anywhere on the Canvas.
- **Center Add**: Click the `[+]` button next to any node type in the Toolbox to place it in the center of the current viewport.

### 4. Running Validation
- Click **🔍 Validate** on the top toolbar or switch to the **Validation** tab in the right panel.
- Review any errors (❌) or warnings (⚠️).
- Click any issue row in the table to immediately jump to and highlight the node or edge on the canvas.

---

## Troubleshooting

- **Tkinter Missing on Linux**:
  If running on Linux and Tkinter is not found, install it via:
  ```bash
  sudo apt-get install python3-tk
  ```
- **Corrupted Workflow Files**:
  If a `.json` file in `data/workflows/` contains malformed JSON or an unsupported schema version, the Workflow List displays it with a `Corrupt ⚠️` badge instead of crashing. You can safely delete or inspect the file.
- **Windows Reserved Filenames**:
  Filenames matching Windows device names (`CON`, `PRN`, `AUX`, `NUL`, etc.) are automatically prefixed (e.g. `_CON.json`) to prevent filesystem errors.
- **Unsaved Changes**:
  If you attempt to switch workflows or close the window while changes are unsaved, the editor prompts you to **Save**, **Discard**, or **Cancel**.

---

## Specification Documents

For architecture and design reference:
- [`SPEC.md`](SPEC.md) — Product specification and acceptance criteria.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Module boundaries and dependency rules.
- [`DATA_MODEL.md`](DATA_MODEL.md) — Data models and JSON contract (`schema_version: 1`).
- [`NODE_CATALOG.md`](NODE_CATALOG.md) — Node definitions, ports, and parameter types.
- [`VALIDATION.md`](VALIDATION.md) — Static graph analysis rules and codes.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — Phased milestone implementation plan.
