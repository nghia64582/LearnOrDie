# plywood_scan

Hai tool để tận dụng phần plywood còn lại sau nhiều lần cắt (mỗi lần cắt tấm bị
đặt lại nên không dựng lại được từ gcode cũ):

1. **`scan_app.py`**: chuyển ảnh chụp tấm gỗ thành **file mask nhị phân**
   (255 = gỗ còn, 0 = đã cắt) kèm file JSON kích thước.
2. **`strip_packer.py`**: đọc mask, xếp **đúng danh sách thanh cần cắt** (ví dụ
   `80,80,100,100`, rộng mặc định 10mm), báo thanh nào không vừa, rồi xuất DSL
   dạng `ADD x y <số> / R 0 0 w h / END` để dán vào tab Designer.

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
  `engraver_ctrl/tab_designer.py`, nên dán thẳng DSL xuất ra vào là xem
  được.
- Mỗi thanh xuất ra là một khung tọa độ cục bộ:
  ```
  ADD x y <số thứ tự>
  R 0 0 w h
  END
  ```
  (x, y) là góc dưới-trái của thanh trên tấm. Thanh ngang là `R 0 0 L 10`,
  thanh dọc là `R 0 0 10 L`. Giữa `R` và `END` có thể thêm chi tiết như JF/JM
  hay lỗ, tọa độ tính từ góc dưới-trái của thanh. Số sau `ADD` là nhãn mà
  Designer vẽ trên canvas.
- **Tọa độ máy = tọa độ tấm + offset** (mặc định offset 0, 0, nghĩa là góc
  dưới-trái của tấm = gốc 0,0 của máy). Gcode căn chỉnh và DSL cắt dùng
  **chung** offset này: offset lưu trong JSON, Strip Packer tự cộng vào `ADD x y`.
- Khi cắt thật, đặt tấm lên máy theo đúng hướng như lúc chọn góc, rồi căn bằng
  gcode căn chỉnh (bước 7 bên dưới).
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
7. **Alignment marks**: click chọn **2 điểm** bất kỳ trên ảnh tấm (user tự
   quyết, nên chọn 2 điểm cách xa nhau, ví dụ góc của 2 lỗ ở hai đầu tấm).
   - *Click sets: P1 / P2* chọn điểm sẽ đặt khi click; đặt xong P1 thì tự
     chuyển sang P2. Kéo dấu + để chỉnh, hoặc gõ tọa độ mm vào ô P1/P2 X/Y.
     Dùng zoom và kính lúp được.
   - Panel hiện tọa độ từng điểm (mm, gốc dưới-trái, X phải, Y lên) và
     **Distance P1-P2**, kèm dX, dY, để đo lại bằng thước trên tấm thật.
   - Thông số gcode: *Cross size* 5mm (mỗi nét dài 5mm, tâm tại điểm), *Power S
     (0-1000)* 100 (= 10%), *Feed* 200 mm/min, *Offset X/Y* 0, và *Return to
     origin at the end*.
   - *Show gcode* để xem gcode. *Send to Machine tab* ghi đè
     `engraver_ctrl/cut_plan.gcode`, là file tab Machine chạy (có hỏi xác nhận
     trước).
   - Gcode theo đúng quy ước của `tab_designer.generate_bounds_gcode`: `G21`,
     `G90`, mỗi nét gồm `G0` tới điểm đầu, `M3 S100`, `G1 … F200`, `M5`, nên
     laser luôn tắt khi di chuyển. Cuối file là `G0` về gốc (offset) và `M5`.
   - Quy trình: đặt tấm lên máy, chạy gcode căn chỉnh, xem 2 dấu + so với 2
     điểm trên tấm, xê dịch tấm, chạy lại cho tới khi trùng. Sau đó mới chạy
     gcode cắt.
8. **Save**: lưu vào **`plywood_scan/output/<name>/`**. *Name* mặc định là tên
   file ảnh (sửa được), thư mục cha đổi được bằng nút `...`. Nếu thư mục đã có
   file, app hỏi: *Yes* = ghi đè, *No* = lưu sang `<name>_2` (hoặc `_3`, …),
   *Cancel* = không lưu. Các file được ghi:
   - `mask.png`: mask cuối, 255 = gỗ, 0 = cắt
   - `mask.json`: `{width_mm, height_mm, mm_per_px, px_per_mm, mm_per_px_mode,
     margin_mm, source, corners_px, alignment: {points_mm, cross_mm, power,
     feed, offset_mm, return_home, gcode_file}, ...}`
   - `mask_raw.png`: mask trước khi co margin, để mở lại sửa tiếp
   - `mask_warped.png`: ảnh đã nắn
   - `alignment.gcode`: gcode căn chỉnh
   Mở lại bằng *Open saved mask* sẽ khôi phục cả 2 điểm căn chỉnh, và lần lưu
   sau ghi vào đúng thư mục đó. *Open in Strip Packer* mở luôn tool 2. Thư mục
   `output/` đã nằm trong `.gitignore`.

Mẹo chụp: chụp thẳng từ trên xuống, đủ sáng, không bóng đổ, tấm phẳng, đặt trên
nền khác màu gỗ (thảm cắt xanh rất tốt).

## Tool 2: strip_packer.py

Font chữ to hơn scan_app 2pt cho dễ đọc. Có 2 chế độ (*Mode*).

**Required pieces** (mặc định, chế độ chính):
- *Piece lengths (mm)*: danh sách độ dài cần cắt, ngăn cách bằng dấu phẩy, dấu
  cách hoặc chấm phẩy, ví dụ `80,80,100,100`. Viết `100x3` nghĩa là 3 thanh
  100mm. Số thứ tự của thanh là thứ tự trong danh sách (1, 2, 3, …). Nhập sai
  (chữ, số ≤ 0) sẽ báo lỗi.
