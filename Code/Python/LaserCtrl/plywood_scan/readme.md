# plywood_scan

Hai tool để tận dụng phần plywood còn lại sau nhiều lần cắt (mỗi lần cắt tấm bị
đặt lại nên không dựng lại được từ gcode cũ):

1. **`scan_app.py`**: chuyển ảnh chụp tấm gỗ thành **file mask nhị phân**
   (255 = gỗ còn, 0 = đã cắt) kèm file JSON kích thước.
2. **`strip_packer.py`**: đọc mask, tính cách xếp các **thanh chữ nhật** (mặc
   định rộng 10mm, dài 30–100mm) rồi xuất lệnh DSL `R x y w h` để dán vào tab
   Designer.

## Cài đặt

```bash
pip install -r requirements.txt     # opencv-python, numpy, pillow
python scan_app.py                  # hoac: python scan_app.py anh.jpg
python strip_packer.py              # hoac: python strip_packer.py tam1_mask.json
```

Chạy từ trong thư mục `plywood_scan` (các file import lẫn nhau).

## Quy ước tọa độ (quan trọng)

- Gốc **(0, 0) = góc DƯỚI-TRÁI của tấm** = **góc số 4** khi chọn góc trong
  `scan_app`. Trục x sang phải, trục **y hướng lên**, đơn vị mm. Giống canvas của
  `engraver_ctrl/tab_designer.py`, nên dán thẳng các dòng `R x y w h` vào là xem
  được.
- `R x y w h`: (x, y) là góc dưới-trái của thanh; thanh ngang có w = độ dài,
  h = độ rộng thanh, thanh dọc thì ngược lại.
- Khi cắt thật, đặt tấm lên máy sao cho góc 4 trùng gốc gcode và cạnh 4→3
  song song trục X của máy (đúng hướng như lúc chọn góc).
- Ảnh mask: hàng 0 = mép trên của tấm, nên `y_mm = (số_hàng − hàng) × mm_per_px`.

## Tool 1: scan_app.py

Các bước:

1. **Mở ảnh**: chọn ảnh tấm gỗ, hoặc *Mở mask đã lưu* để sửa tiếp.
2. **Kích thước tấm**: W (cạnh trên, góc 1→2), H (cạnh trái, góc 1→4) đo bằng
   thước, và độ phân giải mm/pixel (mặc định 0.5).
3. **Chọn 4 góc**: tự gợi ý 4 góc (tìm vùng sáng lớn nhất rồi xấp xỉ tứ giác),
   kéo các chấm màu để chỉnh, có kính lúp ở góc trái dưới. Lăn chuột để zoom,
   chuột phải hoặc giữa kéo để di chuyển, double-click chuột phải để vừa màn hình.
   Thứ tự 1 trên-trái, 2 trên-phải, 3 dưới-phải, 4 dưới-trái; nút *Đổi thứ tự
   góc* xoay thứ tự 90° nếu đặt nhầm.
4. **Kiểm tra lưới**: ảnh đã nắn phối cảnh kèm lưới mm (mặc định 10mm, gốc
   dưới-trái) để đối chiếu với lưới 1cm của thảm cắt nhìn qua các lỗ. Nút *Đo
   lưới thảm qua các lỗ* đo chu kỳ lưới thảm bằng FFT và gợi ý kích thước tấm
   (sai số vài % vì thảm nằm thấp hơn mặt gỗ). Có nút xoay kết quả 90°.
5. **Tạo mask**: phân đoạn tự động (mặc định *Kết hợp*: gỗ ít bão hòa và sáng,
   thảm xanh bão hòa cao, bóng trong lỗ tối), ngưỡng chỉnh bằng thanh trượt
   hoặc Otsu, có thêm K-means. Làm sạch bằng mở hình thái, bỏ đốm gỗ và lỗ nhỏ,
   tùy chọn coi một viền mép tấm là đã cắt. Lớp phủ đỏ = đã cắt. Có cọ *Tô GỖ*
   và *Tô CẮT* để sửa lỗi, Ctrl+Z để hoàn tác. Nét tô được giữ lại khi đổi ngưỡng.
   - Mặc định *Đóng* = 0, vì đóng hình thái có thể lấp mất các đường cắt mảnh
     (vết cắt chưa tách rời vật liệu). Hãy kiểm tra và tô CẮT các đường này.
