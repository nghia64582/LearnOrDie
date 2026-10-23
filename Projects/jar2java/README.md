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
