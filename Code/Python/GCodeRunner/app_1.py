import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports

ser = None

def list_com_ports():
    return [port.device for port in serial.tools.list_ports.comports()]


def connect_port():
    global ser
    port = com_var.get()
    if not port:
        messagebox.showwarning("Warning", "Please select a COM port.")
        return
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        messagebox.showinfo("Connected", f"Connected to {port}")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def send_gcode():
    global ser
    if ser is None:
        messagebox.showwarning("Warning", "Not connected to any COM port.")
        return
    cmd = gcode_entry.get().strip()
    if not cmd:
        return
    try:
        ser.write((cmd + "\n").encode())
    except Exception as e:
        messagebox.showerror("Error", str(e))


root = tk.Tk()
root.title("Laser CNC G-Code Sender")
root.geometry("400x220")

# COM port selection
com_label = tk.Label(root, text="Select COM Port:")
com_label.pack(pady=5)

com_var = tk.StringVar()
com_dropdown = ttk.Combobox(root, textvariable=com_var, values=list_com_ports(), state="readonly")
com_dropdown.pack(pady=5)

refresh_button = tk.Button(root, text="Refresh", command=lambda: com_dropdown.config(values=list_com_ports()))
refresh_button.pack(pady=5)

connect_button = tk.Button(root, text="Connect", command=connect_port)
connect_button.pack(pady=5)

# G-code input
entry_label = tk.Label(root, text="Enter G-Code:")
entry_label.pack(pady=5)

gcode_entry = tk.Entry(root, width=40)
gcode_entry.pack(pady=5)

send_button = tk.Button(root, text="Send", command=send_gcode)
send_button.pack(pady=10)

root.mainloop()
