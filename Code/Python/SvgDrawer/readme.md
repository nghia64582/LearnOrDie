### TOOL TẠO SVG VÀ G-CODE CẮT LASER
  - Mô tả:
    + Các hình cần cắt thường là hình tròn, đa giác (chữ nhật, hình vuông, ...), đoạn thẳng.
    + Cần một tool để nhanh chóng tạo file svg và g-code để cắt các hình này
  - Yêu cầu:
    - UX:
      - Chỉnh sửa một file txt, mỗi khi lưu file thì tự động cập nhật file svg và g-code
  - Promt:
    - Tạo một tool html,css,js để tạo file svg và g-code như sau
      - File svg và g-code có góc tọa độ (0, 0) nằm ở trái dưới, trục y hướng lên trên, trục x hướng 
        sang phải
      - Một text field (Shapes) ở bên trái để nhập các hình trong file cần tạo
      - Các text field và label để điền các thông số cắt laser:
        + Tốc độ cắt (mm/min)
        + Công suất laser (%)
      - Một nút "Generate" để tạo file svg và g-code
      - Một nút "Preview" để hiện thị svg trong một khung bên phải
      - Format nhập vào Shapes là:
        + Mỗi dòng là một hình
        + Hình tròn: "C x y r" (x,y là tâm, r là bán kính)
        + Hình chữ nhật: "R x y w h" (x,y là góc trên bên trái, w là chiều rộng, h là chiều cao)
        + Đoạn thẳng (2 điểm): "L x1 y1 x2 y2" (x1,y1 là điểm đầu, x2,y2 là điểm cuối)
        + Đoạn thẳng ngang (1 điểm + chiều dài): "LH x y l" (x,y là điểm đầu, l là chiều dài)
        + Đoạn thẳng dọc (1 điểm + chiều dài): "LV x y l" (x,y là điểm đầu, l là chiều dài)