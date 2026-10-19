import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import os
import time
import threading
import re
import math
from datetime import datetime

from engraver_ctrl.tab_simulate import TabSimulate

# ---- Cấu hình ước lượng thời gian, chỉnh theo máy thực tế của bạn ----
RAPID_RATE_MM_MIN = 3000  # tốc độ di chuyển nhanh (G0), tra trong setting $110/$111 của GRBL
MIN_LINE_TIME = 0.05      # thời gian tối thiểu cho 1 lệnh không di chuyển (giây)

LOG_FILE = "machine.log"

# File gcode de preview: engraver_ctrl/cut_plan.gcode, tinh theo vi tri
# file nguon nay (khong phu thuoc thu muc dang chay, chay duoc ca
# Windows/Linux vi dung os.path.join thay vi dau "\\" cung)
PREVIEW_GCODE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "cut_plan.gcode"
)

# Buoc jog mac dinh (mm) va cac lua chon nhanh
JOG_STEP_DEFAULT = "1"
JOG_STEP_CHOICES = ["0.1", "1", "5", "10"]

# Phim -> (truc, huong). Quy uoc: Up = +Y, Down = -Y,
# Left = -X, Right = +X
JOG_KEYS = {
    "w": ("Y", 1),
    "s": ("Y", -1),
    "a": ("X", -1),
    "d": ("X", 1),
}


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


class GcodePreviewRenderer:
    """
    Ve preview gcode len 1 canvas, dung lai cac ham parse/ve cua
    TabSimulate (khong copy code). Cac ham do chi can cac thuoc tinh
    canvas, steps, current_step, min/max_x/y, scale, offset_x/y.
    """

    parse_gcode = TabSimulate.parse_gcode
    extract_axis = TabSimulate.extract_axis
    calculate_bounds = TabSimulate.calculate_bounds
    recompute_transform = TabSimulate.recompute_transform
    transform = TabSimulate.transform
    choose_grid_step = TabSimulate.choose_grid_step
    draw_grid = TabSimulate.draw_grid
    draw = TabSimulate.draw

    def __init__(self, canvas):
        self.canvas = canvas
        self.steps = []
        self.current_step = 0
        self.min_x = 0
        self.max_x = 100
        self.min_y = 0
        self.max_y = 100
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

    def load(self, content):
        # Ve toan bo file (current_step = so buoc)
        self.steps = self.parse_gcode(content)
        self.current_step = len(self.steps)
        self.calculate_bounds()
        self.redraw()

    def redraw(self):
        self.recompute_transform()
        self.draw()


class MachineTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.font = app.font
        self.is_running = False
        self.line_times = []
        self.total_time = 1.0
        self.stop_event = threading.Event()
        self.serial_lock = threading.Lock()
        # Chi cho 1 lenh jog chay mot luc, tranh 2 chuoi G91/G0/G90
        # xen ke nhau lam may ket o che do toa do tuong doi
        self.jog_lock = threading.Lock()
        self.build_ui()
        self.bind_jog_keys()

        # Preview file gcode ngay khi mo tab
        self.after_idle(self.preview_gcode)

    def build_ui(self):
        # Ben trai: ket noi + dieu khien + jog + log (khong gian),
        # ben phai: canvas preview gian theo cua so
        self.columnconfigure(0, weight=0)
        # minsize: preview luon co toi thieu 300px, khong bi cot ben
        # trai (log rong) ep mat khi cua so hep
        self.columnconfigure(1, weight=1, minsize=300)
        self.rowconfigure(0, weight=1)

        controls = tk.Frame(self)
        controls.grid(row=0, column=0, sticky="nw", padx=5, pady=5)

        row = 0

        tk.Label(controls, text="COM Port:", font=self.font).grid(row=row, column=0, sticky="e")
        self.combo_com = ttk.Combobox(controls, values=[], width=12)
        self.combo_com.grid(row=row, column=1, sticky="w")

        tk.Button(controls, text="Refresh", font=self.font,
                  command=self.refresh_com).grid(row=row, column=2)
        row += 1

        tk.Button(controls, text="Connect", font=self.font,
                  command=self.connect_serial).grid(row=row, column=1, pady=5)
        row += 1

        tk.Button(controls, text="Laser ON", font=self.font,
                  command=self.laser_on).grid(row=row, column=0)
        tk.Button(controls, text="Laser OFF", font=self.font,
                  command=self.laser_off).grid(row=row, column=1)
        row += 1

        self.btn_run = tk.Button(controls, text="Run GCODE", font=self.font,
                                  command=self.run_gcode)
        self.btn_run.grid(row=row, column=0, pady=10)

        self.btn_stop = tk.Button(controls, text="STOP", font=self.font, fg="white", bg="red",
                                   command=self.stop_gcode, state="disabled")
        self.btn_stop.grid(row=row, column=1, pady=10)
        row += 1

        self.progress_bar = ttk.Progressbar(controls, orient="horizontal",
                                             length=200, mode="determinate")
        self.progress_bar.grid(row=row, column=1)
        row += 1

        self.progress = tk.Label(controls, text="Progress: 0%", font=self.font)
        self.progress.grid(row=row, column=1)
        row += 1

        # ---- Jog: di chuyen nhanh dau laser bang G0 (phim W/A/S/D) ----
        jog_frame = tk.LabelFrame(controls, text="Jog (W/A/S/D)", font=self.font)
        jog_frame.grid(row=row, column=0, columnspan=3, pady=5)

        tk.Label(jog_frame, text="Step (mm):", font=self.font).grid(row=0, column=0, sticky="e")
        self.jog_step_var = tk.StringVar(value=JOG_STEP_DEFAULT)
        self.combo_jog_step = ttk.Combobox(jog_frame, textvariable=self.jog_step_var,
                                           values=JOG_STEP_CHOICES, width=6)
        self.combo_jog_step.grid(row=0, column=1, columnspan=2, sticky="w", pady=(0, 5))

        tk.Button(jog_frame, text="Up (W)", font=self.font, width=8,
                  command=lambda: self.jog("Y", 1)).grid(row=1, column=1)
        tk.Button(jog_frame, text="Left (A)", font=self.font, width=8,
                  command=lambda: self.jog("X", -1)).grid(row=2, column=0)
        tk.Button(jog_frame, text="Right (D)", font=self.font, width=8,
                  command=lambda: self.jog("X", 1)).grid(row=2, column=2)
        tk.Button(jog_frame, text="Down (S)", font=self.font, width=8,
                  command=lambda: self.jog("Y", -1)).grid(row=3, column=1)
        row += 1

        # ---- Log box, thay cho print() ----
        tk.Label(controls, text="Log:", font=self.font).grid(row=row, column=0, sticky="nw")
        self.log_text = scrolledtext.ScrolledText(controls, width=60, height=10, state="disabled",
                                                    font=("Consolas", 9))
        self.log_text.grid(row=row, column=1, columnspan=2, sticky="w", pady=5)

        # ---- Preview gcode (ben phai) ----
        preview_frame = tk.Frame(self)
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)

        header = tk.Frame(preview_frame)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        # width=1: label khong doi requested width theo do dai text
        # -> khong lam cot preview bi co gian (giat) moi lan doi text
        self.preview_info = tk.Label(header, text="Preview: -", font=self.font,
                                     anchor="w", width=1)
        self.preview_info.grid(row=0, column=0, sticky="ew")

        tk.Button(header, text="Reload preview", font=self.font,
                  command=self.preview_gcode).grid(row=0, column=1, padx=(5, 0))

        self.preview_canvas = tk.Canvas(preview_frame, background="white",
                                        highlightthickness=0)
        self.preview_canvas.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        self.preview = GcodePreviewRenderer(self.preview_canvas)
        self.preview_canvas.bind("<Configure>", self.on_preview_resize)

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
        """
        Doc engraver_ctrl/cut_plan.gcode va ve len canvas ben phai.
        Thieu file / loi doc thi bao tren canvas + log, khong crash.
        """
        path = PREVIEW_GCODE_PATH

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.preview.steps = []
            self.preview.current_step = 0
            self.preview_info.config(text=f"Preview: cannot read {path}")
            self._show_preview_message(f"Cannot read G-code file:\n{path}\n\n{e}")
            self.log(f"Preview error: {e}")
            return

        self.preview.load(content)

        if not self.preview.steps:
            self._show_preview_message(f"No G0/G1 moves in:\n{path}")

        self.preview_info.config(
            text=f"Preview: {path} ({len(self.preview.steps)} moves)"
        )
        self.log(f"Preview loaded: {path} ({len(self.preview.steps)} moves)")

    def on_preview_resize(self, event):
        if self.preview.steps:
            self.preview.redraw()
        else:
            self._redraw_preview_message()

    def _show_preview_message(self, message):
        self._preview_message = message
        self._redraw_preview_message()

    def _redraw_preview_message(self):
        message = getattr(self, "_preview_message", "")
        canvas = self.preview_canvas
        canvas.delete("all")
        if message:
            canvas.create_text(
                canvas.winfo_width() / 2,
                canvas.winfo_height() / 2,
                text=message,
                fill="red",
                justify="center"
            )

    # ---------------- JOG ----------------

    def bind_jog_keys(self):
        # Bind tren cua so goc (add="+" de khong de binding khac),
        # handler tu kiem tra tab dang mo va widget dang focus
        root = self.winfo_toplevel()
        for key in JOG_KEYS:
            for k in (key, key.upper()):
                root.bind(f"<KeyPress-{k}>", self.on_jog_key, add="+")

    def on_jog_key(self, event):
        # Chi xu ly khi tab Machine dang duoc chon
        try:
            if self.master.select() != str(self):
                return
        except Exception:
            return

        # Bo qua khi dang go chu trong o nhap (Entry/Combobox/Text...)
        try:
            focus = self.focus_get()
        except Exception:
            focus = None
        if isinstance(focus, (tk.Entry, tk.Text, tk.Spinbox, ttk.Entry, ttk.Spinbox)):
            return

        axis, direction = JOG_KEYS[event.keysym.lower()]
        self.jog(axis, direction)
        return "break"

    def build_jog_lines(self, axis, direction, step):
        # Jog tuong doi: G91 -> G0 truc +/-buoc -> G90 (tra ve tuyet doi,
        # file gcode cua tool dung toa do tuyet doi G90)
        return [
            "G91\n",
            f"G0 {axis}{direction * step:.3f}\n",
            "G90\n",
        ]

    def jog(self, axis, direction):
        if not self.app.ser:
            self.log("Jog ignored: not connected.")
            messagebox.showerror("Error", "Not connected.")
            return

        if self.is_running:
            self.log("Jog ignored: GCODE is running.")
            return

        try:
            step = float(self.jog_step_var.get())
            if step <= 0:
                raise ValueError
        except ValueError:
            self.log(f"Jog ignored: invalid step '{self.jog_step_var.get()}'.")
            messagebox.showerror("Error", "Jog step must be a positive number (mm).")
            return

        # Dang co lenh jog chua xong -> bo qua (vd. giu phim auto-repeat)
        if not self.jog_lock.acquire(blocking=False):
            self.log("Jog busy, ignored.")
            return

        lines = self.build_jog_lines(axis, direction, step)
        threading.Thread(target=self._jog_worker, args=(lines,), daemon=True).start()

    def _jog_worker(self, lines):
        label = f"Jog {lines[1].strip()}"
        try:
            with self.serial_lock:
                self.app.ser.reset_input_buffer()

            # G91
            if not self._send_line_and_wait_ok(lines[0], timeout=5):
                self.log(f"{label} FAILED at '{lines[0].strip()}' "
                         f"(machine may be in Alarm state, try unlock $X)")
                return

            try:
                ok = self._send_line_and_wait_ok(lines[1], timeout=30)
            finally:
                # Luon co gang tra ve G90 sau khi da gui G91, ke ca khi
                # G0 loi, de lan Run GCODE sau khong chay theo toa do
                # tuong doi
                if not self._send_line_and_wait_ok(lines[2], timeout=5):
                    self.log("WARNING: failed to restore G90 after jog, send G90 manually.")

            if ok:
                self.log(label)
            else:
                self.log(f"{label} FAILED (machine may be in Alarm state, try unlock $X)")
        except Exception as e:
            self.log(f"Jog error: {e}")
        finally:
            self.jog_lock.release()
