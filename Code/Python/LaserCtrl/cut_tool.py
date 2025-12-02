import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import serial
import serial.tools.list_ports
import threading
import time

from cut_handler import *   # import your logic (cut_ffd, cut_optimize, export_svg...)

########################################################################
# GLOBAL FONT
########################################################################
APP_FONT_FAMILY = "Times New Roman"
APP_FONT_SIZE = 11
APP_FONT = (APP_FONT_FAMILY, APP_FONT_SIZE)

########################################################################
# GCODE RUNNER
########################################################################
class GCodeRunner:
    def __init__(self):
        self.ser = None
        self.running = False

    def list_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port, baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)  # wait for GRBL reset
            return True
        except Exception as e:
            print("Connection error:", e)
            return False

    def send_gcode_file(self, filename, progress_callback):
        if not self.ser:
            messagebox.showerror("Error", "Not connected to COM port!")
            return

        self.running = True

        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total = len(lines)

        for i, line in enumerate(lines):
            if not self.running:
                break

            g = line.strip()
            if g:
                self.ser.write((g + "\n").encode())
                self.ser.flush()

                # Wait for ok
                resp = self.ser.readline().decode(errors="ignore").strip()
                # Could be empty at times, so we loop
                while resp == "":
                    resp = self.ser.readline().decode(errors="ignore").strip()

            # Update progress (0..1)
            progress_callback((i + 1) / total)

        self.running = False

    def stop(self):
        self.running = False


########################################################################
# MAIN TOOL
########################################################################
def run_tool(compute_cut_lines_func):

    gcode_runner = GCodeRunner()

    root = tk.Tk()
    root.title("Laser Cutting Tool")
    root.geometry("550x520")

    # Styling
    def new_label(text, r, c):
        return tk.Label(root, text=text, font=APP_FONT).grid(row=r, column=c, sticky="w", padx=10, pady=5)

    def new_entry(width, r, c):
        e = tk.Entry(root, font=APP_FONT, width=width)
        e.grid(row=r, column=c, sticky="w", padx=10, pady=5)
        return e

    ###################################################################
    # INPUT UI
    ###################################################################
    new_label("d (length):", 0, 0)
    entry_d = new_entry(15, 0, 1)

    new_label("r (width):", 1, 0)
    entry_r = new_entry(15, 1, 1)

    new_label("c (gap):", 2, 0)
    entry_c = new_entry(15, 2, 1)

    new_label("List a[i] (comma separated):", 3, 0)
    entry_a = new_entry(30, 3, 1)

    separator = ttk.Separator(root, orient='horizontal')
    separator.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)

    ###################################################################
    # GENERATE SVG + GCODE
    ###################################################################
    def generate_files():
        try:
            d = float(entry_d.get())
            r = float(entry_r.get())
            c = float(entry_c.get())
            a = [float(x.strip()) for x in entry_a.get().split(",") if x.strip()]
        except:
            messagebox.showerror("Error", "Invalid input")
            return

        # Your logic
        first_result = cut_optimize(d, a)
        cut_lines = compute_cut_lines_func(first_result, d, r, c, include_end_cut=True)

        export_svg(cut_lines, "cut_plan.svg")
        export_gcode(cut_lines, "cut_plan.gcode")

        messagebox.showinfo("Done", "Generated cut_plan.svg & cut_plan.gcode")

    btn_gen = tk.Button(root, text="Generate SVG + GCODE", font=APP_FONT, command=generate_files)
    btn_gen.grid(row=5, column=0, columnspan=3, pady=10)

    ###################################################################
    # PREVIEW SVG
    ###################################################################
    def preview_svg():
        webbrowser.open("cut_plan.svg")

    btn_prev = tk.Button(root, text="Preview SVG", font=APP_FONT, command=preview_svg)
    btn_prev.grid(row=6, column=0, columnspan=3, pady=10)

    separator2 = ttk.Separator(root, orient='horizontal')
    separator2.grid(row=7, column=0, columnspan=3, sticky="ew", pady=10)

    ###################################################################
    # COM PORT + RUN GCODE
    ###################################################################
    new_label("Select COM Port:", 8, 0)

    combo_ports = ttk.Combobox(root, font=APP_FONT, state="readonly")
    combo_ports['values'] = gcode_runner.list_ports()
    combo_ports.grid(row=8, column=1, padx=10, pady=5)

    lbl_conn_status = tk.Label(root, text="Not connected", fg="red", font=APP_FONT)
    lbl_conn_status.grid(row=8, column=2, padx=10)

    def refresh_ports():
        combo_ports['values'] = gcode_runner.list_ports()

    tk.Button(root, text="Refresh", font=APP_FONT, command=refresh_ports).grid(row=8, column=3)

    def connect_port():
        port = combo_ports.get()
        if not port:
            messagebox.showerror("Error", "Select a COM port")
            return

        ok = gcode_runner.connect(port)
        if ok:
            lbl_conn_status.config(text="Connected", fg="green")
        else:
            lbl_conn_status.config(text="Failed", fg="red")

    tk.Button(root, text="Connect", font=APP_FONT, command=connect_port).grid(row=9, column=1, pady=5)

    ###################################################################
    # PROGRESS BAR
    ###################################################################
    new_label("Progress:", 10, 0)
    progress = ttk.Progressbar(root, length=300)
    progress.grid(row=10, column=1, columnspan=2, pady=5)

    ###################################################################
    # RUN GCODE
    ###################################################################
    def run_gcode():
        if not gcode_runner.ser:
            messagebox.showerror("Error", "Connect COM port first")
            return

        progress["value"] = 0

        def update_progress(p):
            progress["value"] = p * 100

        # Run in thread
        th = threading.Thread(target=gcode_runner.send_gcode_file,
                              args=("cut_plan.gcode", update_progress))
        th.daemon = True
        th.start()

    btn_run = tk.Button(root, text="Run GCODE", font=APP_FONT, bg="#0077CC", fg="white",
                        command=run_gcode)
    btn_run.grid(row=11, column=0, columnspan=3, pady=15)

    ###################################################################
    root.mainloop()


###########################################################################
# START TOOL
###########################################################################
run_tool(compute_cut_lines_fixed)
