Code khá ok rồi, nhưng tôi cần một cải tiến lớn:
  + Hiện tại yêu cầu là cắt thành các thanh nhỏ hình chữ nhật, tôi muốn thêm là các thanh nhỏ này 
có thể có đầu bo tròn (một trong hai hoặc cả hai đầu, dường kính bằng độ rộng que, tâm bo có tọa độ
x nằm ở chính giữa que là r / 2 + (r + c) * k, y là dưới đoạn cắt một khoảng bằng bán kinh bo hay r 
/ 2 ), và có các lỗ tròn nhỏ trong que để bắt vít nữa.
Chính vì vậy chương trình cần thêm các chỉnh sửa sau:
  + Mỗi chi tiết cần các thông số sau:
    + Chiều dài (có sẵn)
    + Tọa độ các lỗ (cần thêm)
    + Bo đầu dưới (cần thêm)
    + Bo đầu trên (cần thêm)
  + Giao diện cần thay đổi:
    + Thêm trường c là bán kính lỗ (dùng chung cho tất cả các lỗ)
    + Vì mỗi chi tiết có nhiều thông số hơn, nên textfield List a[i] cũ sẽ thành một text field lớn
      nhiều dòng với cấu trúc mỗi dòng như sau:
        - d,bo_lower,bo_upper,a1,a2,a3,...
          + d: chiều dài
          + bo_lower: 0 hoặc 1 (0 là không bo đầu dưới, 1 là bo đầu dưới)
          + bo_upper: 0 hoặc 1 (0 là không bo đầu trên, 1 là bo đầu trên)
          + a1,a2,...: tọa độ các lỗ trên thanh (a[i] là khoảng cách từ đường cắt dưới đến lỗ cần cắt)
        + VD:
          + 100,0,0,20.53,50.3: Cắt thanh nhỏ chiều dài 100mm, không bo 2 đầu, và 2 lỗ ở 20.53mm, 50.3mm
          + 150,1,0: Cắt thanh nhỏ chiều dài 150mm, bo dưới, không bo trên, không có lỗ
=> Như vậy, phần tính toán các đoạn cắt vẫn như cũ, chỉ khác là có thêm bo tròn và lỗ tròn trên mỗi thanh.