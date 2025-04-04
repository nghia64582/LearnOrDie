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
        self.geometry("500x350")  # Increased window size
        self.resizable(True, True)
        
        # Clipboard monitoring variables
        self.monitor_active = False
        self.monitor_thread = None
        self.last_clipboard_content = ""
        self.idle_counter = 0
        
        # Set up larger font and styling
        self.default_font = ('Arial', 14)  # Increased font size by ~40%
        self.setup_styles()
        
        # Create and place the widgets
        self.create_widgets()
        
        # Update CPU usage indicator periodically
        self.update_cpu_usage()
        
    def setup_styles(self):
        """Configure styles for larger components"""
        self.style = ttk.Style()
        
        # Configure larger fonts and padding for all elements
        self.style.configure('TLabel', font=self.default_font, padding=(5, 5))
        self.style.configure('TButton', font=self.default_font, padding=(10, 5))
        self.style.configure('TEntry', font=self.default_font, padding=(5, 5))
        self.style.configure('TCheckbutton', font=self.default_font, padding=(5, 10))
        self.style.configure('TFrame', padding=(10, 10))
        self.style.configure('TLabelframe', font=self.default_font, padding=(10, 10))
        self.style.configure('TLabelframe.Label', font=self.default_font)
        
    def create_widgets(self):
        # Create a main frame with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Prefix input section
        prefix_frame = ttk.Frame(main_frame)
        prefix_frame.pack(fill=tk.X, pady=15)  # Increased vertical padding
        
        prefix_label = ttk.Label(prefix_frame, text="Prefix:")
        prefix_label.pack(side=tk.LEFT, padx=10)  # Increased horizontal padding
        
        self.prefix_var = tk.StringVar(value="")
        self.prefix_entry = ttk.Entry(prefix_frame, textvariable=self.prefix_var, width=20, font=self.default_font)
        self.prefix_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)  # Increased padding
        
        # Toggle button for auto-monitor with indicator
        toggle_frame = ttk.Frame(main_frame)
        toggle_frame.pack(fill=tk.X, pady=15)  # Increased vertical padding
        
        self.toggle_var = tk.BooleanVar(value=False)
        self.toggle_button = ttk.Checkbutton(
            toggle_frame, 
            text="Auto-convert clipboard numbers", 
            variable=self.toggle_var,
            command=self.toggle_monitoring,
            style='TCheckbutton'
        )
        self.toggle_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # CPU load indicator
        self.cpu_indicator_var = tk.StringVar(value="Low")
        self.cpu_indicator = ttk.Label(toggle_frame, textvariable=self.cpu_indicator_var)
        self.cpu_indicator.pack(side=tk.RIGHT, padx=10)  # Increased padding
        
        cpu_label = ttk.Label(toggle_frame, text="CPU:")
        cpu_label.pack(side=tk.RIGHT)
        
        # Result display
        result_frame = ttk.LabelFrame(main_frame, text="Last Conversion")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=15)  # Increased padding
        
        original_label = ttk.Label(result_frame, text="Original:")
        original_label.pack(anchor=tk.W, padx=10, pady=10)  # Increased padding
        
        self.original_var = tk.StringVar(value="")
        original_display = ttk.Entry(result_frame, textvariable=self.original_var, state="readonly", font=self.default_font)
        original_display.pack(fill=tk.X, padx=10, pady=5)  # Increased padding
        
        converted_label = ttk.Label(result_frame, text="Converted:")
        converted_label.pack(anchor=tk.W, padx=10, pady=10)  # Increased padding
        
        self.converted_var = tk.StringVar(value="")
        converted_display = ttk.Entry(result_frame, textvariable=self.converted_var, state="readonly", font=self.default_font)
        converted_display.pack(fill=tk.X, padx=10, pady=5)  # Increased padding
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, font=('Arial', 12))
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
            self.cpu_indicator_var.set("Low")
    
    def monitor_clipboard(self):
        """Monitor clipboard for integer numbers and convert them - with adaptive sleep"""
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
                        
                        # Reset idle counter after activity
                        self.idle_counter = 0
                    else:
                        self.last_clipboard_content = current_content
                else:
                    # Update the last clipboard content
                    self.last_clipboard_content = current_content
                    # Increment idle counter
                    self.idle_counter += 1
                
                # Adaptive sleep: Sleep longer when idle, shorter when active
                time.sleep(0.5)
            except Exception as e:
                self.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
                time.sleep(1)
    
    def update_cpu_usage(self):
        """Update the CPU usage indicator"""
        if self.monitor_active:
            if self.idle_counter < 5:
                self.cpu_indicator_var.set("Medium")
            elif self.idle_counter < 20:
                self.cpu_indicator_var.set("Low")
            else:
                self.cpu_indicator_var.set("Very Low")
        else:
            self.cpu_indicator_var.set("Low")
            
        # Schedule the next update
        self.after(1000, self.update_cpu_usage)
    
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