# Architecture and Module Boundaries

## 1. Cấu trúc đề xuất

``` text
desktop_automation/
├── main.py
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main_window.py
│   └── app_state.py
├── models/
│   ├── __init__.py
│   ├── workflow.py
│   ├── node.py
│   ├── edge.py
│   └── node_definitions.py
├── ui/
│   ├── __init__.py
│   ├── workflow_list.py
│   ├── workflow_editor.py
│   ├── workflow_canvas.py
│   ├── properties_panel.py
│   ├── node_toolbox.py
│   ├── validation_panel.py
│   └── dialogs.py
├── services/
│   ├── __init__.py
│   └── workflow_service.py
├── engine/
│   ├── __init__.py
│   └── validator.py
├── storage/
│   ├── __init__.py
│   └── workflow_repository.py
├── data/
│   └── workflows/
└── tests/
    ├── test_models.py
    ├── test_validator.py
    ├── test_repository.py
    └── test_workflow_service.py
```

## 2. Trách nhiệm

-   `main.py`: khởi chạy ứng dụng.
-   `app/main_window.py`: cửa sổ gốc, điều hướng danh sách/editor.
-   `app/app_state.py`: workflow hiện tại, selected node/edge, dirty
    state.
-   `models/node.py`: node data.
-   `models/edge.py`: edge data.
-   `models/workflow.py`: tập hợp workflow, nodes và edges; chuyển đổi
    dict.
-   `models/node_definitions.py`: source of truth cho node type, ports,
    params, defaults và validation metadata.
-   `ui/workflow_list.py`: danh sách và thao tác CRUD.
-   `ui/workflow_editor.py`: ghép Canvas, Toolbox, Properties,
    Validation.
-   `ui/workflow_canvas.py`: rendering, drag, select, connect, pan/zoom.
-   `ui/properties_panel.py`: form chỉnh sửa thuộc tính theo definition.
-   `ui/node_toolbox.py`: lựa chọn node để thêm.
-   `ui/validation_panel.py`: danh sách issue và điều hướng tới đối
    tượng.
-   `ui/dialogs.py`: xác nhận xóa, lỗi file, cảnh báo bỏ thay đổi.
-   `services/workflow_service.py`: nghiệp vụ
    create/open/save/rename/duplicate/delete/validate.
-   `engine/validator.py`: kiểm tra graph độc lập với Tkinter.
-   `storage/workflow_repository.py`: thao tác file JSON.

## 3. Quy tắc phụ thuộc

1.  `models` không import Tkinter, `ui`, `services` hoặc `storage`.
2.  `node_definitions` không phụ thuộc UI.
3.  `validator` nhận model và trả về issue data; không hiển thị dialog.
4.  UI gọi service thay vì tự thao tác file.
5.  Repository không phụ thuộc UI.
6.  Không triển khai runtime executor trong phase 1.
7.  Canvas không sở hữu dữ liệu graph; nó phản ánh model hiện tại.
8.  Tránh circular imports.

## 4. Canvas implementation notes

Dùng `tkinter.Canvas` và `ttk`. Mỗi node có thể được vẽ bằng các Canvas
items; giữ mapping giữa `node_id` và item IDs. Tương tự giữ mapping cho
edges.

-   Node position trong model là tọa độ graph logic.
-   Pan/zoom không được làm hỏng tọa độ logic.
-   Vẽ edge dựa trên vị trí output/input port hiện tại.
-   Sau khi kéo node, chỉ cần cập nhật edge liên quan.
-   Tính toán vị trí port dựa trên node bounding box.
-   Dùng tag Canvas hoặc hit-testing để xác định node/edge/port được
    click.
-   Không phụ thuộc vào màu sắc để truyền đạt ý nghĩa duy nhất; luôn có
    label port.

## 5. Dirty state

Bất kỳ thay đổi nào làm đổi model đều đánh dấu workflow là dirty: -
add/delete/move node - add/delete edge - đổi tên node - sửa params - đổi
tên workflow

Lưu thành công thì dirty = false. Nếu đóng/mở workflow khi dirty, hỏi
người dùng có lưu, bỏ thay đổi hay hủy thao tác.

## 6. Lỗi và độ bền

-   Hiển thị lỗi file qua dialog/status message, không crash.
-   Save dùng file tạm cùng thư mục rồi `replace`.
-   Không ghi đè file workflow khác khi tên trùng.
-   Khi load file, kiểm tra schema và báo lỗi thân thiện.
-   Không tự sửa dữ liệu hỏng một cách âm thầm.
