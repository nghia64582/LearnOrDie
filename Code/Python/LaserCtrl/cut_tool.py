import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from cut_handler import *
import serial
import serial.tools.list_ports
import threading
import time

APP_FONT = ("Times New Roman", 12)


def run_tool(compute_cut_lines_func):
    root = tk.Tk()
    root.title("Laser Cutting Tool")

    # ========== INPUT GRID ==========
    tk.Label(root, text="d (length):", font=APP_FONT).grid(row=0, column=0, sticky="w", pady=2)
    entry_d = tk.Entry(root, font=APP_FONT)
    entry_d.grid(row=0, column=1, pady=2)

    tk.Label(root, text="r (width):", font=APP_FONT).grid(row=1, column=0, sticky="w", pady=2)
    entry_r = tk.Entry(root, font=APP_FONT)
    entry_r.grid(row=1, column=1, pady=2)

    tk.Label(root, text="c (gap):", font=APP_FONT).grid(row=2, column=0, sticky="w", pady=2)
    entry_c = tk.Entry(root, font=APP_FONT)
    entry_c.grid(row=2, column=1, pady=2)

    tk.Label(root, text="List a[i] (comma separated):", font=APP_FONT).grid(row=3, column=0, sticky="w", pady=2)
    entry_a = tk.Entry(root, width=40, font=APP_FONT)
    entry_a.grid(row=3, column=1, pady=2)

    # NEW: FEEDRATE + POWER
    tk.Label(root, text="Speed (feedrate, max 2000):", font=APP_FONT).grid(row=4, column=0, sticky="w", pady=2)
    entry_speed = tk.Entry(root, font=APP_FONT)
    entry_speed.insert(0, "600")
    entry_speed.grid(row=4, column=1, pady=2)

    tk.Label(root, text="Power (laser, max 1000):", font=APP_FONT).grid(row=5, column=0, sticky="w", pady=2)
    entry_power = tk.Entry(root, font=APP_FONT)
    entry_power.insert(0, "100")
    entry_power.grid(row=5, column=1, pady=2)

    separator = ttk.Separator(root, orient='horizontal')
    separator.grid(row=6, columnspan=2, sticky="ew", pady=10)

    # ========== GENERATE FILES ==========

    def generate_files():
        # Read values
        try:
            d = float(entry_d.get())
            r = float(entry_r.get())
            c = float(entry_c.get())
            a = [float(x.strip()) for x in entry_a.get().split(",") if x.strip()]

            feedrate = int(entry_speed.get())
            power = int(entry_power.get())
        except:
            messagebox.showerror("Error", "Invalid input")
            return

        if feedrate > 2000 or feedrate <= 0:
            messagebox.showerror("Error", "Feedrate must be 1–2000")
            return

        if power > 1000 or power <= 0:
            messagebox.showerror("Error", "Power must be 1–1000")
            return

        # Compute cuts
        first_result = cut_optimize(d, a)
        cut_lines = compute_cut_lines_func(first_result, d, r, c, include_end_cut=True)

        # Export SVG & GCODE
        export_svg(cut_lines, "cut_plan.svg")
        export_gcode(cut_lines, "cut_plan.gcode",
                     feedrate=feedrate,
                     laser_power=power)

        messagebox.showinfo("Done", "Generated cut_plan.svg & cut_plan.gcode")

    def preview_svg():
        webbrowser.open("cut_plan.svg")

    tk.Button(root, text="Generate SVG + GCODE", font=APP_FONT,
              command=generate_files).grid(row=7, columnspan=2, pady=10)
    tk.Button(root, text="Preview SVG", font=APP_FONT,
              command=preview_svg).grid(row=8, columnspan=2, pady=10)

    # ===========================
    #   GCODE SERIAL SECTION
    # ===========================

    serial_port = None
    com_var = tk.StringVar()

    def refresh_com_ports():
        ports = [p.device for p in serial.tools.list_ports.comports()]
        com_menu['menu'].delete(0, 'end')
        for p in ports:
            com_menu['menu'].add_command(label=p, command=lambda v=p: com_var.set(v))
        if ports:
            com_var.set(ports[0])

    tk.Label(root, text="COM Port:", font=APP_FONT).grid(row=9, column=0, pady=2)
    com_menu = tk.OptionMenu(root, com_var, "")
    com_menu.grid(row=9, column=1, pady=2, sticky="ew")
    refresh_com_ports()

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
    progress_bar.grid(row=11, columnspan=2, sticky="ew", pady=6)

    def connect_serial():
        nonlocal serial_port
        try:
            serial_port = serial.Serial(com_var.get(), 115200, timeout=1)
            messagebox.showinfo("Connected", f"Connected to {com_var.get()}")
        except:
            messagebox.showerror("Error", "Failed to connect")

    tk.Button(root, text="Connect", font=APP_FONT,
              command=connect_serial).grid(row=10, columnspan=2, pady=5)

    # SEND GCODE
    def send_gcode_thread():
        nonlocal serial_port
        if serial_port is None:
            messagebox.showerror("Error", "Not connected to serial")
            return

        try:
            with open("cut_plan.gcode", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except:
            messagebox.showerror("Error", "cut_plan.gcode not found")
            return

        total = len(lines)
        for i, line in enumerate(lines):
            serial_port.write((line + "\n").encode())
            time.sleep(0.02)  # wait to avoid overflow
            progress_var.set((i + 1) / total * 100)

        messagebox.showinfo("Done", "GCODE sent successfully")

    def send_gcode():
        threading.Thread(target=send_gcode_thread, daemon=True).start()

    tk.Button(root, text="Run GCODE", font=APP_FONT,
              command=send_gcode).grid(row=12, columnspan=2, pady=8)

    root.mainloop()


# START TOOL
run_tool(compute_cut_lines_fixed)
