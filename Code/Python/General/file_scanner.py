import os

MIN_SIZE = 100 * 1024 * 1024  # 100 MB

def scan_folder(path, level=0):
    """
    Trả về tổng kích thước file >= MIN_SIZE và danh sách dòng in.
    """
    total_size = 0
    lines = []
    try:
        with os.scandir(path) as it:
            entries = sorted(it, key=lambda e: e.name.lower())
            for entry in entries:
                if entry.is_file(follow_symlinks=False):
                    size = entry.stat().st_size
                    if size >= MIN_SIZE:
                        total_size += size
                        lines.append('\t' * level + f"{entry.name} ({size / (1024*1024):.2f} MB)")
                elif entry.is_dir(follow_symlinks=False):
                    # Scan folder con
                    sub_size, sub_lines = scan_folder(entry.path, level + 1)
                    if sub_size >= MIN_SIZE:
                        total_size += sub_size
                        lines.append('\t' * level + f"[DIR] {entry.name} - {sub_size / (1024*1024):.2f} MB")
                        lines.extend(sub_lines)
    except PermissionError:
        lines.append('\t' * level + f"[Permission Denied] {path}")
    return total_size, lines

if __name__ == "__main__":
    root_path = input("Nhập đường dẫn folder gốc: ")
    if os.path.exists(root_path):
        total_size, result_lines = scan_folder(root_path)
        # Ghi ra file
        with open("result.txt", "w", encoding="utf-8") as f:
            f.write('\n'.join(result_lines))
        print(f"Hoàn tất! Kết quả đã lưu trong result.txt. Tổng size folder gốc: {total_size / (1024*1024):.2f} MB")
    else:
        print("Đường dẫn không tồn tại!")
