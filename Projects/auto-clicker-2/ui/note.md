# ui/

Giao diện Tkinter/ttk: hai tab chính, canvas hiển thị workflow, form sửa bước, phần chạy nền và toast thông báo.

## File

- **`workflows_tab.py`**: `WorkflowsTab`, tab "Workflow".
  - **Bên trái**: danh sách workflow (Treeview: tên, số bước) với các nút Thêm, Đổi tên, Xóa (dùng `simpledialog` và `messagebox`).
  - **Bên phải**: ô tên kèm nhãn "Đã lưu" và nút Lưu; dưới đó là canvas và form sửa bước đặt trong một `Panedwindow`.
  - **Thanh công cụ**: chọn loại bước, Thêm bước, Lên, Xuống, Xóa bước, và nút **Chạy**. Nút Chạy thành **Dừng** khi đang chạy.
  - **Trạng thái chạy**: nhãn riêng ngay dưới thanh công cụ.
  - **Tự lưu**: đổi tên, sửa bất kỳ trường nào của bước, hoặc chọn bước khác đều gọi `_persist()` để lưu workflow xuống file ngay.
  - **`run_workflow()`**:
    1. Lưu workflow và lấy một bản sao (snapshot) để chạy.
    2. Gọi `validate_workflow`. Có lỗi thì hiện `messagebox.showerror` và không chạy.
    3. Tạo `RunSession`.
    - Trong lúc đếm ngược: nhãn hiện "Bắt đầu sau Ns…", và một toast hiện từ đầu.
    - Toast **được đóng ngay khi bắt đầu thực thi**, để không che màn hình khi click hay tìm ảnh.
    - Mỗi bước: nhãn hiện "Bước i/n: …".
    - Kết thúc: nhãn hiện kết quả. Toast xanh khi hoàn thành, toast xám khi bị dừng. Cả hai tự tắt sau 3 giây.
    - Lỗi: nhãn **đỏ, giữ nguyên tới lần chạy sau**, và toast đỏ hiện 8 giây.
    - Canvas tô màu bước đang chạy (cam), đã xong (viền xanh) và lỗi (đỏ).
  - **"Lấy tọa độ chuột"**: hỏi xác nhận bằng `askokcancel`, rồi đọc `pyautogui.position()`.
- **`run_session.py`**: `RunSession`, chạy workflow nền, **không mở cửa sổ**.
  - Đếm ngược `COUNTDOWN_SECONDS = 3` bằng `after()`, rồi chạy `WorkflowRunner` trên thread daemon.
  - Sự kiện đi qua `queue.Queue` và được đọc trên main thread mỗi 120 ms.
  - Báo ra ngoài qua các callback `on_countdown`, `on_started`, `on_event` và `on_close`.
  - `stop()` yêu cầu dừng, kể cả khi đang đếm ngược.
- **`toast.py`**: `Toast(tk.Toplevel)`, thông báo không chặn (non-modal).
  - Dùng `overrideredirect` và topmost, hiện ở góc dưới-phải cửa sổ chính.
  - Tự đóng sau `duration_ms`; nếu `duration_ms=0` thì chỉ đóng khi gọi `dismiss()`. Click vào toast để đóng sớm.
  - Có 3 kiểu: `info`, `success`, `error`.
- **`workflow_canvas.py`**: `WorkflowCanvas(tk.Canvas)` vẽ các bước thành một cột hộp 220x68, nối bằng mũi tên.
  - Màu nền hộp theo loại bước; click vào hộp để chọn bước.
  - Vẽ theo thứ tự `steps`, không dùng tọa độ `Node`.
- **`step_editor.py`**: `StepEditor(ttk.LabelFrame)` là form "Chi tiết bước".
  - Có combobox đổi loại bước. Khi đổi loại, các `params` trùng khóa được giữ lại.
  - Các trường hiện ra theo loại bước: ảnh (chọn theo tên), độ khớp, timeout, tọa độ X/Y kèm nút lấy tọa độ, nút chuột, số lần click, nội dung text, khoảng cách gõ, phím, và ghi chú.
  - Mỗi lần sửa gọi `on_change`, dẫn tới tự lưu.
- **`images_tab.py`**: `ImagesTab`, tab "Hình ảnh".
  - Danh sách ảnh (tên, file) với các nút Thêm ảnh (chọn file), Đổi tên, Xóa (xóa cả file, có hỏi xác nhận).
  - Xem trước ảnh thu nhỏ tối đa 420x320 bằng Pillow, kèm thông tin tên, file và thời gian tạo.

## Lưu ý

- Các thông báo thao tác thường (chưa chọn workflow, tên trống, xác nhận xóa, lỗi kiểm tra trước khi chạy…) vẫn dùng `messagebox`, tức là hộp thoại chặn. Chỉ phần **chạy workflow** chuyển sang nhãn và toast.
- Nhật ký chi tiết từng bước (sự kiện `log`) không còn hiển thị, vì cửa sổ log cũ đã bỏ. Chỉ còn dòng trạng thái và toast.
