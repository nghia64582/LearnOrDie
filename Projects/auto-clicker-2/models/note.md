# models/

Các dataclass của ứng dụng và lớp lưu/đọc dữ liệu dạng JSON.

## File

- **`step.py`**
  - `StepType(str, Enum)` gồm 5 loại bước. Cột cuối là `params` mặc định do `default_params()` trả về:

    | Giá trị | Nhãn UI | `params` mặc định |
    |---|---|---|
    | `wait_image` | Đợi ảnh | `image_id`, `timeout_seconds=10`, `confidence=0.8` |
    | `click_image` | Click ảnh | `image_id`, `confidence=0.8`, `button="left"`, `clicks=1` |
    | `click_coordinate` | Click tọa độ | `x`, `y`, `button`, `clicks` |
    | `type_text` | Gõ text | `text`, `interval=0.05` |
    | `press_key` | Gõ phím | `keys="enter"` (ví dụ `ctrl+c`) |
    | `move_mouse` | Di chuột | `x`, `y`, `duration=0.2` |
    | `drag_mouse` | Kéo chuột | `x1`, `y1`, `x2`, `y2`, `button="left"`, `duration=0.5` |
    | `activate_window` | Mở cửa sổ | `title`, `timeout_seconds=5` |
    | `set_window` | Đặt vị trí cửa sổ | `title`, `timeout_seconds=5`, `mode="position"` hoặc `"maximize"`, `left`, `top`, `width=800`, `height=600` |
    | `minimize_window` | Thu nhỏ cửa sổ | `title`, `timeout_seconds=5` |
    | `close_window` | Đóng cửa sổ | `title`, `timeout_seconds=5`, `force_kill=False`, `kill_after_seconds=3`, `missing="error"` hoặc `"skip"` |
    | `open_file` | Mở file | `path`, `arguments=""` (tham số cho .exe), `wait_seconds=1` (đợi sau khi mở) |

  - `StepType.is_window_step` đúng với 4 loại bước cửa sổ (mở, đặt vị trí, thu nhỏ, đóng).

  - `Step` (id uuid, `type`, `params`, `note`) có `to_dict`/`from_dict`. Khi đọc, `params` mặc định được gộp với dữ liệu trong file, nên file cũ thiếu khóa vẫn đọc được.
  - `summary()` sinh dòng mô tả ngắn để hiện trên canvas.
- **`node.py`**: `Node` (id, `step_id`, `x`, `y`, `width=180`, `height=72`) là vị trí hiển thị của một bước.
- **`workflow.py`**: `Workflow` (id uuid, `name`, `steps`, `nodes`, `created_at`, `updated_at` theo ISO UTC).
  - Thêm, xóa, đổi thứ tự bước bằng `add_step(step, index)`, `remove_step`, `move_step(step_id, ±1)`.
  - Mỗi thao tác gọi `_relayout_nodes()`, xếp node thành một cột (`x=40`, `y=24 + i*96`).
- **`workflow_store.py`**: `WorkflowStore` lưu **mỗi workflow một file** `data/workflows/<id>.json` (UTF-8, `indent=2`).
  - Có các hàm `all()` (sắp theo tên), `get`, `save` (gọi `touch()` để cập nhật `updated_at`) và `delete`.
  - File lỗi (JSON hỏng, thiếu khóa) bị bỏ qua.
- **`image.py`**: `ImageAsset` (id uuid, `name`, `filename`, thời gian tạo/sửa) và `utc_now_iso()`.
- **`image_library.py`**: `ImageLibrary` quản lý `data/images/` và file chỉ mục `index.json` (`{"images": [...]}`).
  - `add_from_file()` copy ảnh vào thư mục với tên `<uuid><đuôi>`. Chỉ nhận png/jpg/jpeg/bmp/gif/webp.
  - Có thêm `rename`, `delete` (xóa cả file ảnh), `file_path(image_id)` và `reload()`.
- **`__init__.py`**: re-export `ImageAsset`, `Node`, `Step`, `StepType`, `Workflow`.

## Định dạng file workflow (ví dụ rút gọn)

```json
{
  "id": "…uuid…", "name": "Đăng nhập",
  "steps": [{"id": "…", "type": "click_image",
             "params": {"image_id": "…", "confidence": 0.8, "button": "left", "clicks": 1},
             "note": ""}],
  "nodes": [{"id": "…", "step_id": "…", "x": 40.0, "y": 24.0, "width": 180.0, "height": 72.0}],
  "created_at": "2026-10-16T08:00:00+00:00", "updated_at": "…"
}
```

## Lưu ý

- Bước tham chiếu ảnh qua `image_id`, không phải tên file.
- Tọa độ `nodes` thực tế không dùng để vẽ, vì `ui/workflow_canvas.py` tự vẽ theo thứ tự `steps`, và mọi thay đổi đều xếp lại node.
