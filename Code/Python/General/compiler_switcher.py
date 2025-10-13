import os
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

def get_env(var):
    """Lấy giá trị biến môi trường hiện tại"""
    try:
        result = subprocess.check_output(f'echo %{var}%', shell=True, text=True)
        return result.strip()
    except subprocess.CalledProcessError:
        return ""

def set_env(var, value):
    """Đặt biến môi trường bằng setx"""
    subprocess.run(f'setx {var} "{value}"', shell=True)

def find_java_versions():
    """Dò tất cả đường dẫn java.exe qua lệnh where"""
    try:
        output = subprocess.check_output("where java", shell=True, text=True)
        lines = [l.strip() for l in output.splitlines() if l.strip()]
        # Loại bỏ trùng và lấy thư mục gốc
        java_dirs = sorted(set(os.path.dirname(l) for l in lines))
        return java_dirs
    except subprocess.CalledProcessError:
        return []

def apply_java_home(java_bin_path):
    """Đổi JAVA_HOME và ưu tiên PATH"""
    java_home = os.path.dirname(java_bin_path)

    set_env("JAVA_HOME", java_home)

    # Lấy PATH hiện tại
    current_path = get_env("Path")
    paths = current_path.split(";") if current_path else []
    paths = [p for p in paths if p and java_home.lower() not in p.lower()]  # loại cũ
    new_path = f"{os.path.join(java_home, 'bin')};" + ";".join(paths)
    set_env("Path", new_path)

    messagebox.showinfo("Thành công",
        f"Đã đặt JAVA_HOME = {java_home}\n"
        f"và ưu tiên PATH: {os.path.join(java_home, 'bin')}\n\n"
        f"Vui lòng mở CMD mới để áp dụng.")
    refresh_env_display()

def refresh_env_display():
    """Hiển thị lại thông tin môi trường"""
    java_home = get_env("JAVA_HOME")
    label_current_java.config(text=java_home)
    try:
        version = subprocess.check_output("java -version", shell=True, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        version = e.output
    text_version.delete("1.0", tk.END)
    text_version.insert(tk.END, version)

def refresh_java_list():
    """Cập nhật danh sách Java"""
    for widget in frame_list.winfo_children():
        widget.destroy()

    java_dirs = find_java_versions()
    if not java_dirs:
        tk.Label(frame_list, text="Không tìm thấy bản Java nào trong PATH.", fg="red").pack(anchor="w")
        return

    for java_bin in java_dirs:
        java_home = os.path.dirname(java_bin)
        frame_item = tk.Frame(frame_list, pady=3)
        frame_item.pack(fill="x", anchor="w")
        tk.Label(frame_item, text=java_home, anchor="w").pack(side="left", fill="x", expand=True)
        tk.Button(frame_item, text="Dùng bản này", command=lambda j=java_bin: apply_java_home(j), bg="#4CAF50", fg="white").pack(side="right")

# === GUI ===
root = tk.Tk()
root.title("Java Version Switcher")
root.geometry("900x600")

frame_top = tk.Frame(root, padx=10, pady=10)
frame_top.pack(fill="x")

tk.Label(frame_top, text="JAVA_HOME hiện tại:", font=("Arial", 11, "bold")).pack(anchor="w")
label_current_java = tk.Label(frame_top, text="", fg="blue")
label_current_java.pack(anchor="w", pady=(0,10))

tk.Label(frame_top, text="Các bản Java tìm thấy (qua `where java`):", font=("Arial", 11, "bold")).pack(anchor="w")

canvas = tk.Canvas(root)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)
scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

frame_list = scrollable_frame
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

frame_bottom = tk.Frame(root, padx=10, pady=10)
frame_bottom.pack(fill="x")
tk.Label(frame_bottom, text="Kết quả `java -version`:", font=("Arial", 11, "bold")).pack(anchor="w")
text_version = tk.Text(frame_bottom, height=6, width=100)
text_version.pack(fill="both", expand=True)
tk.Button(frame_bottom, text="Làm mới", command=lambda: [refresh_java_list(), refresh_env_display()]).pack(anchor="e", pady=5)

refresh_java_list()
refresh_env_display()
root.mainloop()
