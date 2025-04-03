import tkinter as tk
from tkinter import ttk
import pyperclip
import string
import threading
import time
import re

class AutoBase36Converter(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Configure the window
        self.title("Auto Base36 Converter")
        self.geometry("400x250")
        self.resizable(True, True)
        
        # Clipboard monitoring variables
        self.monitor_active = False
        self.monitor_thread = None
        self.last_clipboard_content = ""
        
        # Create and place the widgets
        self.create_widgets()
        
        # Set up styling
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('TLabel', font=('Arial', 10))
        self.style.configure('TEntry', font=('Arial', 10))
        
    def create_widgets(self):
        # Create a main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Prefix input section
        prefix_frame = ttk.Frame(main_frame)
        prefix_frame.pack(fill=tk.X, pady=10)
        
        prefix_label = ttk.Label(prefix_frame, text="Prefix:")
        prefix_label.pack(side=tk.LEFT, padx=5)
        
        self.prefix_var = tk.StringVar(value="")
        self.prefix_entry = ttk.Entry(prefix_frame, textvariable=self.prefix_var, width=20)
        self.prefix_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Toggle button for auto-monitor
        self.toggle_var = tk.BooleanVar(value=False)
        self.toggle_button = ttk.Checkbutton(
            main_frame, 
            text="Auto-convert clipboard numbers", 
            variable=self.toggle_var,
            command=self.toggle_monitoring
        )
        self.toggle_button.pack(fill=tk.X, pady=10)
        
        # Result display
        result_frame = ttk.LabelFrame(main_frame, text="Last Conversion")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        original_label = ttk.Label(result_frame, text="Original:")
        original_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.original_var = tk.StringVar(value="")
        original_display = ttk.Entry(result_frame, textvariable=self.original_var, state="readonly")
        original_display.pack(fill=tk.X, padx=5, pady=5)
        
        converted_label = ttk.Label(result_frame, text="Converted:")
        converted_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.converted_var = tk.StringVar(value="")
        converted_display = ttk.Entry(result_frame, textvariable=self.converted_var, state="readonly")
        converted_display.pack(fill=tk.X, padx=5, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def convert_to_base36(self, number):
        """Convert decimal number to base36"""
        try:
            number = int(number)
            if number < 0:
                return None  # Skip negative numbers
            
            # Use string.digits + string.ascii_lowercase for base36 digits (0-9, a-z)
            digits = string.digits + string.ascii_lowercase
            
            if number == 0:
                return "0"
                
            result = ""
            while number > 0:
                result = digits[number % 36] + result
                number //= 36
                
            return result
        except ValueError:
            return None
    
    def toggle_monitoring(self):
        """Toggle clipboard monitoring on/off"""
        if self.toggle_var.get():
            # Start monitoring
            self.monitor_active = True
            self.status_var.set("Monitoring clipboard for numbers...")
            
            # Save current clipboard content to avoid processing it immediately
            self.last_clipboard_content = pyperclip.paste()
            
            # Start the monitoring thread
            self.monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
            self.monitor_thread.start()
        else:
            # Stop monitoring
            self.monitor_active = False
            self.status_var.set("Monitoring stopped")
    
    def monitor_clipboard(self):
        """Monitor clipboard for integer numbers and convert them"""
        while self.monitor_active:
            try:
                # Get current clipboard content
                current_content = pyperclip.paste()
                
                # Check if content has changed and is a positive integer number
                if (current_content != self.last_clipboard_content and 
                    current_content.strip() and 
                    re.match(r'^\d+$', current_content.strip())):
                    
                    original = current_content.strip()
                    
                    # Convert to base36
                    base36_value = self.convert_to_base36(original)
                    
                    if base36_value:
                        # Add prefix
                        prefix = self.prefix_var.get()
                        result = prefix + base36_value
                        
                        # Update the display (using the main thread)
                        self.after(0, lambda: self.original_var.set(original))
                        self.after(0, lambda: self.converted_var.set(result))
                        self.after(0, lambda: self.status_var.set(f"Converted {original} → {result}"))
                        
                        # Copy result back to clipboard
                        self.last_clipboard_content = result
                        pyperclip.copy(result)
                    else:
                        self.last_clipboard_content = current_content
                else:
                    # Update the last clipboard content
                    self.last_clipboard_content = current_content
                    
                # Sleep to prevent high CPU usage
                time.sleep(0.5)
                
            except Exception as e:
                self.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
                time.sleep(1)
    
    def on_closing(self):
        """Clean up before closing"""
        self.monitor_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        self.destroy()

if __name__ == "__main__":
    # Check if pyperclip is installed
    try:
        import pyperclip
    except ImportError:
        print("The pyperclip module is required. Install it with 'pip install pyperclip'")
        exit(1)
    
    app = AutoBase36Converter()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()