import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
try:
    import serial
    from serial.tools import list_ports as serial_list_ports
except ImportError:  # optional when pyserial is not installed
    serial = None
    serial_list_ports = None
import os
import time
import threading
import re
import math
from datetime import datetime

from engraver_ctrl.gcode_arcs import arc_length
from engraver_ctrl.tab_simulate import TabSimulate
from engraver_ctrl.paths import CUT_PLAN_GCODE_PATH
from common.ui import ui_font, mono_font, make_button, SIZE_SM

# ---- Cấu hình ước lượng thời gian, chỉnh theo máy thực tế của bạn ----
RAPID_RATE_MM_MIN = 3000  # tốc độ di chuyển nhanh (G0), tra trong setting $110/$111 của GRBL
MIN_LINE_TIME = 0.05      # thời gian tối thiểu cho 1 lệnh không di chuyển (giây)

LOG_FILE = "machine.log"

# File gcode de preview: engraver_ctrl/cut_plan.gcode (xem paths.py),
# cung file voi Run GCODE va cac tab generate
PREVIEW_GCODE_PATH = CUT_PLAN_GCODE_PATH

# Baud rate used for every GRBL connection (shown in the status label).
BAUD_RATE = 115200

# Connection status colours (tk.Label fg). Green = up, red = down / error,
# orange = Hold (paused, not yet usable).
STATUS_CONNECTED_FG = "green"
STATUS_DISCONNECTED_FG = "red"
STATUS_HOLD_FG = "orange"

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

# Set the current position as G54 work origin (0, 0). G10 L20 writes a
# persistent offset that survives a soft reset (0x18 / STOP). G92 is
# cleared on some GRBL 1.1 builds, so it would be lost after STOP.
SET_ZERO_CMD = "G10 L20 P1 X0 Y0\n"


