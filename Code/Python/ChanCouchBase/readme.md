- Các tính năng chính:
  + Lấy đọc json từ uid + model
  + Viết json vào uid + model
  + Chọn nhanh các model đã có
  + Chọn nhanh các uid các nick cũ
- Build exe file (mỗi lần update code):
 + Yêu cầu: Không console, có icon, đọc file .txt trong folder minify/, file model_key_name.txt, chạy main.py
 
 + S1: pip install pyinstaller (nếu chưa cài)
 + S2: vào console thư mục chứa file main.py
 + S3: pyinstaller --noconsole --icon=icon.ico --add-data "minify;minify" --add-data "model_key_name.txt;." main.py