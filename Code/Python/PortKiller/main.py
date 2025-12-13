# ------- DPI FIX -------
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()
# -----------------------

import os
import socket
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading

class PortKillerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Port Killer Utility")
        self.root.geometry("500x400")
        self.root.resizable(True, True)
        
        # Set app icon if desired
        # self.root.iconbitmap("icon.ico")  # Uncomment and add your icon path
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10, "bold"))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        self.style.configure("Result.TLabel", font=("Arial", 9))
        
        # Create the main frame
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # App title
        title_label = ttk.Label(
            main_frame, 
            text="Port Killer Utility", 
            style="Header.TLabel"
        )
        title_label.pack(pady=(0, 20))
        
        # Port input frame
        port_frame = ttk.Frame(main_frame)
        port_frame.pack(fill=tk.X, pady=(0, 15))
        
        port_label = ttk.Label(
            port_frame, 
            text="Enter Port Number:", 
            style="TLabel"
        )
        port_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_entry = ttk.Entry(port_frame, width=15)
        self.port_entry.pack(side=tk.LEFT)
        self.port_entry.focus()
        
        # Action buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.kill_button = ttk.Button(
            button_frame, 
            text="Find and Kill Process", 
            style="TButton",
            command=self.kill_port_thread
        )
        self.kill_button.pack(pady=10)
        
        # Status frame
        status_frame = ttk.Frame(main_frame, relief=tk.GROOVE, borderwidth=2)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        status_label = ttk.Label(
            status_frame, 
            text="Status:", 
            style="TLabel"
        )
        status_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Create a text widget for better output display
        self.result_text = tk.Text(
            status_frame, 
            height=8, 
            width=50, 
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.result_text.pack(padx=10, pady=(0, 10), fill=tk.BOTH, expand=True)
        self.result_text.config(state=tk.DISABLED)
        
        # Scrollbar for result text
        scrollbar = ttk.Scrollbar(self.result_text, command=self.result_text.yview)
        self.result_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # OS info label at bottom
        os_info = "Windows" if os.name == 'nt' else "Linux/macOS"
        os_label = ttk.Label(
            main_frame, 
            text=f"Detected OS: {os_info}", 
            style="Result.TLabel"
        )
        os_label.pack(anchor=tk.W, pady=(10, 0))

    def update_status(self, message, is_append=False):
        """Update the status display with a message"""
        self.result_text.config(state=tk.NORMAL)
        if not is_append:
            self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)

    def find_process_using_port(self, port):
        """Find the process ID (PID) using the given port."""
        try:
            # Use netstat (Windows) or lsof (Linux/macOS) to find the PID
            if os.name == 'nt':  # Windows
                cmd = f'netstat -ano | findstr :{port}'
            else:  # Linux/macOS
                cmd = f'lsof -i :{port} | grep LISTEN'

            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True)
            
            # Extract PID from output
            lines = output.strip().split("\n")
            pids = set()
            for line in lines:
                parts = line.split()
                if os.name == 'nt':  # Windows format
                    pids.add(parts[-1])  # PID is the last column
                else:  # Linux/macOS format
                    pids.add(parts[1])  # PID is the second column
            
            return pids

        except subprocess.CalledProcessError:
            return set()

    def kill_process(self, pid):
        """Kill process by PID."""
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
            self.update_status(f"✅ Process {pid} terminated.", is_append=True)
            return True
        except Exception as e:
            self.update_status(f"❌ Failed to terminate process {pid}: {e}", is_append=True)
            return False

    def kill_port(self):
        """Main function to find and kill processes using a port"""
        # Get port from entry
        port = self.port_entry.get().strip()
        
        # Validate port
        if not port.isdigit():
            self.update_status("❌ Invalid port number. Please enter a numeric port.")
            return
        
        # Enable the button again
        self.root.after(0, lambda: self.kill_button.config(state=tk.NORMAL))
        
        self.update_status(f"🔍 Searching for processes using port {port}...")
        pids = self.find_process_using_port(port)

        if not pids:
            self.update_status(f"✅ No processes found using port {port}.", is_append=True)
        else:
            success_count = 0
            for pid in pids:
                if self.kill_process(pid):
                    success_count += 1
            
            if success_count == len(pids):
                self.update_status(f"✅ Successfully terminated all processes on port {port}.", is_append=True)
            else:
                self.update_status(f"⚠️ Terminated {success_count} out of {len(pids)} processes on port {port}.", is_append=True)

    def kill_port_thread(self):
        """Run the port killing process in a separate thread to avoid freezing the UI"""
        self.kill_button.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.kill_port)
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = PortKillerApp(root)
    root.mainloop()