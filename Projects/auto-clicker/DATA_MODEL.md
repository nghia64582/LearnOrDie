# Data Model and JSON Contract

## 1. JSON top-level

Mỗi workflow lưu trong một file `.json`:

``` json
{
  "schema_version": 1,
  "workflow": {
    "id": "uuid",
    "name": "Example workflow",
    "description": "",
    "created_at": "2026-10-15T10:00:00+07:00",
    "updated_at": "2026-10-15T10:00:00+07:00"
  },
  "nodes": [],
  "edges": [],
  "view": {
    "zoom": 1.0,
    "pan_x": 0.0,
    "pan_y": 0.0
  }
}
```

## 2. Workflow fields

-   `schema_version`: integer, bắt buộc, hiện tại là `1`.
-   `workflow.id`: UUID string, ổn định qua rename.
-   `workflow.name`: tên hiển thị.
-   `workflow.description`: string, có thể rỗng.
-   `created_at`, `updated_at`: ISO 8601 có timezone.
-   `nodes`: danh sách node.
-   `edges`: danh sách edge.
-   `view`: trạng thái viewport; không ảnh hưởng graph semantics.

## 3. Node

``` json
{
  "id": "node-uuid",
  "type": "CHECK_IMAGE",
  "name": "Dashboard visible?",
  "params": {
    "image_id": "dashboard",
    "threshold": 0.85
  },
  "position": {
    "x": 300.0,
    "y": 180.0
  }
}
```

`id` phải duy nhất trong workflow. `type` phải thuộc node catalog.
`params` là object. `position.x/y` là tọa độ graph logic, không phải tọa
độ màn hình sau zoom/pan.

## 4. Edge

``` json
{
  "id": "edge-uuid",
  "source": "source-node-id",
  "source_port": "true",
  "target": "target-node-id",
  "target_port": "in"
}
```

-   `source` và `target` tham chiếu node ID.
-   `source_port` phải thuộc output ports của source type.
-   `target_port` phải thuộc input ports của target type.
-   `id` duy nhất.
-   Không cho phép cạnh trùng cùng cặp
    source/source_port/target/target_port.

## 5. Port conventions

Mọi node (ngoại trừ START) có một input port tên `in`. - `START`: output
`next`. - `END`: không có output. - `WAIT_IMAGE`: `success`,
`timeout`. - `CLICK_IMAGE`, `TYPE_TEXT`, `PRESS_KEY`, `WAIT_TIME`:
`success`, `failure`. - `CHECK_IMAGE`: `true`, `false`.

Mỗi output port tối đa một edge. Input `in` có thể nhận nhiều edge để hỗ
trợ merge.

## 6. Sample full workflow

``` json
{
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
}
```

## 7. Compatibility rules

-   Reject unknown `schema_version` with clear error.
-   Do not silently discard unknown node types or fields.
-   Keep serialization deterministic and human-readable (`indent=2`,
    UTF-8).
-   `updated_at` changes on save; `created_at` does not.
-   Save As creates a new workflow ID and resets
    `created_at`/`updated_at` appropriately.
-   File path should be derived safely from workflow name or a stable
    ID; sanitize invalid filename characters and handle collisions.