def estimate_gcode_times(lines):
    """
    Ước lượng thời gian thực thi (giây) cho từng dòng gcode, dựa trên khoảng cách
    di chuyển và feedrate hiện hành (modal). G2/G3 dùng độ dài cung (I/J hoặc R), không dùng dây cung. Trả về list song song với `lines`.
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

        # G2/G3: use the arc length, not the chord (a cap or hole
        # would otherwise be badly underestimated).
        if motion in (2, 3):
            try:
                xy_len = arc_length(
                    pos["X"], pos["Y"],
                    target["X"], target["Y"],
                    clockwise=(motion == 2),
                    i=params.get("I"),
                    j=params.get("J"),
                    r=params.get("R"),
                )
                distance = math.hypot(xy_len, dz)
            except ValueError:
                pass

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
        self.font = getattr(app, "font", None) or ui_font(SIZE_SM)
        self.is_running = False
        self.line_times = []
        self.total_time = 1.0
        self.stop_event = threading.Event()
        self.serial_lock = threading.Lock()
        # Chi cho 1 lenh jog chay mot luc, tranh 2 chuoi G91/G0/G90
        # xen ke nhau lam may ket o che do toa do tuong doi
        self.jog_lock = threading.Lock()
        self._connected_port = None
        self._connected_baud = None
        self._machine_state = None
        self._run_thread = None
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

        make_button(controls, "Refresh", command=self.refresh_com).grid(row=row, column=2)
        row += 1

        self.btn_connect = make_button(controls, "Connect", command=self.connect_serial)
        self.btn_connect.grid(row=row, column=1, pady=5)
        self.btn_disconnect = make_button(
            controls, "Disconnect", command=self.disconnect_serial, state="disabled"
        )
        self.btn_disconnect.grid(row=row, column=2, pady=5)
        row += 1

        self.connection_status = tk.Label(
            controls,
            text="Disconnected",
            font=self.font,
            fg=STATUS_DISCONNECTED_FG,
            anchor="w",
        )
        self.connection_status.grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        make_button(controls, "Laser ON", command=self.laser_on).grid(row=row, column=0)
        make_button(controls, "Laser OFF", command=self.laser_off).grid(row=row, column=1)
        self.btn_unlock = make_button(controls, "Unlock", command=self.unlock_machine, state="disabled")
        self.btn_unlock.grid(row=row, column=2)
        row += 1

        self.btn_run = make_button(controls, "Run GCODE", command=self.run_gcode)
        self.btn_run.grid(row=row, column=0, pady=10)

        self.btn_stop = make_button(controls, "STOP", command=self.stop_gcode, state="disabled")
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

        make_button(jog_frame, "Up (W)", command=lambda: self.jog("Y", 1), width=8).grid(row=1, column=1)
        make_button(jog_frame, "Left (A)", command=lambda: self.jog("X", -1), width=8).grid(row=2, column=0)
        make_button(jog_frame, "Right (D)", command=lambda: self.jog("X", 1), width=8).grid(row=2, column=2)
        make_button(jog_frame, "Down (S)", command=lambda: self.jog("Y", -1), width=8).grid(row=3, column=1)
        self.btn_set_zero = make_button(
            jog_frame, "Set Zero", command=self.set_work_zero,
            width=10, state="disabled",
        )
        self.btn_set_zero.grid(row=4, column=0, columnspan=3, pady=(6, 2))
        row += 1

        # ---- Log box, thay cho print() ----
        tk.Label(controls, text="Log:", font=self.font).grid(row=row, column=0, sticky="nw")
        self.log_text = scrolledtext.ScrolledText(controls, width=60, height=10, state="disabled",
                                                    font=mono_font(SIZE_SM))
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

        make_button(header, "Reload preview", command=self.preview_gcode).grid(row=0, column=1, padx=(5, 0))

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
        if serial_list_ports is None:
            self.combo_com["values"] = []
            self.log("pyserial not installed; COM list unavailable.")
            return
        ports = [p.device for p in serial_list_ports.comports()]
        self.combo_com["values"] = ports
        if ports:
            self.combo_com.current(0)

    def _is_connected(self):
        ser = getattr(self.app, "ser", None)
        if ser is None:
            return False
        return bool(getattr(ser, "is_open", True))

    def _serial_exc_types(self):
        types = [OSError]
        if serial is not None:
            exc = getattr(serial, "SerialException", None)
            if isinstance(exc, type) and exc not in types:
                types.append(exc)
        return tuple(types)

    def _set_connection_status(self, text, connected=False, *, connecting=False, fg=None):
        """Update the status label and Connect/Disconnect button states.

        Safe to call from a worker thread (marshals onto the Tk thread).
        Colour is set with tk.Label fg: green when connected, red otherwise,
        or an explicit fg (orange Hold, red Alarm).
        """
        def apply():
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            color = fg if fg is not None else (
                STATUS_CONNECTED_FG if connected else STATUS_DISCONNECTED_FG
            )
            try:
                self.connection_status.config(text=text, fg=color)
            except Exception:
                pass
            try:
                unlock = "disabled" if connecting or not connected else "normal"
                if connecting:
                    self.btn_connect.config(state="disabled")
                    self.btn_disconnect.config(state="disabled")
                elif connected:
                    self.btn_connect.config(state="disabled")
                    self.btn_disconnect.config(state="normal")
                else:
                    self.btn_connect.config(state="normal")
                    self.btn_disconnect.config(state="disabled")
                if getattr(self, "btn_unlock", None) is not None:
                    self.btn_unlock.config(state=unlock)
                self._sync_set_zero_button(
                    connected=connected, connecting=connecting
                )
            except Exception:
                pass

        try:
            if threading.current_thread() is threading.main_thread():
                apply()
            else:
                self.after(0, apply)
        except Exception:
            try:
                self.after(0, apply)
            except Exception:
                pass

    def _reset_run_buttons(self):
        def apply():
            try:
                if not self.winfo_exists():
                    return
                self.btn_run.config(state="normal")
                self.btn_stop.config(state="disabled")
                self._sync_set_zero_button()
            except Exception:
                pass

        try:
            if threading.current_thread() is threading.main_thread():
                apply()
            else:
                self.after(0, apply)
        except Exception:
            try:
                self.after(0, apply)
            except Exception:
                pass

    def _set_zero_allowed(self, connected=None, connecting=False):
        """True when Set Zero is safe: connected, Idle, and not running."""
        if connecting:
            return False
        if connected is None:
            connected = self._is_connected()
        if not connected or self.is_running:
            return False
        key = (self._machine_state or "Idle").split(":")[0].strip().lower()
        return key in ("", "idle")

    def _sync_set_zero_button(self, connected=None, connecting=False):
        btn = getattr(self, "btn_set_zero", None)
        if btn is None:
            return
        try:
            allowed = self._set_zero_allowed(
                connected=connected, connecting=connecting
            )
            btn.config(state="normal" if allowed else "disabled")
        except Exception:
            pass

    def _close_serial_port(self):
        """Close app.ser if present and clear the reference. Caller holds serial_lock if needed."""
        ser = getattr(self.app, "ser", None)
        self.app.ser = None
        self._connected_port = None
        self._connected_baud = None
        if ser is None:
            return
        try:
            ser.close()
        except Exception:
            pass

    def _handle_connection_lost(self, exc, context="Connection lost"):
        """Close the port after a read/write failure and show a red error status."""
        self.stop_event.set()
        self.is_running = False
        acquired = False
        try:
            acquired = self.serial_lock.acquire(timeout=1.0)
        except Exception:
            acquired = False
        try:
            self._close_serial_port()
        finally:
            if acquired:
                try:
                    self.serial_lock.release()
                except Exception:
                    pass
        detail = f"{context}: {exc}"
        self.log(detail)
        self._reset_run_buttons()
        self._set_connection_status(detail, connected=False)

    def connect_serial(self):
        if self._is_connected():
            return
        if serial is None:
            self._set_connection_status("pyserial is not installed", connected=False)
            messagebox.showerror("Error", "pyserial is not installed.")
            return
        port = (self.combo_com.get() or "").strip()
        if not port:
            self._set_connection_status("No COM port selected", connected=False)
            messagebox.showerror("Error", "Please select a COM port.")
            return

        self._set_connection_status("Connecting...", connected=False, connecting=True)
        try:
            self.update_idletasks()
        except Exception:
            pass

        ser = None
        try:
            ser = serial.Serial(port, BAUD_RATE, timeout=1)
            time.sleep(2)
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            self.app.ser = ser
            self._connected_port = port
            self._connected_baud = BAUD_RATE
            self.stop_event.clear()
            self._machine_state = "Idle"
            self._set_connection_status(
                f"Connected ({port} @ {BAUD_RATE})", connected=True
            )
            self.log(f"Connected to {port}")
            messagebox.showinfo("Connected", f"Connected to {port}")
        except Exception as e:
            for candidate in (ser, getattr(self.app, "ser", None)):
                if candidate is not None:
                    try:
                        candidate.close()
                    except Exception:
                        pass
            self.app.ser = None
            self._connected_port = None
            self._connected_baud = None
            self._set_connection_status(f"Connect error: {e}", connected=False)
            self.log(f"Connect error: {e}")
            messagebox.showerror("Error", str(e))

    def disconnect_serial(self):
        """User-facing disconnect: stop a run if needed, close the port, reset UI."""
        if not self._is_connected() and getattr(self.app, "ser", None) is None:
            self._set_connection_status("Disconnected", connected=False)
            return
        # shutdown_connection sends the stop sequence if a run is active,
        # then closes the port.
        self.shutdown_connection()
        self._reset_run_buttons()
        self.log("Disconnected")
        self._set_connection_status("Disconnected", connected=False)

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
        try:
            with self.serial_lock:
                ser = getattr(self.app, "ser", None)
                if ser is None:
                    missing = True
                else:
                    missing = False
                    ser.reset_input_buffer()
        except self._serial_exc_types() as e:
            self._handle_connection_lost(e, "Laser command failed")
            return
        if missing:
            self._handle_connection_lost(
                RuntimeError("not connected"), "Laser command failed"
            )
            return

        for gcode_line in gcode_lines:
            ok = self._send_line_and_wait_ok(gcode_line, timeout=5)
            if not ok:
                if not self._is_connected():
                    return
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
        try:
            with self.serial_lock:
                ser = getattr(self.app, "ser", None)
                if ser is None:
                    return False
                ser.write(line.encode())
                ser.flush()
        except self._serial_exc_types() as e:
            self._handle_connection_lost(e, "Connection lost")
            return False

        start = time.time()
        while True:
            if self.stop_event.is_set():
                self.log(f"Aborted while waiting response for: {line.strip()}")
                return False

            if time.time() - start > timeout:
                self.log(f"Timeout waiting response for: {line.strip()}")
                return False

            ser = getattr(self.app, "ser", None)
            if ser is None:
                return False
            try:
                resp = ser.readline().decode(errors="ignore").strip().lower()
            except self._serial_exc_types() as e:
                self._handle_connection_lost(e, "Connection lost")
                return False

            if not resp:
                # timeout=0 ports (tests / non-blocking) must not busy-spin.
                to = float(getattr(ser, "timeout", 1) or 0)
                if to <= 0:
                    self.log(f"Timeout waiting response for: {line.strip()}")
                    return False
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
            with open(CUT_PLAN_GCODE_PATH, "r") as f:
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
        self._sync_set_zero_button()

        try:
            with self.serial_lock:
                ser = getattr(self.app, "ser", None)
                if ser is None:
                    messagebox.showerror("Error", "Not connected.")
                    self.is_running = False
                    self.btn_run.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    return
                ser.reset_input_buffer()
        except self._serial_exc_types() as e:
            self._handle_connection_lost(e, "Connection lost")
            self.is_running = False
            self.btn_run.config(state="normal")
            self.btn_stop.config(state="disabled")
            return

        self.log(f"Starting GCODE run ({len(lines)} lines)")
        self._run_thread = threading.Thread(
            target=self._run_gcode_worker, args=(lines,), daemon=True
        )
        self._run_thread.start()

    def _write_realtime(self, data):
        with self.serial_lock:
            ser = getattr(self.app, "ser", None)
            if ser is None:
                raise RuntimeError("not connected")
            ser.write(data)
            ser.flush()

    def _drain_input(self):
        with self.serial_lock:
            ser = getattr(self.app, "ser", None)
            if ser is not None:
                try:
                    ser.reset_input_buffer()
                except Exception:
                    pass

    def _readline_serial(self):
        ser = getattr(self.app, "ser", None)
        if ser is None:
            return None
        try:
            return ser.readline().decode(errors="ignore").strip()
        except self._serial_exc_types() as e:
            self._handle_connection_lost(e, "Connection lost")
            return None

    @staticmethod
    def _parse_grbl_state(line):
        """Extract Idle/Alarm/Hold/Run/... from a GRBL '<' status report."""
        match = re.match(r"<([^|>]+)", (line or "").strip())
        if not match:
            return None
        return match.group(1).split(":")[0].strip()

    @staticmethod
    def _parse_xyz_field(line, tag):
        """Parse tag:x,y,z from a GRBL status report. Returns a 3-tuple or None."""
        match = re.search(
            rf"{tag}:(-?\d+\.?\d*),(-?\d+\.?\d*),(-?\d+\.?\d*)",
            line or "",
        )
        if not match:
            return None
        return tuple(float(v) for v in match.groups())

    @staticmethod
    def _parse_grbl_wpos(line):
        """Work position (x, y, z) from a GRBL status report, or None.

        Uses WPos when present; otherwise MPos minus WCO.
        """
        wpos = MachineTab._parse_xyz_field(line, "WPos")
        if wpos is not None:
            return wpos
        mpos = MachineTab._parse_xyz_field(line, "MPos")
        wco = MachineTab._parse_xyz_field(line, "WCO")
        if mpos is not None and wco is not None:
            return tuple(a - b for a, b in zip(mpos, wco))
        return None

    def _apply_machine_state(self, state):
        """Reflect Idle / Alarm / Hold (etc.) on the connection status label."""
        self._machine_state = state
        if not self._is_connected():
            return
        port = self._connected_port or "?"
        baud = self._connected_baud or BAUD_RATE
        base = f"Connected ({port} @ {baud})"
        key = (state or "Idle").split(":")[0].strip()
        raw = key.lower()
        if raw in ("", "idle"):
            self._set_connection_status(base, connected=True)
        elif raw == "alarm":
            self._set_connection_status(
                f"{base} — Alarm", connected=True, fg=STATUS_DISCONNECTED_FG
            )
        elif raw == "hold":
            self._set_connection_status(
                f"{base} — Hold", connected=True, fg=STATUS_HOLD_FG
            )
        elif raw == "door":
            self._set_connection_status(
                f"{base} — Door", connected=True, fg=STATUS_DISCONNECTED_FG
            )
        else:
            self._set_connection_status(f"{base} — {key}", connected=True)

    def _incoming_lines(self, timeout):
        """Yield decoded serial lines until timeout. Avoids a tight loop in tests."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._readline_serial()
            if line is None and not self._is_connected():
                return
            if line:
                yield line
                continue
            ser = getattr(self.app, "ser", None)
            blocking = float(getattr(ser, "timeout", 1) or 0) if ser is not None else 1.0
            if blocking <= 0:
                return
            if time.monotonic() >= deadline:
                return

    def _wait_for_reset_banner(self, timeout=3.0):
        """Read after a soft reset. Returns (got_banner, alarm, last_alarm_text)."""
        got_banner = False
        alarm = False
        alarm_text = ""
        for line in self._incoming_lines(timeout):
            self.log(f"GRBL: {line}")
            low = line.lower()
            if low.startswith("grbl"):
                got_banner = True
            if (
                low.startswith("alarm")
                or "reset to continue" in low
                or ("unlock" in low and ("$x" in low or "$h" in low))
            ):
                alarm = True
                alarm_text = line
            if got_banner and alarm:
                break
        return got_banner, alarm, alarm_text

    def _query_grbl_status(self, timeout=1.5):
        """Send '?' and return (state, report_line). (None, None) if unknown."""
        if not self._is_connected():
            return None, None
        try:
            self._drain_input()
            self._write_realtime(b"?")
        except self._serial_exc_types() as e:
            self._handle_connection_lost(e, "Connection lost")
            return None, None
        except RuntimeError:
            return None, None
        for line in self._incoming_lines(timeout):
            state = self._parse_grbl_state(line)
            if state:
                return state, line
        return None, None

    def _query_grbl_state(self, timeout=1.5):
        """Send '?' and parse the '<' status report. None if unknown."""
        state, _line = self._query_grbl_status(timeout)
        return state

    def _unlock_grbl(self, timeout=5):
        """Send $X and wait for ok. Harmless if already Idle. Returns True on ok."""
        ok = self._send_line_and_wait_ok("$X\n", timeout=timeout)
        if ok:
            self.log("Sent $X (unlock)")
        else:
            self.log("Unlock ($X) failed")
        return ok

    def unlock_machine(self):
        """UI handler: unlock GRBL from Alarm ($X) and refresh the status label."""
        if not self._is_connected():
            messagebox.showerror("Error", "Not connected.")
            return
        if self.is_running:
            self.log("Unlock ignored: GCODE is running.")
            return
        try:
            if self._unlock_grbl():
                state = self._query_grbl_state() or "Idle"
                self._apply_machine_state(state)
                self.log("Machine unlocked")
            else:
                self._apply_machine_state("Alarm")
                messagebox.showerror(
                    "Error",
                    "Unlock ($X) failed. Machine may still be in Alarm.",
                )
        except self._serial_exc_types() as e:
            self._handle_connection_lost(e, "Unlock error")

    def set_work_zero(self):
        """Set the current position as G54 work origin (0, 0)."""
        if not self._is_connected():
            messagebox.showerror("Error", "Not connected.")
            return
        if self.is_running:
            self.log("Set Zero ignored: GCODE is running.")
            return
        key = (self._machine_state or "Idle").split(":")[0].strip().lower()
        if key not in ("", "idle"):
            self.log(f"Set Zero ignored: machine is in {self._machine_state}.")
            return
        try:
            if not self._send_line_and_wait_ok(SET_ZERO_CMD, timeout=5):
                self.log("Set Zero (G10 L20 P1 X0 Y0) failed")
                messagebox.showerror(
                    "Error",
                    "Set Zero failed. Machine may be in Alarm; try Unlock.",
                )
                return
            self.log(
                "Set Zero: current position is now work origin (0, 0) "
                "[G10 L20 P1]"
            )
            state, report = self._query_grbl_status()
            if state:
                self._apply_machine_state(state)
            wpos = self._parse_grbl_wpos(report) if report else None
            if wpos is not None:
                self.log(f"WPos: {wpos[0]:.3f}, {wpos[1]:.3f}")
        except self._serial_exc_types() as e:
            self._handle_connection_lost(e, "Set Zero error")

    def _recover_after_reset(self):
        """After 0x18: read banner, $X if Alarm (or always $X), M5, refresh state.

        Returns True if the machine looks usable (not Alarm/Door).
        Must only be called once stop_event is cleared, or $X/M5 would abort.
        """
        got_banner, alarm, alarm_text = self._wait_for_reset_banner()
        if alarm:
            self.log(
                f"GRBL in Alarm after reset ({alarm_text or 'alarm'}); sending $X."
            )
            self._apply_machine_state("Alarm")
        elif got_banner:
            self.log("GRBL reset banner received.")
        # $X is required after a mid-job reset (Alarm / 'Reset to continue')
        # and is a no-op ok if already Idle.
        if not self._unlock_grbl():
            state = self._query_grbl_state() or "Alarm"
            self._apply_machine_state(state)
            return state.lower() not in ("alarm", "door")
        if not self._send_line_and_wait_ok("M5\n", timeout=5):
            self.log("WARNING: M5 after reset did not get ok.")
        state = self._query_grbl_state() or "Idle"
        self._apply_machine_state(state)
        return state.lower() not in ("alarm", "door")

    def _recover_to_idle(self, auto_unlock=True):
        """Query '?' and leave Alarm/Hold so the next command can run."""
        state = self._query_grbl_state()
        if state is None:
            return True
        self._apply_machine_state(state)
        key = state.lower()
        if key in ("idle", "jog"):
            return True
        if key == "run":
            self.log("Machine is still moving; try again when Idle.")
            return False
        if key == "hold":
            # Do not resume (~) — that would continue the stopped cut.
            self.log("Machine is in Hold; soft-reset (will not resume) then unlock.")
            try:
                self._write_realtime(b"\x18")
            except self._serial_exc_types() as e:
                self._handle_connection_lost(e, "Connection lost")
                return False
            time.sleep(0.2)
            return self._recover_after_reset()
        if key in ("alarm", "door"):
            if not auto_unlock:
                return False
            self.log(f"Machine is in {state}; sending $X to unlock.")
            if self._unlock_grbl():
                new = self._query_grbl_state() or "Idle"
                self._apply_machine_state(new)
                return new.lower() not in ("alarm", "door", "hold")
            self._apply_machine_state("Alarm")
            return False
        return True

    def _join_run_thread(self, timeout=2.0):
        thread = getattr(self, "_run_thread", None)
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=timeout)

    def stop_gcode(self):
        if not self.is_running:
            return

        self.log("STOP requested by user")

        # Stop the streaming worker first so it will not send more lines,
        # then halt motion and reset the controller.
        self.stop_event.set()

        if self.app.ser:
            try:
                # Feed hold: decelerate immediately (realtime, no newline).
                self._write_realtime(b"!")
                time.sleep(0.15)
                # Soft reset: clear the planner so the job cannot resume.
                # (M5 sent during Hold would be wiped by this reset anyway.)
                self._write_realtime(b"\x18")
            except self._serial_exc_types() as e:
                self._handle_connection_lost(e, "Error while stopping")
                self.btn_stop.config(state="disabled")
                return
            except Exception as e:
                self.log(f"Error while stopping: {e}")

            # The worker may still be blocked on readline; the reset unblocks
            # it. Join before clearing stop_event so it cannot send another line.
            self._join_run_thread(timeout=2.0)
            self.stop_event.clear()

            try:
                recovered = self._recover_after_reset()
                if recovered and self._is_connected():
                    self.log("STOP complete; machine is ready.")
                elif self._is_connected():
                    self.log(
                        "STOP complete, but machine is not Idle. "
                        "Press Unlock if the status shows Alarm."
                    )
            except self._serial_exc_types() as e:
                self._handle_connection_lost(e, "Error while stopping")
            except Exception as e:
                self.log(f"Error while recovering after STOP: {e}")
        else:
            self._join_run_thread(timeout=2.0)
            self.stop_event.clear()

        self.btn_stop.config(state="disabled")
        # Machine is idle again (or disconnected). Allow jog / a new run
        # even if the worker's _on_run_finished has not been processed yet.
        self.is_running = False
        try:
            self.btn_run.config(state="normal")
        except Exception:
            pass
        self._sync_set_zero_button()

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
        already_idle = not self.is_running
        self.is_running = False
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")
        self._sync_set_zero_button()
        # Disconnect / unexpected drop already reported the outcome.
        if already_idle:
            return

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
            self._show_preview_message(f"No G0/G1/G2/G3 moves in:\n{path}")

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

    def _is_visible_in_notebooks(self):
        """True only when every ancestor Notebook has this branch selected.

        Needed when Machine lives under Engraver sub-Notebook inside the
        unified app main Notebook — selecting Frame Toolkit must disable jog.
        """
        widget = self
        while widget is not None:
            parent = getattr(widget, "master", None)
            if parent is None:
                break
            if isinstance(parent, ttk.Notebook):
                try:
                    if parent.select() != str(widget):
                        return False
                except Exception:
                    return False
            widget = parent
        return True

    def on_jog_key(self, event):
        # Chi xu ly khi nhanh tab Machine dang visible (moi notebook cha)
        if not self._is_visible_in_notebooks():
            return

        # Bo qua khi dang go chu trong o nhap (Entry/Combobox/Text...)
        try:
            focus = self.focus_get()
        except Exception:
            focus = None
        if isinstance(focus, (tk.Entry, tk.Text, tk.Spinbox,
                              ttk.Entry, ttk.Spinbox, ttk.Combobox)):
            return
        # scrolledtext.ScrolledText is a Frame subclass hosting a Text
        try:
            if focus is not None and focus.winfo_class() in ("Text", "TEntry", "TCombobox"):
                # already covered by isinstance for most cases; keep soft check
                if isinstance(focus, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
                    return
        except Exception:
            pass

        key = event.keysym.lower()
        if key not in JOG_KEYS:
            return
        axis, direction = JOG_KEYS[key]
        self.jog(axis, direction)
        return "break"

    def shutdown_connection(self):
        """Conservative close: stop workers and close the serial port.

        Does not send speculative machine commands. If a GCODE run is active,
        request the existing cooperative stop first (that path already sends
        the halt sequence the Machine tab uses for Stop).
        """
        try:
            if getattr(self, "is_running", False) and self._is_connected():
                # Existing stop path — not speculative; user/app is ending a run.
                try:
                    self.stop_gcode()
                except Exception:
                    self.stop_event.set()
        except Exception:
            pass
        try:
            self.stop_event.set()
        except Exception:
            pass
        # Wait briefly for an in-flight jog / stream to finish before closing.
        acquired_jog = False
        try:
            acquired_jog = self.jog_lock.acquire(timeout=1.0)
        except Exception:
            acquired_jog = False
        acquired_serial = False
        try:
            acquired_serial = self.serial_lock.acquire(timeout=1.0)
        except Exception:
            acquired_serial = False
        try:
            self._close_serial_port()
        finally:
            if acquired_serial:
                try:
                    self.serial_lock.release()
                except Exception:
                    pass
            if acquired_jog:
                try:
                    self.jog_lock.release()
                except Exception:
                    pass
        self.is_running = False

    def build_jog_lines(self, axis, direction, step):
        # Legacy relative jog used before $J= (kept for tests / reference).
        return [
            "G91\n",
            f"G0 {axis}{direction * step:.3f}\n",
            "G90\n",
        ]

    def build_jog_command(self, axis, direction, step):
        # GRBL 1.1 jog: does not leave the modal state in G91 if a later
        # command fails, unlike the older G91 / G0 / G90 sequence.
        feed = int(RAPID_RATE_MM_MIN)
        return f"$J=G91 {axis}{direction * step:.3f} F{feed}\n"

    def jog(self, axis, direction):
        if not self.app.ser:
            self.log("Jog ignored: not connected.")
            messagebox.showerror("Error", "Not connected.")
            return

        if self.is_running:
            self.log("Jog ignored: GCODE is running.")
            return

        # A leftover stop_event from STOP used to abort the first jog line
        # immediately (looked like an Alarm failure). Clear it once idle.
        if self.stop_event.is_set():
            self.stop_event.clear()

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

        cmd = self.build_jog_command(axis, direction, step)
        threading.Thread(target=self._jog_worker, args=(cmd,), daemon=True).start()

    def _jog_worker(self, cmd):
        label = f"Jog {cmd.strip()}"
        try:
            if not self._recover_to_idle(auto_unlock=True):
                state = self._machine_state or "unknown"
                self.log(
                    f"{label} FAILED: machine is in {state}. "
                    "Press Unlock if the status shows Alarm."
                )
                return

            with self.serial_lock:
                ser = getattr(self.app, "ser", None)
                if ser is None:
                    return
                ser.reset_input_buffer()

            if not self._send_line_and_wait_ok(cmd, timeout=30):
                state = self._query_grbl_state()
                if state:
                    self._apply_machine_state(state)
                self.log(
                    f"{label} FAILED"
                    + (f" (state: {state})" if state else "")
                )
                return

            self.log(label)
            state = self._query_grbl_state()
            if state:
                self._apply_machine_state(state)
        except self._serial_exc_types() as e:
            self._handle_connection_lost(e, "Jog error")
        except Exception as e:
            self.log(f"Jog error: {e}")
        finally:
            self.jog_lock.release()
