# Dự án làm tool auto click

## 1. Mục tiêu
Tạo một ứng dụng desktop Python Tkinter cho phép người dùng thiết kế và chạy workflow, là các quy trình tự động tương tác với ứng dụng, web dựa trên UI.

## 2. Các thực thể và định nghĩa trong ứng dụng
1. Hình ảnh:
 - Là các hình ảnh dùng cho các bước đợi ảnh, click ảnh.
2. Workflow:
 - Là quy trình một tập hợp các bước trong 
3. Step:
 - Là một bước trong workflow.
 - Có thể là một trong các tính năng đợi ảnh xuất hiện, click ảnh, click tọa độ, gõ text, gõ chữ
 - Có thể được edit
 - Cần được lưu vào file (txt, json, ...)
 - 
4. Thực thi:
 - Là việc chạy một workflow.
 - Có thông báo về việc 

## 3. Các thư viện, công cụ, thiết kế áp dụng cho ứng dụng
- Python 3.11  : ngôn ngữ chính
- Canvas       : Mô phỏng bằng ảnh cho workflow
- Tkinter      : Dùng để giao diện
- PyAutoGUI    : Dùng để thao tác với UI như click hoặc gõ text

## 4. Các UI/page cần có
- Giao diện chính sẽ gồm các tab chính
- Tab 1: Thêm/xóa/sửa/chạy các workflow
- Tab 2: Thêm/sửa/xóa các hình ảnh

## 5. Các flow UX cần có
- Thêm sửa xóa các hình ảnh (dùng cho các bước đợi, click ảnh)
- Thêm/xóa/chạy các workflow
- Chỉnh sửa workflow.

## 6. Cấu trúc chính dự án (có thể cập nhật thêm)
```
├── main.py
├── spec.md
├── app/
│   ├── __init__.py
│   ├── main_window.py
├── models/
│   ├── __init__.py
│   ├── workflow.py
│   ├── node.py
│   ├── step.py
├── ui/
│   ├── __init__.py
├── data/
│   ├── workflows/
│   └── images/
```

## 7. Yêu cầu kỹ thuật
 - Không cần viết test cho mỗi bước, có thể để dev tương tác với giao diện để test.

## 8. Các milestone chính
1. Hoàn thành các model ứng với các entities chính
2. Hoàn thành giao diện xem/thêm/xóa ảnh
3. Hoàn thành giao diện xem/thêm/xóa workflow
4. Hoàn thành tính năng chạy workflow.