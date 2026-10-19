# engraver_ctrl

Công cụ xử lý cắt chi tiết nhỏ, xuất G-code, mô phỏng và điều khiển máy khắc/cắt.

## Các file chính

- **cut_handler.py** — Thuật toán bin-packing (FFD, BFD…) để cắt thanh dài thành các đoạn nhỏ.
- **cut_plan_builder.py** — Xây dựng CutPlan, hỗ trợ bo tròn đầu (arch) và lỗ tròn.
- **extended_cut_export.py** + **cut_tool_2.py** — Xuất và công cụ phụ.
- **tab_small_parts.py** — Giao diện cắt thanh nhỏ.
- **tab_designer.py** — Thiết kế chi tiết (file lớn nhất).
- **tab_simulate.py** — Mô phỏng G-code.
- **tab_machine.py** — Điều khiển / ước lượng thời gian máy.
- **tab_parallel.py** — Các đường song song.

Các file `.gcode` là ví dụ đầu ra.
