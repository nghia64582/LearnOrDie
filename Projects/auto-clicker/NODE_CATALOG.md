# Node Catalog

`models/node_definitions.py` is the single source of truth for this
catalog. UI forms, Canvas ports, and validator should consume it rather
than hardcoding node rules separately.

## Common node structure

Every node has: - `id`: unique ID. - `type`: catalog key. - `name`:
editable label. - `params`: dict. - `position`: `{x, y}` in graph
coordinates.

Every node except `START` has input port `in`. `START` has no input.
`END` has no output.

## Catalog

  --------------------------------------------------------------------------
  Type              Group             Output ports      Parameters
  ----------------- ----------------- ----------------- --------------------
  `START`           Flow              `next`            none

  `END`             Flow              none              none

  `WAIT_IMAGE`      Action            `success`,        `image_id`,
                                      `timeout`         `condition`,
                                                        `timeout_ms`,
                                                        `poll_interval_ms`

  `CLICK_IMAGE`     Action            `success`,        `image_id`,
                                      `failure`         `offset_x`,
                                                        `offset_y`

  `TYPE_TEXT`       Action            `success`,        `text`
                                      `failure`         

  `PRESS_KEY`       Action            `success`,        `key` or `keys`
                                      `failure`         

  `WAIT_TIME`       Action            `success`,        `duration_ms`
                                      `failure`         

  `CHECK_IMAGE`     Condition         `true`, `false`   `image_id`,
                                                        `threshold`
  --------------------------------------------------------------------------

## Parameter definitions

### WAIT_IMAGE

-   `image_id`: string, non-empty for validation.
-   `condition`: enum `appear` or `disappear`; default `appear`.
-   `timeout_ms`: integer \> 0; default 10000.
-   `poll_interval_ms`: integer \> 0; default 300.

### CLICK_IMAGE

-   `image_id`: string, non-empty for validation.
-   `offset_x`: number; default 0.
-   `offset_y`: number; default 0.
-   Offset is relative to detected image center. The future executor
    will use image center when both offsets are zero.

### TYPE_TEXT

-   `text`: string. Empty text may be permitted; define UI behavior
    consistently.

### PRESS_KEY

-   `key`: non-empty string for a single key, or `keys`: list of
    non-empty strings for a key combination.
-   Pick one representation and document it in code; do not allow
    ambiguous simultaneous values.

### WAIT_TIME

-   `duration_ms`: integer \>= 0; default 1000.

### CHECK_IMAGE

-   `image_id`: string, non-empty for validation.
-   `threshold`: number from 0.0 through 1.0; default 0.85.

## Default values

Use valid defaults for all fields so newly created nodes render
immediately. Image IDs may default to empty string; validator reports
missing required image reference. Avoid inventing a real image asset
dependency in phase 1.

## UI suggestions

-   Display node type and name in node body.
-   Render ports as visible circles or clear port handles with labels.
-   Distinguish Condition nodes visually from Action nodes, but also
    include text labels.
-   In Properties Panel, render enum values as dropdowns, booleans as
    checkboxes, numbers as numeric inputs and strings as text fields.
-   Keep parameter labels human-readable while preserving exact keys in
    JSON.