6. **Khoảng an toàn**: co vùng gỗ vào một khoảng (mm), tính theo khoảng cách
   Euclid, để chừa mép cháy, kerf và sai số khi đặt lại tấm. Vùng màu cam là
   phần bị bỏ. Mép tấm cũng tính là mép cắt.
7. **Lưu** `<ten>.png`, kèm theo:
   - `<ten>.json` `{width_mm, height_mm, mm_per_px, margin_mm, source, ...}`
   - `<ten>_raw.png` mask trước khi co margin, để mở lại sửa tiếp
   - `<ten>_warped.png` ảnh đã nắn
   Nút *Mở trong Strip Packer* mở luôn tool 2 với file vừa lưu.

Mẹo chụp: chụp thẳng từ trên xuống, đủ sáng, không bóng đổ, tấm phẳng, đặt trên
nền khác màu gỗ (thảm cắt xanh rất tốt).

## Tool 2: strip_packer.py

Tham số: bề rộng thanh, dài tối thiểu/tối đa, bước độ dài (0 = tự do, ví dụ 5 →
30, 35, 40, …), khoảng cách giữa 2 thanh (kerf, mặc định 0.5mm), hướng (cả hai /
ngang / dọc), mục tiêu (tổng chiều dài lớn nhất hoặc nhiều thanh nhất).

Kết quả hiện lên ảnh (xanh lá = thanh ngang, xanh dương = thanh dọc), kèm số
thanh, tổng chiều dài và kết quả kiểm tra hợp lệ. Xuất được DSL (`.txt`, các
dòng `#` là chú thích mà Designer bỏ qua), copy DSL, hoặc lưu ảnh kết quả.

Thuật toán (`pack_core.py`):
- Với một hướng, mỗi "dải" cao bằng bề rộng thanh chia thành các đoạn liên tục
  toàn gỗ. Mỗi đoạn dài n được chia tối ưu thành các thanh bằng knapsack (độ
  dài cho phép, có gap). Sau đó quy hoạch động chọn tập dải không chồng nhau tốt
  nhất. Trong một hướng, với kiểu xếp theo dải, kết quả là tối ưu.
- Kết hợp 2 hướng bằng cách thử: chỉ ngang, chỉ dọc, ngang trước rồi lấp phần
  còn lại bằng dọc (xen kẽ), dọc trước rồi ngang, và chọn chiến lược theo từng
  vùng gỗ liên thông. Lấy phương án tốt nhất.
- `verify_strips` kiểm tra lại: mỗi thanh nằm trọn trong gỗ, không chồng nhau,
  và cách nhau ≥ gap.

Dùng như thư viện:

```python
from strip_packer import pack_strips, load_mask_file, strips_to_dsl
mask, meta, _ = load_mask_file("tam1_mask.json")
res = pack_strips(mask, meta["mm_per_px"], strip_w=10, min_len=30, max_len=100,
                  step=0, gap=0.5, orient="both", objective="length")
print(res["count"], res["total_length"])
print("\n".join(strips_to_dsl(res["strips"])))
```

## Test

`python test_sample.py [thu_muc_out]` chạy toàn bộ pipeline không cần GUI trên
`sample/plywood_01.png`, với 4 góc chọn tay và kích thước **giả định 300×450mm**
(ước lượng từ lưới 1cm của thảm, chưa đo thật). Kết quả gồm mask, ảnh kết quả
và DSL, và script kiểm tra không có thanh nào chồng nhau hoặc nằm ngoài gỗ.

## File

- `scan_app.py` – GUI tool 1
- `strip_packer.py` – GUI tool 2 (re-export hàm lõi)
- `scan_core.py` – xử lý ảnh: góc, nắn phối cảnh, phân đoạn, margin, lưu/đọc mask
- `pack_core.py` – thuật toán xếp thanh, kiểm tra, xuất DSL, vẽ kết quả
- `image_view.py` – canvas zoom/pan và kính lúp dùng chung
- `test_sample.py` – test không GUI
- `sample/plywood_01.png` – ảnh mẫu
