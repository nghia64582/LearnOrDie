# jar2java — Decompile JAR → .java để search trong IntelliJ / VS Code

Chuyển hàng loạt file `.jar` / `.war` thành mã nguồn `.java` (giữ nguyên cấu trúc package) để dùng **Ctrl+Shift+F** (global search) trong IDE.

## Chọn decompiler
| Decompiler | Chất lượng | Tốc độ | Java mới (records, sealed, switch pattern) |
|---|---|---|---|
| **Vineflower** (fork FernFlower, mặc định) | Tốt nhất, code dễ đọc, ít lỗi | Nhanh, đa luồng | Tốt (tới Java 21+) |
| CFR (fallback) | Tốt, rất bền với bytecode lạ/obfuscate | Rất nhanh | Khá (dừng phát triển từ 0.152) |
| Procyon | Khá, nhưng cũ | Chậm hơn | Kém với Java 17+ |

Mặc định dùng Vineflower; nếu jar nào lỗi sẽ tự thử lại bằng CFR.

## Cài đặt
- Python 3.9+ và Java 17+ (khuyên dùng [Temurin](https://adoptium.net)).
- Lần chạy đầu, tool tự tải Vineflower và CFR từ Maven Central vào thư mục `tools/`.
  (Máy không có mạng: tự copy `vineflower-*.jar`, `cfr-*.jar` vào `tools/`.)

## Cách dùng
```bash
# 1 jar
python3 jar2java.py lib/foo.jar -o output
# Cả thư mục (quét đệ quy), 8 luồng song song
python3 jar2java.py ~/.m2/repository/com/mycompany -o output -j 8
# Danh sách (mỗi dòng 1 jar/thư mục, dòng '#' là comment)
python3 jar2java.py -l jars.txt -o output
# Spring Boot fat jar + decompile luôn các jar trong BOOT-INF/lib (lọc theo regex)
python3 jar2java.py app.jar --nested --nested-filter "mycompany|common" -o output
# Dùng CFR làm mặc định / chạy lại toàn bộ bỏ qua cache
python3 jar2java.py app.jar -d cfr --force
```
Windows: `jar2java.bat C:\libs -o D:\out -j 8` hoặc PowerShell: `python .\jar2java.py C:\libs -o D:\out`.
Linux/macOS: `./jar2java.sh ...`. Đặt biến `JAVA=/path/to/java` nếu java không có trong PATH.

### Tuỳ chọn
| Option | Ý nghĩa |
|---|---|
| `-o DIR` | Thư mục output (mặc định `output`) |
| `-j N` | Số jar xử lý song song |
| `-d vineflower\|cfr` | Decompiler chính |
| `--no-fallback` | Không thử lại bằng CFR |
| `--nested` / `--nested-filter REGEX` | Decompile jar lồng (BOOT-INF/lib, WEB-INF/lib) → `output/<app>__libs/` |
| `--no-resources` | Không copy file tài nguyên (xml, properties, yml, ...) |
| `--force` | Bỏ qua cache hash, decompile lại |
| `--no-ide` | Không tạo `.vscode/settings.json` và `.iml` |
| `--xmx 4g` | Heap cho JVM decompiler (jar rất lớn) |

## Kết quả
```
output/
  <ten-jar>/org/.../*.java + resources   # Spring Boot: lấy từ BOOT-INF/classes
  <ten-app>__libs/<lib>/...              # khi dùng --nested
  jar2java-failures.log                  # jar lỗi + thông báo lỗi
  jar2java-report.json                   # thống kê từng jar
  .jar2java-cache.json                   # hash SHA-256 → jar không đổi sẽ được SKIP
  .vscode/settings.json, output.iml
```
Mở thư mục `output` bằng IntelliJ (File → Open) hoặc VS Code (File → Open Folder) rồi Ctrl+Shift+F.
Settings VS Code tắt Java language server import để không bị build/index nặng — chỉ dùng để search/đọc.

## Hạn chế
- Code decompile không phải 100% bản gốc: mất comment, tên biến local (nếu jar không có debug info), generic có thể bị sai; một số method phức tạp có thể ra code không compile được.
- Jar obfuscate (ProGuard...) thì vẫn khó đọc.
- Trùng tên jar ở các thư mục khác nhau → thư mục output có hậu tố `_xxxxxx`.
- Nếu có sẵn `-sources.jar` trên Maven thì nên dùng nó thay vì decompile.

## Giao diện đồ hoạ (GUI)

Chạy: `python3 jar2java_gui.py` — hoặc nhấp đúp `jar2java_gui.bat` (Windows, không hiện cửa sổ console) / `./jar2java_gui.sh` (Linux/macOS).

1. **Thêm file JAR...** (chọn nhiều file cùng lúc) hoặc **Thêm thư mục...** (quét cả thư mục con). Có thể xoá từng mục hoặc xoá hết.
2. Chọn **thư mục output**.
3. Tuỳ chọn: decompiler (vineflower/cfr), số luồng song song, dịch cả thư viện lồng bên trong + bộ lọc regex, chạy lại tất cả (bỏ qua cache).
4. Bấm **▶ Chạy**. Thanh tiến trình, trạng thái từng file và nhật ký cập nhật trực tiếp; giao diện không bị treo. **Huỷ** sẽ bỏ qua các file chưa chạy (file đang chạy sẽ chạy xong).
5. Xong thì bấm **Mở thư mục output**, rồi mở thư mục đó bằng IntelliJ / VS Code và Ctrl+Shift+F.

Yêu cầu: Python 3 có Tkinter (Windows/macOS có sẵn; Ubuntu: `sudo apt install python3-tk`) và Java 11+. Nếu thiếu Java, chương trình sẽ báo rõ ràng.
GUI dùng chung lõi với CLI (`jar2java.run()`), nên kết quả giống hệt bản dòng lệnh.

## Index @MetaInfo (tên class mã hoá ↔ tên thật)

Mặc định tool đọc annotation `@MetaInfo(name = "Tx::ClassName")` **trực tiếp từ bytecode** (`.class`). Cách này không phụ thuộc decompiler, không cần thư viện ngoài, và chạy được cả với retention CLASS/RUNTIME.
- Nhận `MetaInfo` ở **bất kỳ package nào** (so theo tên ngắn). Đọc thuộc tính `name`; nếu không có thì đọc `value`, rồi đến chuỗi đầu tiên.
- Lấy cả **class lồng/inner class** (vd. `a.b.xQ_9z$iI1`).
- Kết quả:
  - Mỗi jar: `<output>/<jar>/metainfo-index.txt` (2 cột, cách nhau bằng tab) và `metainfo-index.md` (bảng).
  - Gộp ở thư mục output: `metainfo-index.txt` / `.md` (2 cột), cùng `metainfo-index-by-jar.txt` / `.md` (thêm cột jar).

Ví dụ `metainfo-index.txt`:
```
a.b.xQ_9z	Tx::Foo
a.b.xQ_9z$iI1	Tx::Foo.Inner
```
Tuỳ chọn CLI: `--no-metainfo` (tắt), `--metainfo-annotation TenKhac`, `--metainfo-attr name`. Trên GUI có ô tick "Tạo file index @MetaInfo" và ô "Tên annotation".

## Nhiều jar trùng tên ở các thư mục khác nhau

- Jar có tên không trùng thì giữ nguyên tên thư mục (`server/`).
- Khi có jar trùng tên (không phân biệt hoa thường, như trên Windows), mỗi jar thêm **số thư mục cha ít nhất đủ để phân biệt**, nối bằng `__`:
  - `D:\work-space\server.jar` → `work-space__server/`
  - `D:\work-space-2\server.jar` → `work-space-2__server/`
  - Nếu trùng tới tận gốc thì thêm cả ổ đĩa: `D__work-space__server/` và `E__work-space__server/`.
- Ký tự không hợp lệ trên Windows (`<>:"/\|?*`) được thay bằng `_`. Tên dài quá 120 ký tự được cắt bớt và thêm hash ngắn.
- Bảng ánh xạ jar → thư mục nằm trong `jar2java-mapping.json`, và log (CLI/GUI) in các dòng `MAP ... -> ...`.
- Cache tính theo **đường dẫn đầy đủ** của jar, kèm tên thư mục output.
