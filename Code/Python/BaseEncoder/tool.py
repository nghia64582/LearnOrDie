import tkinter as tk
from tkinter import ttk
import pyperclip
import string

class Base36Converter(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Configure the window
        self.title("Base36 Converter")
        self.geometry("400x300")
        self.resizable(True, True)
        
        # Create and place the widgets
        self.create_widgets()
        
        # Set up styling
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('TLabel', font=('Arial', 10))
        self.style.configure('TEntry', font=('Arial', 10))
        345
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
        
        # Convert button
        convert_button = ttk.Button(main_frame, text="Convert Clipboard to Base36", command=self.convert_clipboard)
        convert_button.pack(fill=tk.X, pady=10)
        
        # Manual input section
        manual_frame = ttk.Frame(main_frame)
        manual_frame.pack(fill=tk.X, pady=10)
        
        manual_label = ttk.Label(manual_frame, text="Decimal input:")
        manual_label.pack(side=tk.LEFT, padx=5)
        
        self.manual_var = tk.StringVar(value="")
        self.manual_entry = ttk.Entry(manual_frame, textvariable=self.manual_var, width=20)
        self.manual_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        convert_manual_button = ttk.Button(main_frame, text="Convert Input to Base36", command=self.convert_manual)
        convert_manual_button.pack(fill=tk.X, pady=10)
        
        # Result display
        result_label = ttk.Label(main_frame, text="Result:")
        result_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.result_var = tk.StringVar(value="")
        result_display = ttk.Entry(main_frame, textvariable=self.result_var, state="readonly", width=40)
        result_display.pack(fill=tk.X, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    
    def convert_to_base36(self, number):
        """Convert decimal number to base36"""
        try:
            number = int(number)
            if number < 0:
                return "-" + self.convert_to_base36(-number)
            
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
            self.status_var.set("Error: Invalid decimal number")
            return None
    
    def convert_clipboard(self):
        """Convert number from clipboard to base36 with prefix"""
        try:
            # Get the decimal number from clipboard
            clipboard_content = pyperclip.paste()
            
            # Convert to base36
            base36_value = self.convert_to_base36(clipboard_content)
            
            if base36_value:
                # Add prefix
                prefix = self.prefix_var.get()
                result = prefix + base36_value
                
                # Display result
                self.result_var.set(result)
                
                # Copy result back to clipboard
                pyperclip.copy(result)
                
                self.status_var.set(f"Converted {clipboard_content} to {result} (copied to clipboard)")
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
    
    def convert_manual(self):
        """Convert manually entered number to base36 with prefix"""
        try:
            # Get the decimal number from entry
            decimal_value = self.manual_var.get()
            
            # Convert to base36
            base36_value = self.convert_to_base36(decimal_value)
            
            if base36_value:
                # Add prefix
                prefix = self.prefix_var.get()
                result = prefix + base36_value
                
                # Display result
                self.result_var.set(result)
                
                # Copy result to clipboard
                pyperclip.copy(result)
                
                self.status_var.set(f"Converted {decimal_value} to {result} (copied to clipboard)")
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")

if __name__ == "__main__":
    # Check if pyperclip is installed
    try:
        import pyperclip
    except ImportError:
        print("The pyperclip module is required. Install it with 'pip install pyperclip'")
        exit(1)
    
    app = Base36Converter()
    app.mainloop()