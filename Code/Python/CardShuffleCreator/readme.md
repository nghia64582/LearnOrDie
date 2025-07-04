 - Công dụng:
  + Tạo bộ bài ngẫu nhiên bằng giao diện.
  + Lưu các bộ bài đã tạo vào file.
  + Tải các bộ bài đã lưu từ file.
  + Upload bộ bài lên server thông qua SSH.
 - Cài exe file:
  + Yêu cầu: Không console, có icon (ngoài window explorer, trong taskbar và trong app), đọc file .txt trong folder cards/, card_deck/, chạy main.py đổi thành card_shuffle_creator.exe
  + S1: pip install pyinstaller (nếu chưa cài)
  + S2: vào console thư mục chứa file main.py
  + S3: pyinstaller --noconsole --icon=icon.ico --add-data "cards;cards" --add-data "card_deck;card_deck" main.py

 - Chú ý [Note]
  + 
