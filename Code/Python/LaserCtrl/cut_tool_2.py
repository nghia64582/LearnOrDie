import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
from cut_plan_builder import *
from extended_cut_export import *

class CutToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Laser Cutting Tool v2 (GCODE Only)")
        self.font = ("Times New Roman", 11)
        self.ser = None
        self.build_gui()

    def build_gui(self):
        frame = tk.Frame(self.root)
        frame.grid(row=0, column=0, padx=10, pady=10)

        row = 0

        def add(label):
            nonlocal row
            tk.Label(frame, text=label, font=self.font).grid(row=row, column=0, sticky="e")
            row += 1

        # ================= INPUT =================

        add("Stock Length (mm):")
        self.entry_stock_length = tk.Entry(frame, width=40, font=self.font)
        self.entry_stock_length.insert(0, "100")
        self.entry_stock_length.grid(row=row-1, column=1)

        add("Width (mm):")
        self.entry_width = tk.Entry(frame, width=40, font=self.font)
        self.entry_width.insert(0, "10")
        self.entry_width.grid(row=row-1, column=1)

        add("Gap (mm):")
        self.entry_gap = tk.Entry(frame, width=40, font=self.font)
        self.entry_gap.insert(0, "5")
        self.entry_gap.grid(row=row-1, column=1)

        add("Hole Radius (mm):")
        self.entry_hole_radius = tk.Entry(frame, width=40, font=self.font)
        self.entry_hole_radius.insert(0, "1.5")
        self.entry_hole_radius.grid(row=row-1, column=1)

        add("Feedrate:")
        self.entry_feedrate = tk.Entry(frame, width=40, font=self.font)
        self.entry_feedrate.insert(0, "280")
        self.entry_feedrate.grid(row=row-1, column=1)

        add("Power:")
        self.entry_power = tk.Entry(frame, width=40, font=self.font)
        self.entry_power.insert(0, "1000")
        self.entry_power.grid(row=row-1, column=1)

        add("Parts:")
        self.text_parts = tk.Text(frame, width=40, height=8, font=self.font)
        self.text_parts.grid(row=row-1, column=1)

        tk.Label(
            frame,
            text="Format: part_length, is_cut_down, is_cut_up, hole1, hole2 ...",
            font=("Times New Roman", 9), fg="#444"
        ).grid(row=row, column=1, sticky="w")
        row += 1

        # ================= BUTTON =================

        tk.Button(frame, text="Generate GCODE", font=self.font,
                  command=self.on_generate_files).grid(row=row, column=0, pady=8)
        tk.Button(frame, text="Run GCODE", font=self.font,
                  command=self.run_gcode).grid(row=row, column=1)
        row += 1

        # ================= SERIAL =================

        tk.Label(frame, text="COM Port:", font=self.font).grid(row=row, column=0, sticky="e")
        self.combo_com = ttk.Combobox(frame, values=[], font=self.font, width=10)
        self.combo_com.grid(row=row, column=1, sticky="w")
        tk.Button(frame, text="Refresh", font=self.font,
                  command=self.refresh_com).grid(row=row, column=1)
        row += 1

        tk.Button(frame, text="Connect", font=self.font,
                  command=self.connect_serial).grid(row=row, column=1)
        row += 1

        # ================= LASER =================

        tk.Button(frame, text="Laser ON", font=self.font,
                  command=self.laser_on).grid(row=row, column=0)
        tk.Button(frame, text="Laser OFF", font=self.font,
                  command=self.laser_off).grid(row=row, column=1)
        row += 1

        self.progress = tk.Label(frame, text="Progress: 0%", font=self.font)
        self.progress.grid(row=row, column=1)

    # ======================================================

    def on_generate_files(self):
        try:
            stock_length = float(self.entry_stock_length.get())
            width = float(self.entry_width.get())
            gap = float(self.entry_gap.get())
            hole_radius = float(self.entry_hole_radius.get())
            feedrate = float(self.entry_feedrate.get())
            power = float(self.entry_power.get())

            parts_text = self.text_parts.get("1.0", tk.END)
            parts = self.convert_text_to_parts(parts_text)

            cut_plan: CutPlan = build_cut_plan(
                stock_length=stock_length,
                parts=parts,
                width=width,
                gap=gap,
                hole_radius=hole_radius
            )

            export_gcode_extended(
                cut_plan,
                "cut_plan.gcode",
                feedrate=feedrate,
                power=power
            )

            messagebox.showinfo("OK", "GCODE generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= SERIAL =================

    def refresh_com(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.combo_com["values"] = ports
        if ports:
            self.combo_com.current(0)

    def connect_serial(self):
        port = self.combo_com.get()
        self.ser = serial.Serial(port, 115200, timeout=1)
        messagebox.showinfo("Connected", f"Connected to {port}")

    def laser_on(self):
        if self.ser:
            # Bật laser ở S100 (đủ nhìn)
            self.ser.write(b"M3 S100\n")

    def laser_off(self):
        if self.ser:
            self.ser.write(b"M5\n")

    def run_gcode(self):
        if not self.ser:
            messagebox.showerror("Error", "Not connected.")
            return
        try:
            with open("cut_plan.gcode", "r") as f:
                lines = f.readlines()

            total_lines = len(lines)
            for i, line in enumerate(lines):
                self.ser.write(line.encode('utf-8'))
                self.ser.flush()
                # Đợi phản hồi từ máy
                while True:
                    response = self.ser.readline().decode('utf-8').strip()
                    if response:
                        break
                progress_percent = int((i + 1) / total_lines * 100)
                self.progress.config(text=f"Progress: {progress_percent}%")
                self.root.update_idletasks()

            messagebox.showinfo("Done", "GCODE execution completed.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= PARSER =================

    def convert_text_to_parts(self, txt: str) -> List[Part]:
        parts: List[Part] = []
        lines = txt.strip().splitlines()

        for raw_line in lines:
            tokens = [t.strip() for t in raw_line.split(",") if t.strip()]
            length = float(tokens[0])
            is_cut_down = bool(int(tokens[1]))
            is_cut_up = bool(int(tokens[2]))
            hole_centers = [float(t) for t in tokens[3:]]

            parts.append(Part(
                length=length,
                is_cut_down=is_cut_down,
                is_cut_up=is_cut_up,
                hole_centers=hole_centers
            ))
        return parts


if __name__ == "__main__":
    root = tk.Tk()
    app = CutToolApp(root)
    root.mainloop()