- *Strip width*: mặc định 10mm. *Gap / kerf*: khoảng cách tối thiểu giữa 2
  thanh, mặc định 0.5mm. *Orientation*: Both / Horiz. (X) / Vert. (Y).
- Độ dài giữ **đúng như nhập**, làm tròn tới 0.01mm. Số pixel mỗi thanh chiếm
  luôn đủ chứa đúng độ dài đó, kể cả khi mm/px là số lẻ.
- Thuật toán (`pack_pieces`):
  - Thử nhiều thứ tự xếp: dài trước, theo thứ tự nhập, ngắn trước, và vài
    thứ tự ngẫu nhiên (trong giới hạn khoảng 6 giây).
  - Ghép với 2 quy tắc chọn vị trí: tiếp xúc nhiều nhất với mép hoặc thanh đã
    đặt (xếp chặt), và gần góc dưới-trái nhất. Ghép tiếp với ưu tiên hướng
    (H+V, chỉ H, chỉ V).
  - Mỗi vị trí ứng viên được kiểm tra bằng ảnh tích phân, nên luôn nằm trọn
    trong gỗ và cách các thanh khác ít nhất một gap.
  - Chọn phương án **đặt được nhiều thanh nhất**, sau đó tổng chiều dài lớn
    nhất, sau đó gọn và gần gốc (0,0). Vì ưu tiên số thanh, khi danh sách quá
    nhiều thì thanh dài có thể bị bỏ để nhét được nhiều thanh ngắn hơn.
- Kết quả: *Placed n / N pieces* và dòng đỏ *Did not fit: #3 (500 mm), …* liệt kê
  các thanh không vừa (cũng ghi thành dòng `#` trong DSL). Trên ảnh, mỗi thanh
  có ghi số thứ tự (*Piece numbers*).

**Auto-fill** (chế độ phụ): tự lấp đầy vùng gỗ bằng các thanh dài trong
[*Min length*, *Max length*] (*Length step* 0 = tự do), mục tiêu *Max total
length* hoặc *Max count*. Thuật toán (`pack_strips`):
- Với mỗi hướng, mỗi dải cao bằng bề rộng thanh được chia tối ưu thành các
  thanh bằng knapsack.
- Quy hoạch động chọn tập dải tốt nhất.
- Kết hợp 2 hướng: ngang trước rồi lấp dọc, dọc trước rồi lấp ngang, hoặc
  chọn theo từng vùng gỗ liên thông.

Nếu JSON có điểm căn chỉnh, Strip Packer vẽ P1/P2 (dấu + và tọa độ) và đường
nối lên ảnh kết quả, hiện khoảng cách P1-P2, và cộng offset máy vào `ADD x y`
(có ghi chú trong DSL khi offset khác 0). Hộp thoại mở file mặc định ở
`output/`.

Nút: *Compute*, *Export DSL (.txt)* (dòng `#` là chú thích, Designer bỏ qua),
*Copy DSL*, *Save result image (.png)*. Kết quả luôn được kiểm tra lại
(*Check: OK*) bằng `verify_strips`: mỗi thanh nằm trọn trong gỗ, không chồng
nhau, và cách nhau ≥ gap.

Dùng như thư viện:

```python
from strip_packer import pack_pieces, parse_lengths, load_mask_file, strips_to_dsl
mask, meta, _ = load_mask_file("tam1_mask.json")
res = pack_pieces(mask, meta["mm_per_px"], parse_lengths("80,80,100,100"),
                  strip_w=10, gap=0.5, orient="both")
print(res["count"], res["unplaced"])          # unplaced: [{"id", "length"}]
print("\n".join(strips_to_dsl(res["strips"])))  # ADD / R 0 0 w h / END
```

## Test

`python test_sample.py [thu_muc_out]` chạy toàn bộ pipeline không cần GUI trên
`sample/plywood_01.png`, với 4 góc chọn tay, kích thước **306 × 460 mm** và
mm/px tính tự động từ 4 góc. Script chạy các trường hợp sau:
- Danh sách `80,80,100,100`.
- Danh sách 93 thanh quá nhiều so với chỗ trống, để kiểm tra báo thanh không vừa.
- Danh sách có thanh quá dài (500mm).
- Chế độ Auto-fill.
Với mỗi trường hợp, script kiểm tra không có thanh nào chồng nhau hoặc nằm ngoài
gỗ, độ dài đúng như nhập, và các dòng DSL `ADD/R/END` đọc ngược lại khớp vị trí
và số thứ tự.

Script còn lưu kết quả vào `<thu_muc_out>/plywood_01/` giống app, với 2 điểm
căn chỉnh mẫu, rồi mô phỏng `alignment.gcode` để kiểm tra:
- Mỗi điểm có đúng 2 nét vuông góc dài 5mm, tâm đúng tại điểm.
- Mọi nét cắt là S100 và F200.
- Không có `G0` nào khi laser đang bật, và file kết thúc bằng `M5` ở gốc.
- Offset được cộng đúng.

## File

- `scan_app.py` – GUI tool 1
- `strip_packer.py` – GUI tool 2 (re-export hàm lõi)
- `scan_core.py` – xử lý ảnh: góc, nắn phối cảnh, phân đoạn, margin, lưu/đọc mask
- `pack_core.py` – thuật toán xếp thanh, kiểm tra, xuất DSL, vẽ kết quả
- `align_core.py` – điểm căn chỉnh: sinh gcode dấu +, mô phỏng gcode để test
- `image_view.py` – canvas zoom/pan và kính lúp dùng chung
- `ui_util.py` – DPI awareness trên Windows và hệ số scale kích thước pixel
- `test_sample.py` – test không GUI
- `sample/plywood_01.png` – ảnh mẫu
