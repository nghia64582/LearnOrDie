# Product Specification --- Phase 1

## 1. Mục tiêu

Tạo một ứng dụng desktop Python Tkinter cho phép người dùng thiết kế
workflow bằng graph có nhánh, lưu thành một JSON file cho mỗi workflow,
mở lại và kiểm tra tính hợp lệ.

## 2. Đã chốt

-   Canvas: kéo thả node, chọn node và nối node bằng chuột
    (`drag_connect`).
-   Kết nối: hỗ trợ cả kéo từ output port sang node đích và chế độ click
    output port rồi click node đích (`both`).
-   Node types: đầy đủ Start, End, Action và Condition.
-   Edge rules: strict.
-   Xóa node: cascade, xóa node và mọi edge kề.
-   Persistence: một JSON file cho mỗi workflow.
-   Layout: free placement, lưu tọa độ node.
-   Undo/Redo: không thuộc giai đoạn 1.
-   Có workflow mẫu.

## 3. Tính năng bắt buộc

### 3.1 Workflow management

-   Liệt kê workflow trong thư mục dữ liệu.
-   Tạo workflow mới với một START mặc định.
-   Mở workflow.
-   Đổi tên workflow.
-   Lưu workflow.
-   Save As / duplicate workflow với ID mới.
-   Xóa workflow sau khi xác nhận.
-   Cảnh báo trước khi bỏ thay đổi chưa lưu.
-   Xử lý file JSON hỏng mà không làm ứng dụng crash.

### 3.2 Graph editor

-   Toolbox để thêm node.
-   Kéo node từ toolbox hoặc chọn loại node rồi click Canvas để thêm.
-   Chọn node và cạnh.
-   Kéo node để đổi vị trí.
-   Vẽ cạnh có mũi tên và nhãn cổng.
-   Nối bằng kéo dây hoặc click output port rồi click node đích.
-   Hủy thao tác nối bằng Escape.
-   Xóa cạnh riêng lẻ.
-   Xóa node theo cascade.
-   Pan/zoom Canvas.
-   Lưu tọa độ node và trạng thái viewport.
-   Không bắt buộc tự động layout.

### 3.3 Properties

-   Chỉnh sửa tên node.
-   Chỉnh tham số dựa trên node definition.
-   Hiển thị trường có kiểu phù hợp: text, number, checkbox, dropdown
    khi cần.
-   Cập nhật Canvas và trạng thái dirty sau thay đổi.
-   Node vừa tạo có giá trị mặc định và có thể chỉnh sửa ngay.

### 3.4 Validation

-   Có nút Validate.
-   Phân biệt Error và Warning.
-   Mỗi issue có severity, code, message và node/edge ID nếu liên quan.
-   Click issue để chọn node/cạnh tương ứng.
-   Validation không tự chạy workflow.
-   Cho phép lưu workflow nháp ngay cả khi có lỗi.

### 3.5 Persistence

-   Một file `.json` cho mỗi workflow.
-   Dùng UTF-8 và `json` module chuẩn.
-   Ghi file an toàn qua file tạm và replace.
-   Bảo toàn ID, tham số, vị trí, cạnh và viewport khi save/load.
-   `schema_version` bắt buộc.

## 4. Node types

-   `START`
-   `END`
-   `WAIT_IMAGE`
-   `CLICK_IMAGE`
-   `TYPE_TEXT`
-   `PRESS_KEY`
-   `WAIT_TIME`
-   `CHECK_IMAGE`

Node thao tác ảnh chỉ lưu cấu hình; không cần file ảnh tồn tại trong
giai đoạn 1.

## 5. Ngoài phạm vi

-   Screenshot, crop ảnh, image manager.
-   OpenCV/template matching.
-   PyAutoGUI hoặc điều khiển desktop.
-   Runtime thực thi workflow.
-   Retry, timeout runtime, execution logs.
-   Undo/Redo.
-   Tự động sắp xếp graph.
-   Chạy nhiều workflow đồng thời.

## 6. Tiêu chí nghiệm thu

-   Tạo, đổi tên, lưu, mở, Save As và xóa workflow.
-   Tạo được tất cả node types.
-   Kéo thả node; edge theo sát node.
-   Hai cách nối node hoạt động.
-   Kết nối sai bị từ chối với thông báo rõ.
-   Xóa node xóa toàn bộ edge liên quan.
-   Properties chỉnh được tên và params.
-   Validator phát hiện lỗi cấu trúc và cảnh báo reachability/loop.
-   Save/load không mất dữ liệu.
-   Workflow mẫu có nhánh `true`/`false`.
-   App chạy mà không cần thư viện nhận diện ảnh hoặc điều khiển
    desktop.
