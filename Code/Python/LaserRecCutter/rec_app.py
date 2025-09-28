import tkinter as tk
from tkinter import filedialog, messagebox
import svgwrite
import os

def export_svg():
    try:
        D = float(entry_D.get())
        R = float(entry_R.get())
        C = float(entry_C.get())
        t = float(entry_t.get())
    except ValueError:
        messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ!")
        return

    # Kích thước các mặt
    top_bottom = (D, R)            # mặt trên/dưới
    left_right = (C - 2*t, R)      # mặt trái/phải
    front_back = (D - 2*t, C - 2*t) # mặt trước/sau

    # Chọn thư mục lưu
    folder = filedialog.askdirectory(title="Chọn thư mục lưu SVG")
    if not folder:
        return

    def save_rect(filename, width, height):
        dwg = svgwrite.Drawing(os.path.join(folder, filename),
                               size=(f"{width}mm", f"{height+5}mm"))
        dwg.add(dwg.rect(insert=(0, 5),
                         size=(f"{width}mm", f"{height}mm"),
                         fill="none", stroke="black", stroke_width=0.1))
        dwg.save()

    # Xuất 3 file
    save_rect("top_bottom.svg", *top_bottom)
    save_rect("left_right.svg", *left_right)
    save_rect("front_back.svg", *front_back)

    messagebox.showinfo("Hoàn tất", "Đã xuất 3 file SVG vào thư mục đã chọn.")

# Giao diện
root = tk.Tk()
root.title("Laser Box SVG Generator")

tk.Label(root, text="D (dài, mm):").grid(row=0, column=0, sticky="e")
tk.Label(root, text="R (rộng, mm):").grid(row=1, column=0, sticky="e")
tk.Label(root, text="C (cao, mm):").grid(row=2, column=0, sticky="e")
tk.Label(root, text="t (độ dày, mm):").grid(row=3, column=0, sticky="e")

entry_D = tk.Entry(root); entry_D.grid(row=0, column=1)
entry_R = tk.Entry(root); entry_R.grid(row=1, column=1)
entry_C = tk.Entry(root); entry_C.grid(row=2, column=1)
entry_t = tk.Entry(root); entry_t.grid(row=3, column=1)

tk.Button(root, text="Export SVG", command=export_svg).grid(row=4, column=0, columnspan=2, pady=10)

root.mainloop()
