import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import math

# ====== Load sticks từ file txt ======
# Format file: name,length,width,cost
def load_sticks(file_path="sticks.txt"):
    sticks = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) >= 4:
                    sticks.append({
                        "name": parts[0].strip(),
                        "length": float(parts[1]),
                        "width": float(parts[2]),
                        "cost": int(parts[3])
                    })
    except FileNotFoundError:
        messagebox.showerror("Lỗi", f"Không tìm thấy file {file_path}")
    return sticks

# ====== Hàm tính toán ======
def calc_num_sticks(stick_len, stick_wid, rect_w, rect_h):
    """
    stick_len: chiều dài que
    stick_wid: chiều rộng que
    rect_w, rect_h: kích thước hình chữ nhật cần cắt
    return: số que cần hoặc None nếu que không đủ dài
    """
    # Trừ phần bo tròn (5mm mỗi đầu -> 10mm)
    usable_len = stick_len - 10
    if usable_len < rect_w:  # cạnh dài hình phải <= usable_len
        return None
    num_sticks = math.ceil(rect_h / stick_wid)
    return num_sticks

# ====== Xuất SVG ======
def save_svg(rect_w, rect_h, file_path):
    svg_content = f"""<?xml version="1.0" standalone="no"?>
<svg width="{rect_w}mm" height="{rect_h + 5}mm" viewBox="0 0 {rect_w} {rect_h + 5}"
     xmlns="http://www.w3.org/2000/svg" version="1.1">
  <!-- Đường thẳng nhỏ để căn gốc -->
  <line x1="0" y1="0" x2="0" y2="0.1" stroke="black" stroke-width="0.1"/>
  <!-- Hình chữ nhật -->
  <rect x="0" y="0" width="{rect_w}" height="{rect_h}" fill="none" stroke="black" stroke-width="0.2"/>
</svg>
"""
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(svg_content)

# ====== GUI ======
class StickApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ghép que kem & Xuất SVG")
        self.sticks = load_sticks()

        frm = tk.Frame(root)
        frm.pack(padx=10, pady=10)

        tk.Label(frm, text="Chiều dài (mm):").grid(row=0, column=0)
        tk.Label(frm, text="Chiều rộng (mm):").grid(row=1, column=0)

        self.entry_len = tk.Entry(frm)
        self.entry_wid = tk.Entry(frm)
        self.entry_len.grid(row=0, column=1)
        self.entry_wid.grid(row=1, column=1)

        tk.Button(frm, text="Tính toán", command=self.calculate).grid(row=2, column=0, pady=5)
        tk.Button(frm, text="Xuất SVG", command=self.export_svg).grid(row=2, column=1, pady=5)

        # Table
        self.tree = ttk.Treeview(root, columns=("que","orientation","num","cost","total"), show="headings")
        self.tree.heading("que", text="Loại que")
        self.tree.heading("orientation", text="Hướng (WxH)")
        self.tree.heading("num", text="Số que")
        self.tree.heading("cost", text="Chi phí/que")
        self.tree.heading("total", text="Tổng chi phí")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def calculate(self):
        rect_w = float(self.entry_len.get())
        rect_h = float(self.entry_wid.get())

        # Clear bảng
        for row in self.tree.get_children():
            self.tree.delete(row)

        for stick in self.sticks:
            # Trường hợp đứng WxH
            num1 = calc_num_sticks(stick["length"], stick["width"], rect_w, rect_h)
            if num1:
                total1 = num1 * stick["cost"]
                self.tree.insert("", "end", values=(stick["name"], f"{rect_w}x{rect_h}", num1, stick["cost"], total1))

            # Trường hợp xoay HxW
            num2 = calc_num_sticks(stick["length"], stick["width"], rect_h, rect_w)
            if num2:
                total2 = num2 * stick["cost"]
                self.tree.insert("", "end", values=(stick["name"], f"{rect_h}x{rect_w}", num2, stick["cost"], total2))

    def export_svg(self):
        try:
            rect_w = float(self.entry_len.get())
            rect_h = float(self.entry_wid.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".svg",
                                                 filetypes=[("SVG files","*.svg")],
                                                 initialfile=f"rec_{int(rect_w)}_{int(rect_h)}.svg")
        if file_path:
            save_svg(rect_w, rect_h, file_path)
            messagebox.showinfo("Thành công", f"Đã lưu {file_path}")

# ====== Run ======
if __name__ == "__main__":
    root = tk.Tk()
    app = StickApp(root)
    root.mainloop()
