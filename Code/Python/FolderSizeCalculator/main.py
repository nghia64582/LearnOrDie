from time import *
import os

def get_folder_info(folder_path):
    total_size = 0
    file_count = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
                file_count += 1
    return total_size, file_count

def get_size_readable(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024

def list_folder_info(directory):
    total_size, file_count = 0, 0
    with os.scandir(directory) as entries:
        for entry in entries:
            start = time()
            if entry.is_dir():
                size, count = get_folder_info(entry.path)
                total_size += size
                file_count += count
                print(f"{entry.name:>30}|{get_size_readable(size):>10}|{f'{count} file(s)':>15}|{f'{time() - start:.2f} seconds':>15}")
    print(f"\nTotal size of all folders: {get_size_readable(total_size)} | Total files: {file_count}")

if __name__ == "__main__":
    target_directory = input("Enter the directory path: ")
    if os.path.isdir(target_directory):
        list_folder_info(target_directory)
    else:
        print("Invalid directory.")
