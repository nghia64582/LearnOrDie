# engraver_ctrl

Công cụ xử lý cắt chi tiết nhỏ, xuất G-code, mô phỏng và điều khiển máy khắc/cắt.

## Các file chính

- **cut_handler.py** — 1D packing (FFD, BFD, optional OR-Tools exact) for stick cut lists. No kerf.
- **cut_plan_builder.py** — CutPlan with per-stick placements, stadium-stick layout, text format for parts.
- **extended_cut_export.py** + **cut_tool_2.py** — Xuất và công cụ phụ.
- **tab_small_parts.py** — Small parts UI: text/card input, packing preview, G-code export.
- **test_small_parts.py** — Packing, arrangement, format, export, and UI mode-sync tests.
- **tab_designer.py** — Thiết kế chi tiết (file lớn nhất).
- **tab_simulate.py** — Mô phỏng G-code.
- **tab_machine.py** — Điều khiển / ước lượng thời gian máy.
- **tab_parallel.py** — Các đường song song.

Các file `.gcode` là ví dụ đầu ra.
