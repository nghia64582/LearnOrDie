# Workflow Graph Editor --- Project Docs

Tài liệu đặc tả cho MVP giai đoạn 1 của ứng dụng Python Tkinter Workflow
Graph Editor.

## Đọc theo thứ tự

1.  `SPEC.md` --- phạm vi và tiêu chí nghiệm thu.
2.  `ARCHITECTURE.md` --- cấu trúc module và nguyên tắc phụ thuộc.
3.  `DATA_MODEL.md` --- model Python và schema JSON.
4.  `NODE_CATALOG.md` --- node types, ports và tham số.
5.  `VALIDATION.md` --- quy tắc validation.
6.  `IMPLEMENTATION_PLAN.md` --- các chặng triển khai.
7.  `AGENT_PROMPT.md` --- prompt để giao cho coding agent.

## Mục tiêu

Xây ứng dụng desktop bằng Python + Tkinter để tạo, chỉnh sửa, validate
và lưu workflow dạng graph. Giai đoạn này chỉ làm editor và persistence;
chưa nhận diện ảnh, chưa điều khiển desktop, chưa chạy workflow.

## Công nghệ

-   Python 3.11+
-   Tkinter / `tkinter.ttk`
-   Thư viện chuẩn Python là đủ cho MVP.
-   `pytest` là tùy chọn để chạy test.

## Khởi chạy mục tiêu

Sau khi agent triển khai xong:

``` bash
python main.py
```

## Nguyên tắc

-   Model không phụ thuộc Tkinter.
-   Quy tắc node được định nghĩa tập trung.
-   Canvas chỉ vẽ và chuyển input thành lệnh cập nhật model.
-   Đọc/ghi file đi qua repository/service.
-   Lưu được workflow nháp chưa hợp lệ.
-   Không triển khai giả nhận diện ảnh hoặc thao tác desktop trong giai
    đoạn 1.
