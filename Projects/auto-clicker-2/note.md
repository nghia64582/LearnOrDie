# auto-clicker-2

Ứng dụng desktop (Python + Tkinter) để **thiết kế và chạy workflow tự động thao tác giao diện**: đợi ảnh xuất hiện trên màn hình, click ảnh, click tọa độ, gõ text, gõ phím, di/kéo chuột, mở / thu nhỏ / đặt vị trí cửa sổ đang chạy, mở file/thư mục/chương trình. Thao tác chuột/bàn phím và tìm ảnh dùng PyAutoGUI. Yêu cầu ban đầu nằm trong `spec.md`.

## Chạy

```bash
python -m pip install -r requirements.txt   # Pillow, pyautogui, opencv-python, pygetwindow
python main.py
```

- `main.py` bật DPI awareness (`engine/screen.py`, chỉ có tác dụng trên Windows), gọi `ensure_data_dirs()` rồi mở `MainWindow`.
- Import dùng tên tuyệt đối (`app.`, `models.`, `engine.`, `ui.`). Khi chạy `python main.py`, thư mục dự án tự nằm trong `sys.path`.
- Dữ liệu luôn lưu ở `data/` của dự án (tính theo vị trí file nguồn, không theo thư mục đang đứng).

## Cấu trúc

| Thư mục | Vai trò | Ghi chú chi tiết |
|---|---|---|
| `app/` | Cửa sổ chính và đường dẫn dữ liệu | [app/note.md](app/note.md) |
| `models/` | Dataclass Workflow / Step / Node / ImageAsset, lưu-đọc JSON | [models/note.md](models/note.md) |
| `engine/` | Kiểm tra và thực thi workflow bằng PyAutoGUI | [engine/note.md](engine/note.md) |
| `ui/` | Các tab, canvas workflow, form sửa bước, chạy nền, toast | [ui/note.md](ui/note.md) |
| `data/` | Nơi lưu workflow (`*.json`) và ảnh mẫu, bị gitignore | [data/note.md](data/note.md) |

## Luồng chính

1. **Tab "Hình ảnh"**: thêm ảnh mẫu bằng cách chọn file, **chụp màn hình** (nút "Chụp màn hình (Win+Shift+S)" mở công cụ cắt của Windows rồi tự lấy ảnh mới từ clipboard), hoặc **dán ảnh bằng Ctrl+V**. Ảnh được copy vào `data/images/<uuid>.<ext>` (ảnh chụp lưu dạng PNG) và ghi vào `data/images/index.json`.
2. **Tab "Workflow"**: tạo workflow, thêm/sửa/sắp xếp các bước. Mỗi thay đổi được **tự lưu** ngay vào `data/workflows/<id>.json`.
3. **Nhấn "Chạy"**:
   - Kiểm tra workflow (`validate_workflow`).
   - Đếm ngược 3 giây để người dùng chuyển sang cửa sổ cần thao tác.
   - Chạy tuần tự từng bước trên thread nền (`WorkflowRunner`).
   - Trạng thái hiện ở nhãn dưới nút Chạy, kèm một toast nhỏ tự tắt. Không còn cửa sổ popup.
   - Bước đang chạy, đã xong hoặc lỗi được tô màu trên canvas.
4. **Dừng**: nút "Dừng" (chính là nút Chạy khi đang chạy), hoặc đưa chuột lên góc trên-trái màn hình (FAILSAFE của PyAutoGUI).

## Phụ thuộc

- **Pillow**: bắt buộc, vì tab Hình ảnh import PIL ngay khi mở app. `ImageGrab.grabclipboard()` cũng dùng để đọc ảnh chụp hoặc ảnh dán. Trên Linux, việc này cần thêm `xclip` hoặc `wl-paste`.
- **pyautogui**: chỉ import khi chạy workflow hoặc lấy tọa độ chuột, nên thiếu nó app vẫn mở được.
- **pygetwindow** (đi kèm pyautogui): dùng cho các bước cửa sổ (mở, thu nhỏ, đặt vị trí) và dropdown chọn cửa sổ. Thư viện này **chỉ chạy trên Windows**; trên máy khác form vẫn mở được nhưng báo lỗi khi làm mới danh sách hoặc khi chạy bước cửa sổ.
- **opencv-python**: cần cho tham số "độ khớp" (`confidence`) khi tìm ảnh. Thiếu nó thì engine tìm ảnh khớp tuyệt đối.
- **pyperclip** (không có trong requirements): tùy chọn, dùng để gõ text có dấu/Unicode qua clipboard (Ctrl+V).

## Lưu ý

- Workflow chỉ chạy **tuần tự**, không có rẽ nhánh hay vòng lặp.
- Tọa độ `Node` lưu trong JSON luôn bị xếp lại thành một cột, và canvas tự vẽ theo layout cố định (xem `models/note.md`).
- File workflow JSON hỏng sẽ bị **bỏ qua im lặng** khi liệt kê.
- Xóa ảnh không kiểm tra workflow nào đang dùng ảnh đó. Lỗi chỉ lộ ra khi chạy (bước kiểm tra sẽ báo).
- **Nhiều màn hình**: engine tìm ảnh trên **mọi màn hình** (chụp cả màn hình ảo bằng `ImageGrab.grab(all_screens=True)`), rồi đổi tọa độ sang tọa độ màn hình thật, kể cả khi màn hình phụ nằm bên trái/phía trên màn hình chính (tọa độ âm). Chưa có tùy chọn chọn màn hình cho từng bước. Chi tiết xem `engine/note.md`.
- Ứng dụng nhắm tới Windows (font Segoe UI, hotkey `ctrl+v`).
