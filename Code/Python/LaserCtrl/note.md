# LaserCtrl

Bộ công cụ Python hỗ trợ thiết kế và xuất file cắt laser cho khung, thanh dầm, mối nối, v.v. từ tấm phẳng (thường dày 3mm).

## Cấu trúc chính

- **frame_creator/** — Frame Toolkit: launcher hợp nhất 4 công cụ (mối nối, thanh dầm, khung xương, dầm ngang).
- **engraver_ctrl/** — Công cụ cắt chi tiết / G-code / mô phỏng / máy.
- **dsl_library_tool_v1/** — Ứng dụng quản lý và chỉnh sửa thư viện DSL.
- **shape_codes/** — Các mẫu hình dạng chi tiết (box, hinge, bar, gusset…).
- **sample/** — Ví dụ I-shape bar.
- **notes/** — Ghi chú nhỏ (ví dụ board-hole).
- **rect_nesting_app.py** — Công cụ nesting hình chữ nhật độc lập.

## Yêu cầu

- Python 3.10+
- Tkinter
- `ortools` (chỉ cần cho tab Joint Nesting)

Chạy Frame Toolkit: vào `frame_creator/` rồi `python main_app.py`.
