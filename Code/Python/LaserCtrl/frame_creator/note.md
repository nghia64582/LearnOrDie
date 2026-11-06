# frame_creator

Frame Toolkit — launcher hợp nhất 5 công cụ chính trong một cửa sổ (ttk.Notebook).

## Các file

- **main_app.py** — Entry point. Tạo notebook với 5 tab, import và gắn các GUI. Đã thêm `sys.path` để import package `frame_creator` khi chạy trực tiếp từ thư mục này.
- **joint_nesting_gui.py** + **joint_nesting_solver.py** — Tối ưu xếp mối nối (L/T/Plus, có/không lỗ) bằng OR-Tools CP-SAT. Xuất DSL + preview.
- **beam_dsl_core.py** + **beam_dsl_gui.py** — Sinh DSL cho thanh dầm L / T / Plus (finger joint, dày 3mm). Core tính hình học, GUI nhập số lượng + chiều dài.
- **rail_skeleton_core.py** + **rail_skeleton_gui.py** — Công cụ khung xương (skeleton).
- **rail_cutlist_core.py** + **rail_cutlist_gui.py** — Công cụ dầm ngang / rail cut-list.
- **box_core.py** + **box_gui.py** — Tab hộp: nhập khung đường tâm + H + số frame, xuất một file DSL (rails/joints/beams). Frames nhân rail; beam_count nhân dầm; mỗi dầm cần 2 mối có lỗ.

## Chạy

```bash
cd frame_creator
python main_app.py
```

Cần `pip install ortools` nếu dùng tab Mối nối.
