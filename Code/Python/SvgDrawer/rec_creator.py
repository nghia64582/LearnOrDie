import tkinter as tk
from tkinter import filedialog, messagebox
import svgwrite
import os

def export_svg():
    try:
        D = float(entry_D.get())
        R = float(entry_R.get())
    except ValueError:
        messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ!")
        return

    # Chọn thư mục lưu
    folder = filedialog.askdirectory(title="Chọn thư mục lưu SVG")
    if not folder:
        return

    filename = os.path.join(folder, f"rect_{int(D)}x{int(R)}.svg")

    # Vẽ SVG
    dwg = svgwrite.Drawing(filename, size=(f"{D}mm", f"{R+5}mm"))
    # Đảo hệ trục Y để tương thích LaserGRBL
    canvas_height = R + 5
    y_svg = canvas_height - R - 5

    dwg.add(dwg.rect(insert=(0, y_svg),
                    size=(f"{D}mm", f"{R}mm"),
                    fill="none", stroke="black", stroke_width=0.1))
    dwg.save()

    messagebox.showinfo("Hoàn tất", f"Đã tạo file:\n{filename}")

# Giao diện Tkinter
root = tk.Tk()
root.title("Rectangle SVG Generator")

tk.Label(root, text="D (dài, mm):").grid(row=0, column=0, sticky="e")
tk.Label(root, text="R (rộng, mm):").grid(row=1, column=0, sticky="e")

entry_D = tk.Entry(root); entry_D.grid(row=0, column=1)
entry_R = tk.Entry(root); entry_R.grid(row=1, column=1)

tk.Button(root, text="Export SVG", command=export_svg).grid(row=2, column=0, columnspan=2, pady=10)

root.mainloop()
