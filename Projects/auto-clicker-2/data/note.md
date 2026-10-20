# data/

Nơi ứng dụng lưu dữ liệu người dùng. Đường dẫn được định nghĩa trong `app/paths.py`.

- **`workflows/`**: mỗi workflow là một file `<workflow_id>.json` do `models/workflow_store.py` ghi. Định dạng xem trong [../models/note.md](../models/note.md).
- **`images/`**: các ảnh mẫu được copy vào với tên `<image_id>.<đuôi>`, cùng file chỉ mục `index.json` (`{"images": [{id, name, filename, created_at, updated_at}]}`) do `models/image_library.py` quản lý.

Nội dung hai thư mục này bị `.gitignore` bỏ qua, chỉ giữ `.gitkeep`. Vì vậy workflow và ảnh **không được commit** và chỉ tồn tại trên máy đang dùng.
