# engine/

Kiểm tra và thực thi workflow bằng PyAutoGUI. Phần này không phụ thuộc Tkinter.

## `runner.py`

- **`validate_workflow(workflow, library)`** trả về danh sách lỗi:
  - Workflow chưa có bước nào.
  - Bước đợi ảnh hoặc click ảnh chưa chọn ảnh, ảnh không còn trong thư viện, hoặc mất file ảnh.
- **`RunEvent(kind, message, step_id, index)`**: sự kiện gửi ra ngoài. `kind` là một trong `log`, `step_started`, `step_success`, `failed`, `cancelled`, `finished`.
- **`WorkflowRunner(workflow, library, should_stop, emit).run()`** trả về `"finished"`, `"failed"` hoặc `"cancelled"`.
  - Import `pyautogui` lúc chạy. Nếu thiếu thì phát `failed` kèm hướng dẫn cài.
  - Đặt `FAILSAFE = True` và `PAUSE = 0.05`.
  - Chạy lần lượt từng bước. Sau mỗi bước nghỉ `STEP_PAUSE = 0.2` giây.
  - Lỗi ở một bước thì phát `failed` và **dừng luôn** (không chạy tiếp các bước sau).
  - Gọi `should_stop()` trước mỗi bước và trong vòng lặp tìm ảnh. Nếu được yêu cầu dừng thì phát `cancelled`.
  - Đưa chuột vào góc màn hình (`FailSafeException`) cũng được coi là `cancelled`.
- **Từng loại bước:**
  - *Đợi ảnh*: gọi `locateOnScreen` mỗi `LOCATE_INTERVAL = 0.35` giây cho tới `timeout_seconds`. Hết giờ thì báo `TimeoutError`.
  - *Click ảnh*: đợi ảnh tối đa `CLICK_IMAGE_TIMEOUT = 8` giây (cố định), rồi click vào tâm ảnh với `button` và `clicks` đã chọn.
  - *Click tọa độ*: `pyautogui.click(x, y, …)`.
  - *Gõ text*:
    - Text ASCII dùng `pyautogui.write(interval)`.
    - Text có ký tự Unicode thì copy vào clipboard bằng `pyperclip` rồi nhấn `ctrl+v`, sau đó trả lại nội dung clipboard cũ.
    - Nếu không có `pyperclip` thì quay về `write`, và text có dấu có thể bị gõ sai.
  - *Gõ phím*: `"enter"` dùng `press`, còn `"ctrl+shift+s"` dùng `hotkey`.
- **`confidence`** bị giới hạn trong khoảng 0.1–0.99. Nếu OpenCV không có (lỗi liên quan confidence/opencv) thì engine tìm lại **không** dùng confidence, tức khớp tuyệt đối.

## `__init__.py`

Re-export `RunEvent`, `WorkflowRunner`, `validate_workflow`.

## Lưu ý

- `run()` chạy blocking. UI gọi nó trên thread nền (`ui/run_session.py`) và nhận sự kiện qua `emit`.
- Ảnh được tìm trên toàn màn hình, nên cửa sổ hay thông báo nào che vùng cần tìm hoặc cần click đều làm ảnh hưởng kết quả.
