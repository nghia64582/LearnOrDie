- Đây là folder lưu trữ dữ liệu giả, giúp dev có thể tạo data ngẫu nhiên, cho phép chạy demo chương
  trình thay vì nhập tay.
- Quy trình là chạy image mysql trong docker, sau đó, một script sẽ được chạy để thêm các dữ liệu vào
  trong mysql.
- Có thể dùng docker volumn để sử dụng dữ liệu này
- Cấu trúc dữ liệu: 
    - Images: Chứa các ảnh của các sản phẩm, cấu trúc chung của thư mục là 
        - product/<category>/product_<id>/
        - category: là tên của danh mục sản phẩm, ví dụ: "clothes", "shoes", "accessories"
        - id: là id của sản phẩm, ví dụ: 1, 2, 3, ...
        - Trong mỗi thư mục, sẽ có các ảnh của sản phẩm, với tên là "image_1.jpg", "image_2.jpg", ...
    - Data: Chứa các file dữ liệu, với cấu trúc là