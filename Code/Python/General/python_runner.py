import tkinter as tk
from tkinter import filedialog, messagebox, font
import subprocess
import os
import sys # Import sys module to check platform

class PythonAppRunner:
    def __init__(self, master):
        self.master = master
        master.title("Python App Runner")
        master.geometry("800x600") # Set an initial size
        master.configure(bg="#282C34") # Dark background

        # Define the custom font
        try:
            self.custom_font = font.Font(family="JetBrains Mono SemiBold", size=13)
        except tk.TclError:
            # Fallback font if JetBrains Mono is not available
            self.custom_font = font.Font(family="TkDefaultFont", size=13, weight="bold")
            messagebox.showwarning("Font Warning", "Font 'JetBrains Mono SemiBold' not found. Using default font.")

        self.apps_file = "apps_config.txt"
        self.app_entries = [] # To store references to app UI frames
        self.app_data = [] # To store app name and path in memory

        self.create_widgets()
        self.load_apps()

    def create_widgets(self):
        # Main frame for scrollable content
        self.main_frame = tk.Frame(self.master, bg="#282C34")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.main_frame, bg="#282C34", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#282C34")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Buttons at the bottom
        button_frame = tk.Frame(self.master, bg="#282C34")
        button_frame.pack(pady=10)

        # Add Application Button
        self.add_app_button = tk.Button(
            button_frame,
            text="Add New Application",
            command=self.add_new_app_entry,
            font=self.custom_font,
            bg="#61AFEF", # Blue
            fg="white",
            activebackground="#569CD6",
            activeforeground="white",
            bd=0,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.add_app_button.pack(side=tk.LEFT, padx=5)

        # Global Save Button
        self.global_save_button = tk.Button(
            button_frame,
            text="Save All Applications",
            command=self.save_apps,
            font=self.custom_font,
            bg="#C678DD", # Purple
            fg="white",
            activebackground="#A35CB8",
            activeforeground="white",
            bd=0,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.global_save_button.pack(side=tk.RIGHT, padx=5)


        # Style for buttons (optional, but makes them look better)
        self.master.option_add('*Button.Background', '#61AFEF')
        self.master.option_add('*Button.Foreground', 'white')
        self.master.option_add('*Button.Font', self.custom_font)
        self.master.option_add('*Button.Borderwidth', 0)
        self.master.option_add('*Button.Relief', tk.FLAT)

        self.master.option_add('*Entry.Background', '#3B4048') # Darker grey
        self.master.option_add('*Entry.Foreground', '#ABB2BF') # Light grey
        self.master.option_add('*Entry.Font', self.custom_font)
        self.master.option_add('*Entry.Borderwidth', 1)
        self.master.option_add('*Entry.Relief', tk.SOLID)
        self.master.option_add('*Entry.InsertBackground', 'white') # Cursor color

        self.master.option_add('*Label.Background', '#282C34')
        self.master.option_add('*Label.Foreground', '#ABB2BF')
        self.master.option_add('*Label.Font', self.custom_font)


    def add_app_ui_entry(self, app_name="", app_path=""):
        """Adds a new row of widgets for an application."""
        app_frame = tk.Frame(self.scrollable_frame, bg="#3B4048", bd=2, relief=tk.GROOVE, padx=10, pady=10)
        app_frame.pack(fill=tk.X, padx=5, pady=5)
        self.app_entries.append(app_frame)

        # Store app name and path as StringVar and attribute on the frame
        app_frame.name_var = tk.StringVar(value=app_name)
        app_frame.path_value = app_path # Store path directly as an attribute

        # App Name Label and Entry
        name_label = tk.Label(app_frame, text="App Name:", bg="#3B4048", fg="#ABB2BF", font=self.custom_font)
        name_label.grid(row=0, column=0, sticky="w", pady=2, padx=5)
        name_entry = tk.Entry(app_frame, width=30, bg="#3B4048", fg="#ABB2BF", font=self.custom_font, insertbackground='white', textvariable=app_frame.name_var)
        name_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=5)

        # Buttons in a single row
        button_row_frame = tk.Frame(app_frame, bg="#3B4048")
        button_row_frame.grid(row=0, column=2, padx=5, pady=2, sticky="e")

        # Browse Button
        browse_button = tk.Button(
            button_row_frame,
            text="Browse",
            command=lambda frame=app_frame: self.browse_file(frame),
            bg="#98C379", # Green
            fg="white",
            activebackground="#7B9E60",
            activeforeground="white",
            bd=0,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        browse_button.pack(side=tk.LEFT, padx=2)

        # Start Button
        start_button = tk.Button(
            button_row_frame,
            text="Start",
            command=lambda frame=app_frame: self.run_app(frame.path_value),
            bg="#61AFEF", # Blue
            fg="white",
            activebackground="#569CD6",
            activeforeground="white",
            bd=0,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        start_button.pack(side=tk.LEFT, padx=2)

        # Delete Button
        delete_button = tk.Button(
            button_row_frame,
            text="Delete",
            command=lambda frame=app_frame: self.delete_app_entry(frame),
            bg="#E06C75", # Red
            fg="white",
            activebackground="#B2555C",
            activeforeground="white",
            bd=0,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        delete_button.pack(side=tk.LEFT, padx=2)

        # Configure column weights for responsiveness
        app_frame.grid_columnconfigure(1, weight=1)


    def add_new_app_entry(self):
        """Adds a blank new application entry to the UI."""
        self.add_app_ui_entry()
        self.canvas.update_idletasks() # Update canvas scroll region immediately
        self.canvas.yview_moveto(1) # Scroll to bottom


    def delete_app_entry(self, app_frame_to_delete):
        """Deletes an application entry from the UI and internal data."""
        if messagebox.askyesno("Delete Application", "Are you sure you want to delete this application entry?"):
            app_frame_to_delete.destroy()
            self.app_entries.remove(app_frame_to_delete)
            self.save_apps() # Save changes immediately after deletion


    def browse_file(self, app_frame):
        """Opens a file dialog to select a Python file and updates the app_frame's path_value."""
        filepath = filedialog.askopenfilename(
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filepath:
            app_frame.path_value = filepath # Update the internal path value
            # Optionally, you could update the app name entry to show the filename
            # app_frame.name_var.set(os.path.basename(filepath))
            messagebox.showinfo("File Selected", f"Path for '{app_frame.name_var.get()}' set to: {filepath}")


    def run_app(self, filepath):
        """Runs the specified Python script without showing a console window,
        setting the current working directory to the script's directory."""
        if not filepath:
            messagebox.showerror("Error", "Please provide a file path to run.")
            return

        if not os.path.exists(filepath):
            messagebox.showerror("Error", f"File not found: {filepath}")
            return

        if not filepath.endswith(".py"):
            messagebox.showwarning("Warning", f"The file '{filepath}' does not seem to be a Python script (.py). Attempting to run anyway.")

        try:
            # Get the directory containing the script
            script_directory = os.path.dirname(filepath)
            # Get the script's filename
            script_filename = os.path.basename(filepath)

            # Determine creation flags based on OS
            creation_flags = 0
            if sys.platform.startswith('win'): # Check if OS is Windows
                # CREATE_NO_WINDOW prevents a console window from appearing
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            # Use subprocess.Popen to run the script without blocking the GUI
            # stdin, stdout, stderr are set to PIPE to prevent a console from opening
            # even if creation_flags is not fully supported or effective on a specific system/Python version.
            # The 'cwd' argument sets the current working directory for the subprocess.
            subprocess.Popen(
                [sys.executable, script_filename], # Run the script by its filename
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True, # Decode output as text
                creationflags=creation_flags,
                cwd=script_directory # Set the working directory for the subprocess
            )
            
            # Removed messagebox.showinfo("App Started", ...) as requested.
            # You could add logic here to monitor the process, read its output, etc.

        except FileNotFoundError:
            messagebox.showerror("Error", "Python executable not found. Make sure Python is installed and added to your system's PATH.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while trying to run the app: {e}")

    def load_apps(self):
        """Loads application data from the config file."""
        if not os.path.exists(self.apps_file):
            return

        with open(self.apps_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(":::")
                    if len(parts) == 2:
                        app_name, app_path = parts
                        self.app_data.append({"name": app_name, "path": app_path})
                        # Pass loaded data to add_app_ui_entry
                        self.add_app_ui_entry(app_name, app_path)
        self.canvas.update_idletasks() # Update canvas scroll region after loading

    def save_apps(self):
        """Saves current application data from UI to the config file."""
        self.app_data = [] # Clear existing data

        for app_frame in self.app_entries:
            name = app_frame.name_var.get().strip()
            path = app_frame.path_value.strip() # Get path from the attribute
            if name and path: # Only save if both name and path are provided
                self.app_data.append({"name": name, "path": path})

        with open(self.apps_file, "w", encoding="utf-8") as f:
            for app in self.app_data:
                f.write(f"{app['name']}:::{app['path']}\n")
        
        messagebox.showinfo("Saved", "Application configurations saved successfully!")

# Main part of the script
if __name__ == "__main__":
    root = tk.Tk()
    app = PythonAppRunner(root)
    root.mainloop()
