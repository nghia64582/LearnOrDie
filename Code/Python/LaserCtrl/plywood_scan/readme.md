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
python scan_app.py                  # hoặc: python scan_app.py anh.jpg
python strip_packer.py              # hoặc: python strip_packer.py tam1_mask.json
```

Chạy từ trong thư mục `plywood_scan` (các file import lẫn nhau). Giao diện dùng
tiếng Anh. Trên Windows, app bật DPI awareness (`shcore.SetProcessDpiAwareness(1)`,
fallback `user32.SetProcessDPIAware()`) trước khi tạo cửa sổ để chữ không bị mờ
khi màn hình scale 125%/150%; kích thước panel tự nhân theo DPI (`ui_util.py`).

## Quy ước tọa độ (quan trọng)

- Gốc **(0, 0) = góc DƯỚI-TRÁI của tấm** = **góc số 4** khi chọn góc trong
  `scan_app` (*4 bottom-left (0,0)*). Trục x sang phải, trục **y hướng lên**, đơn vị mm. Giống canvas của
  `engraver_ctrl/tab_designer.py`, nên dán thẳng các dòng `R x y w h` vào là xem
  được.
- `R x y w h`: (x, y) là góc dưới-trái của thanh; thanh ngang có w = độ dài,
  h = độ rộng thanh, thanh dọc thì ngược lại.
- Khi cắt thật, đặt tấm lên máy sao cho góc 4 trùng gốc gcode và cạnh 4→3
  song song trục X của máy (đúng hướng như lúc chọn góc).
- Ảnh mask: hàng 0 = mép trên của tấm, nên `y_mm = (số_hàng − hàng) × mm_per_px`.

## Tool 1: scan_app.py

Các bước (tên bước như trên giao diện):

1. **Open image**: chọn ảnh tấm gỗ (*Open sheet photo...*), hoặc *Open saved
   mask (continue editing)...* để sửa tiếp mask đã lưu.
2. **Sheet size**: nhập *Width W* (cạnh trên, góc 1→2) và *Height H* (cạnh
   trái, góc 1→4) đo bằng thước. Kích thước điển hình khoảng **306 × 460 mm**
   nhưng mỗi tấm một khác, nên luôn đo lại.
   - **Độ phân giải mm/px được tính tự động**, không cần nhập:
     `rx = W / trung bình(px cạnh trên, px cạnh dưới)`,
     `ry = H / trung bình(px cạnh trái, px cạnh phải)`, và `mm_per_px = (rx + ry) / 2`.
     Nhờ vậy ảnh nắn giữ xấp xỉ độ phân giải gốc của ảnh chụp.
   - Muốn nhập tay thì tích *Advanced: override mm/px manually*.
3. **Pick 4 corners**:
   - *Auto-detect 4 corners* gợi ý 4 góc (vùng sáng lớn nhất, xấp xỉ tứ giác).
     Kéo các chấm màu để chỉnh, có kính lúp ở dưới bên trái. Lăn chuột để zoom,
     kéo chuột phải hoặc giữa để di chuyển, double-click chuột phải để vừa
     màn hình.
   - Thứ tự góc: 1 top-left, 2 top-right, 3 bottom-right, 4 bottom-left.
     *Rotate corner order 90 deg* xoay thứ tự nếu đặt nhầm.
   - Panel hiện ngay độ phân giải đang tính (mm/px và px/mm), kích thước ảnh
     nắn, và rx, ry. Nếu X/Y lệch quá 3% sẽ có cảnh báo: có thể đã nhập sai
     W × H hoặc đặt góc lệch.
4. **Check grid**: ảnh đã nắn kèm lưới mm (*Show mm grid*, *Grid step*, gốc
   dưới-trái) để đối chiếu với lưới 1cm của thảm cắt nhìn qua các lỗ.
   - *Measure mat grid through holes* đo chu kỳ lưới thảm bằng FFT và gợi ý kích
     thước tấm; bấm *Use suggested size* để áp dụng. Sai số vài % vì thảm nằm
     thấp hơn mặt gỗ.
   - *Rotate left/right 90* xoay kết quả.
5. **Mask**:
   - Phân đoạn tự động, mặc định *Combined (saturation + light)*: gỗ ít bão hòa
     và sáng, thảm xanh bão hòa cao, bóng trong lỗ tối. Có thêm HSV, L, Lab b*
     và K-means.
   - *Threshold* chỉnh bằng thanh trượt hoặc nút *Otsu*.
   - Làm sạch bằng *Open (denoise)*, *Drop wood specks*, *Fill small holes*,
     và *Cut border band* (coi một viền mép tấm là đã cắt).
   - Lớp phủ đỏ = đã cắt.
   - Cọ *Paint WOOD* / *Paint CUT* để sửa lỗi, *Undo (Ctrl+Z)* để hoàn tác.
     Nét tô được giữ lại khi đổi ngưỡng.
   - Mặc định *Close (fill gaps)* = 0, để không lấp mất các đường cắt mảnh.
6. **Safety margin**: co vùng gỗ vào một khoảng (mm), tính theo khoảng cách
   Euclid, để chừa mép cháy, kerf và sai số khi đặt lại tấm. Vùng màu cam là
   phần bị bỏ. Mép tấm cũng tính là mép cắt.
7. **Save** (*Save mask (PNG + JSON)...*) ghi `<ten>.png` (mask cuối, 255 = gỗ,
   0 = cắt), kèm theo:
   - `<ten>.json`: `{width_mm, height_mm, mm_per_px, px_per_mm, mm_per_px_mode
     ("auto"/"manual"), margin_mm, source, corners_px, ...}`
   - `<ten>_raw.png`: mask trước khi co margin, để mở lại sửa tiếp
   - `<ten>_warped.png`: ảnh đã nắn
   *Open in Strip Packer* mở luôn tool 2 với file vừa lưu.

Mẹo chụp: chụp thẳng từ trên xuống, đủ sáng, không bóng đổ, tấm phẳng, đặt trên
nền khác màu gỗ (thảm cắt xanh rất tốt).

## Tool 2: strip_packer.py

Tham số: *Strip width*, *Min length* / *Max length*, *Length step* (0 = tự do,
ví dụ 5 → 30, 35, 40, …), *Gap / kerf* (mặc định 0.5mm), *Orientation* (Both /
Horizontal / Vertical), *Objective* (Max total length / Max count). Bấm *Compute*.

Mọi tọa độ và độ dài xuất ra đều làm tròn tới 0.01 mm về phía trong vùng gỗ đã
kiểm tra, nên các dòng DSL vẫn hợp lệ dù mm/px tự động là số lẻ (ví dụ 0.5393).
Ở chế độ độ dài tự do, độ dài thanh sẽ lẻ (ví dụ 93.29). Muốn số tròn thì đặt
*Length step*, ví dụ 5.

Kết quả hiện lên ảnh (xanh lá = thanh ngang, xanh dương = thanh dọc), kèm số
thanh, tổng chiều dài và kết quả kiểm tra (*Check: OK*). Có các nút *Export DSL
(.txt)* (dòng `#` là chú thích, Designer bỏ qua), *Copy DSL* và *Save result
image (.png)*.

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
`sample/plywood_01.png`, với 4 góc chọn tay, kích thước **306 × 460 mm** và
mm/px tính tự động từ 4 góc. Kết quả gồm mask, ảnh kết quả và DSL. Script kiểm
tra không có thanh nào chồng nhau hoặc nằm ngoài gỗ, kể cả sau khi đọc ngược các
dòng DSL đã làm tròn.

## File

- `scan_app.py` – GUI tool 1
- `strip_packer.py` – GUI tool 2 (re-export hàm lõi)
- `scan_core.py` – xử lý ảnh: góc, nắn phối cảnh, phân đoạn, margin, lưu/đọc mask
- `pack_core.py` – thuật toán xếp thanh, kiểm tra, xuất DSL, vẽ kết quả
- `image_view.py` – canvas zoom/pan và kính lúp dùng chung
- `ui_util.py` – DPI awareness trên Windows và hệ số scale kích thước pixel
- `test_sample.py` – test không GUI
- `sample/plywood_01.png` – ảnh mẫu
