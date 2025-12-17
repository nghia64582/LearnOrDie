import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import subprocess
import os


class MachineTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.font = app.font
        self.build_ui()
        self.lasergrbl_process = None

    def build_ui(self):
        row = 0

        tk.Label(self, text="COM Port:", font=self.font).grid(row=row, column=0, sticky="e")
        self.combo_com = ttk.Combobox(self, values=[], width=12)
        self.combo_com.grid(row=row, column=1, sticky="w")

        tk.Button(self, text="Refresh", font=self.font,
                  command=self.refresh_com).grid(row=row, column=2)
        row += 1

        tk.Button(self, text="Connect", font=self.font,
                  command=self.connect_serial).grid(row=row, column=1, pady=5)
        row += 1

        tk.Button(self, text="Laser ON", font=self.font,
                  command=self.laser_on).grid(row=row, column=0)
        tk.Button(self, text="Laser OFF", font=self.font,
                  command=self.laser_off).grid(row=row, column=1)
        row += 1

        tk.Button(self, text="Run GCODE", font=self.font,
                  command=self.run_gcode).grid(row=row, column=1, pady=10)
        row += 1

        self.progress = tk.Label(self, text="Progress: 0%", font=self.font)
        self.progress.grid(row=row, column=1)

        row += 1
        tk.Button(
            self,
            text="Preview GCODE",
            font=self.font,
            command=self.preview_gcode
        ).grid(row=row, column=1, pady=5)


    # ---------------- SERIAL ----------------

    def refresh_com(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.combo_com["values"] = ports
        if ports:
            self.combo_com.current(0)

    def connect_serial(self):
        port = self.combo_com.get()
        try:
            self.app.ser = serial.Serial(port, 115200, timeout=1)
            messagebox.showinfo("Connected", f"Connected to {port}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def laser_on(self):
        if self.app.ser:
            self.app.ser.write(b"M3 S100\n")

    def laser_off(self):
        if self.app.ser:
            self.app.ser.write(b"M5\n")

    def run_gcode(self):
        if not self.app.ser:
            messagebox.showerror("Error", "Not connected.")
            return

        try:
            with open("cut_plan.gcode", "r") as f:
                lines = f.readlines()

            total = len(lines)
            for i, line in enumerate(lines):
                self.app.ser.write(line.encode())
                self.app.ser.flush()
                while not self.app.ser.readline():
                    pass

                percent = int((i + 1) / total * 100)
                self.progress.config(text=f"Progress: {percent}%")
                self.update_idletasks()

            messagebox.showinfo("Done", "GCODE execution completed.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def preview_gcode(self):
        lasergrbl_path = r"C:\Program Files (x86)\LaserGRBL\LaserGRBL.exe"
        gcode_path = r"C:\Users\LaptopKhanhTran\Desktop\Workspace\LearnOrDie\Code\Python\LaserCtrl\cut_plan.gcode"

        if not os.path.exists(lasergrbl_path):
            messagebox.showerror("Error", "LaserGRBL.exe not found.")
            return

        if not os.path.exists(gcode_path):
            messagebox.showerror("Error", "GCODE file not found.")
            return

        try:
            # Nếu chưa từng mở hoặc process đã tắt
            if (
                self.lasergrbl_process is None
                or self.lasergrbl_process.poll() is not None
            ):
                # Mở LaserGRBL (lần đầu, chậm)
                self.lasergrbl_process = subprocess.Popen(
                    [lasergrbl_path, gcode_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("First launch.")
            else:
                # LaserGRBL đang chạy → reuse instance
                subprocess.Popen(
                    [lasergrbl_path, gcode_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("Reused.")

        except Exception as e:
            messagebox.showerror("Error", str(e))
