# app/

Khởi tạo cửa sổ chính và định nghĩa đường dẫn dữ liệu.

## File

- **`paths.py`**
  - `ROOT_DIR` là thư mục dự án (cha của `app/`).
  - `DATA_DIR = data/`, `IMAGES_DIR = data/images/`, `WORKFLOWS_DIR = data/workflows/`, `IMAGES_INDEX = data/images/index.json`.
  - `ensure_data_dirs()` tạo các thư mục nếu chưa có.
- **`main_window.py`**: lớp `MainWindow(tk.Tk)`.
  - Kích thước 1100x640, tối thiểu 900x520.
  - Tạo `ImageLibrary` và `WorkflowStore` dùng chung.
  - `ttk.Notebook` có 2 tab: **"Workflow"** (`ui.workflows_tab.WorkflowsTab`) và **"Hình ảnh"** (`ui.images_tab.ImagesTab`).
  - Khi đổi tab (`<<NotebookTabChanged>>`):
    - Sang tab Workflow: gọi `refresh_images()` để đọc lại thư viện ảnh, giúp danh sách ảnh trong form bước được cập nhật.
    - Sang tab Hình ảnh: gọi `refresh_list()`.
- **`__init__.py`**: chỉ có docstring.

## Lưu ý

Các module `models/` import hằng số đường dẫn từ đây **lúc import**. Muốn đổi thư mục dữ liệu (ví dụ khi test) thì phải sửa `app.paths` trước khi import `models`, hoặc truyền đường dẫn vào `ImageLibrary(images_dir=..., index_path=...)` / `WorkflowStore(workflows_dir=...)`.
