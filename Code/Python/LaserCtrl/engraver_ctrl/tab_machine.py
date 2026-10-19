import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import subprocess
import os
import time
import threading
import re
import math
from datetime import datetime

# ---- Cấu hình ước lượng thời gian, chỉnh theo máy thực tế của bạn ----
RAPID_RATE_MM_MIN = 3000  # tốc độ di chuyển nhanh (G0), tra trong setting $110/$111 của GRBL
MIN_LINE_TIME = 0.05      # thời gian tối thiểu cho 1 lệnh không di chuyển (giây)

LOG_FILE = "machine.log"


def estimate_gcode_times(lines):
    """
    Ước lượng thời gian thực thi (giây) cho từng dòng gcode, dựa trên khoảng cách
    di chuyển và feedrate hiện hành (modal). Trả về list song song với `lines`.
    """
    times = []
    pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
    feed = 1000.0
    last_motion = None
    token_re = re.compile(r"([A-Za-z])\s*(-?\d+\.?\d*)")

    for raw_line in lines:
        line = raw_line.split(";")[0].split("(")[0].strip()
        if not line:
            times.append(MIN_LINE_TIME)
            continue

        params = {}
        for letter, value in token_re.findall(line):
            params[letter.upper()] = float(value)

        motion = last_motion
        if "G" in params:
            g = int(params["G"])
            if g in (0, 1, 2, 3):
                motion = g
                last_motion = g

        if "F" in params:
            feed = params["F"]

        target = pos.copy()
        for axis in ("X", "Y", "Z"):
            if axis in params:
                target[axis] = params[axis]

        dx = target["X"] - pos["X"]
        dy = target["Y"] - pos["Y"]
        dz = target["Z"] - pos["Z"]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        pos = target

        if motion is not None and distance > 0:
            rate = RAPID_RATE_MM_MIN if motion == 0 else max(feed, 1)
            t = (distance / rate) * 60.0  # phút -> giây
            times.append(max(t, MIN_LINE_TIME))
        else:
            times.append(MIN_LINE_TIME)

    return times


class MachineTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.font = app.font
        self.lasergrbl_process = None
        self.is_running = False
        self.line_times = []
        self.total_time = 1.0
        self.stop_event = threading.Event()
        self.serial_lock = threading.Lock()
        self.build_ui()

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

        self.btn_run = tk.Button(self, text="Run GCODE", font=self.font,
                                  command=self.run_gcode)
        self.btn_run.grid(row=row, column=0, pady=10)

        self.btn_stop = tk.Button(self, text="STOP", font=self.font, fg="white", bg="red",
                                   command=self.stop_gcode, state="disabled")
        self.btn_stop.grid(row=row, column=1, pady=10)
        row += 1

        self.progress_bar = ttk.Progressbar(self, orient="horizontal",
                                             length=200, mode="determinate")
        self.progress_bar.grid(row=row, column=1)
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
        row += 1

        # ---- Log box, thay cho print() ----
        tk.Label(self, text="Log:", font=self.font).grid(row=row, column=0, sticky="nw")
        self.log_text = scrolledtext.ScrolledText(self, width=60, height=10, state="disabled",
                                                    font=("Consolas", 9))
        self.log_text.grid(row=row, column=1, columnspan=2, sticky="w", pady=5)

    # ---------------- LOG ----------------

    def log(self, message):
        """
        Thread-safe logging: ghi ra UI (Text widget) và file, thay cho print().
        Có thể gọi từ bất kỳ thread nào.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"

        # Ghi ra file log để xem lại sau, kể cả khi không mở terminal
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

        # Cập nhật UI phải chạy trên main thread
        self.after(0, self._append_log_ui, line)

    def _append_log_ui(self, line):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

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
            time.sleep(2)
            self.app.ser.reset_input_buffer()
            self.app.ser.reset_output_buffer()
            self.log(f"Connected to {port}")
            messagebox.showinfo("Connected", f"Connected to {port}")
        except Exception as e:
            self.log(f"Connect error: {e}")
            messagebox.showerror("Error", str(e))
    
    def laser_on(self):
        if not self.app.ser:
            messagebox.showerror("Error", "Not connected.")
            return
        threading.Thread(target=self._send_laser_sequence,
                        args=(["M3 S30.0000\n", "G1 F1000\n"], "Laser ON"),
                        daemon=True).start()

    def laser_off(self):
        if not self.app.ser:
            messagebox.showerror("Error", "Not connected.")
            return
        threading.Thread(target=self._send_laser_sequence,
                        args=(["M5 S0\n", "G0\n"], "Laser OFF"),
                        daemon=True).start()

    def _send_laser_sequence(self, gcode_lines, label):
        with self.serial_lock:
            self.app.ser.reset_input_buffer()

        for gcode_line in gcode_lines:
            ok = self._send_line_and_wait_ok(gcode_line, timeout=5)
            if not ok:
                self.log(f"{label} FAILED at line '{gcode_line.strip()}' "
                        f"(machine may be in Alarm state, try unlock $X)")
                self.after(0, lambda: messagebox.showwarning(
                    "Warning",
                    f"{label} failed - GRBL không phản hồi 'ok'.\n"
                    "Có thể máy đang ở trạng thái Alarm, hãy gửi $X để unlock."
                ))
                return

        self.log(label)

    def _send_line_and_wait_ok(self, line, timeout=30):
        with self.serial_lock:
            self.app.ser.write(line.encode())
            self.app.ser.flush()

        start = time.time()
        while True:
            if self.stop_event.is_set():
                self.log(f"Aborted while waiting response for: {line.strip()}")
                return False

            if time.time() - start > timeout:
                self.log(f"Timeout waiting response for: {line.strip()}")
                return False

            resp = self.app.ser.readline().decode(errors="ignore").strip().lower()

            if not resp:
                continue
            if resp == "ok":
                return True
            if resp.startswith("error"):
                self.log(f"GRBL error for line '{line.strip()}': {resp}")
                return False
            self.log(f"Ignored response: {resp}")

    # ---------------- RUN / STOP ----------------

    def run_gcode(self):
        if not self.app.ser:
            messagebox.showerror("Error", "Not connected.")
            return

        if self.is_running:
            messagebox.showwarning("Warning", "GCODE is already running.")
            return

        try:
            with open("cut_plan.gcode", "r") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            lines.append("M5")          # tắt laser trước
            lines.append("G0 X0 Y0")    # rồi mới di chuyển về vị trí gốc
        except Exception as e:
            self.log(f"File error: {e}")
            messagebox.showerror("Error", str(e))
            return

        self.line_times = estimate_gcode_times(lines)
        self.total_time = sum(self.line_times) or 1.0

        self.stop_event.clear()
        self.is_running = True
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")

        with self.serial_lock:
            self.app.ser.reset_input_buffer()

        self.log(f"Starting GCODE run ({len(lines)} lines)")
        thread = threading.Thread(target=self._run_gcode_worker, args=(lines,), daemon=True)
        thread.start()

    def stop_gcode(self):
        if not self.is_running:
            return

        self.log("STOP requested by user")

        # Báo cho worker thread ngừng gửi dòng tiếp theo
        self.stop_event.set()

        if self.app.ser:
            try:
                with self.serial_lock:
                    # Feed hold: dừng di chuyển ngay lập tức (lệnh realtime, không cần newline)
                    self.app.ser.write(b'!')
                    self.app.ser.flush()
                time.sleep(0.1)

                with self.serial_lock:
                    # Tắt laser ngay
                    self.app.ser.write(b"M5\n")
                    self.app.ser.flush()
                time.sleep(0.1)

                with self.serial_lock:
                    # Soft reset: xoá sạch phần gcode còn lại trong buffer của GRBL,
                    # tránh việc máy chạy tiếp phần cũ khi resume sau này
                    self.app.ser.write(b'\x18')
                    self.app.ser.flush()

                self.log("Sent feed-hold + M5 + soft-reset. "
                         "Machine may be in Alarm state, unlock ($X) before running again.")
            except Exception as e:
                self.log(f"Error while stopping: {e}")

        self.btn_stop.config(state="disabled")

    def _run_gcode_worker(self, lines):
        elapsed_time = 0.0
        had_error = False
        stopped = False

        for i, line in enumerate(lines):
            if self.stop_event.is_set():
                stopped = True
                break

            gcode_line = line + "\n"
            ok = self._send_line_and_wait_ok(gcode_line)

            if not ok:
                if self.stop_event.is_set():
                    stopped = True
                else:
                    had_error = True
                break

            elapsed_time += self.line_times[i]
            percent = min(int(elapsed_time / self.total_time * 100), 100)
            self.after(0, self._update_progress, percent)

        # Nếu không phải do Stop chủ động (đã tự gửi M5/reset trong stop_gcode),
        # vẫn đảm bảo tắt laser trong trường hợp lỗi thường hoặc chạy xong bình thường
        if not stopped:
            self._send_line_and_wait_ok("M5\n")

        self.after(0, self._on_run_finished, had_error, stopped)

    def _update_progress(self, percent):
        self.progress.config(text=f"Progress: {percent}%")
        self.progress_bar["value"] = percent

    def _on_run_finished(self, had_error, stopped):
        self.is_running = False
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")

        if stopped:
            self.log("GCODE run stopped by user.")
            messagebox.showinfo("Stopped", "GCODE execution stopped by user. Laser is off.")
        elif had_error:
            self.log("GCODE run stopped due to error.")
            messagebox.showerror("Error", "GCODE execution stopped due to an error. Laser has been turned off.")
        else:
            self.log("GCODE run completed successfully.")
            messagebox.showinfo("Done", "GCODE execution completed.")

    # ---------------- PREVIEW ----------------

    def preview_gcode(self):
        lasergrbl_path = r"C:\Program Files (x86)\LaserGRBL\LaserGRBL.exe"
        gcode_path = r"C:\Users\LaptopKhanhTran\Desktop\Workspace\LearnOrDie\Code\Python\LaserCtrl\cut_plan.gcode"

        if not os.path.exists(lasergrbl_path):
            self.log("LaserGRBL.exe not found.")
            messagebox.showerror("Error", "LaserGRBL.exe not found.")
            return

        if not os.path.exists(gcode_path):
            self.log("GCODE file not found.")
            messagebox.showerror("Error", "GCODE file not found.")
            return

        try:
            if (
                self.lasergrbl_process is None
                or self.lasergrbl_process.poll() is not None
            ):
                self.lasergrbl_process = subprocess.Popen(
                    [lasergrbl_path, gcode_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.log("LaserGRBL: first launch.")
            else:
                subprocess.Popen(
                    [lasergrbl_path, gcode_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.log("LaserGRBL: reused instance.")

        except Exception as e:
            self.log(f"Preview error: {e}")
            messagebox.showerror("Error", str(e))