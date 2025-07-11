import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import font as tkFont
import subprocess
import os
import shutil
import threading # For running PyInstaller in a separate thread to keep UI responsive

class PyInstallerGUI:
    def __init__(self, master):
        self.master = master
        master.title("PyInstaller App Builder")
        master.geometry("800x750") # Slightly increased initial window size
        master.resizable(True, True) # Allow resizing
        self.entries = {}

        # Configure font
        self.default_font = tkFont.Font(family="Times New Roman", size=14)
        # Fallback if "Inter" is not available (commented out as per previous instruction)
        # if "Inter" not in tkFont.families():
        #     self.default_font = tkFont.Font(family="TkDefaultFont", size=14)
        #     messagebox.showwarning("Font Warning", "The 'Inter' font was not found. Using default Tkinter font.")

        # Apply font to all widgets by default (optional, but good for consistency)
        master.option_add("*Font", self.default_font)

        # --- UI Elements ---

        # Main File
        self.create_label_and_entry("Main Python File (.py):", 0, "main_file_path")
        self.create_browse_button(self.browse_main_file, "Browse...", 0, 2)

        # External Files/Folders (for external copying after build)
        # These are files/folders that your *built app* might need at runtime,
        # but are NOT bundled by PyInstaller. They will be copied alongside
        # your .exe to the target directory.
        tk.Label(master, text="External Files/Folders to Copy (comma-separated paths):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.external_copy_files_entry = tk.Entry(master, width=60)
        self.external_copy_files_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # Files/Folders to Bundle (--add-data)
        # These are files/folders that PyInstaller will try to bundle *into*
        # your executable or its accompanying directory. Use SOURCE;DEST format.
        tk.Label(master, text="Files/Folders to Bundle (--add-data, SOURCE;DEST, comma-separated):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.add_data_entry = tk.Entry(master, width=60)
        self.add_data_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        # Pre-fill with the user's example
        self.add_data_entry.insert(0, "minify;minify,model_key_name.txt;.,uids.txt;.")


        # No Console Option
        self.no_console_var = tk.BooleanVar()
        tk.Checkbutton(master, text="No Console Window (--noconsole)", variable=self.no_console_var).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # Target Directory
        self.create_label_and_entry("Target Output Directory:", 4, "target_dir_path")
        self.create_browse_button(self.browse_target_dir, "Browse...", 4, 2)

        # Icon File
        self.create_label_and_entry("Icon File (.ico):", 5, "icon_file_path")
        self.create_browse_button(self.browse_icon_file, "Browse...", 5, 2)

        # Build Button
        self.build_button = tk.Button(master, text="Build App", command=self.start_build_thread, bg="#4CAF50", fg="white", activebackground="#45a049", relief=tk.RAISED, bd=3)
        self.build_button.grid(row=6, column=0, columnspan=3, pady=20)

        # Output Log
        tk.Label(master, text="PyInstaller Output:").grid(row=7, column=0, sticky="w", padx=10, pady=5)
        self.output_log = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=90, height=20, bg="#f0f0f0", fg="#333", relief=tk.SUNKEN, bd=2)
        self.output_log.grid(row=8, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        # Configure grid weights for resizing
        master.grid_rowconfigure(8, weight=1)
        master.grid_columnconfigure(1, weight=1)

        # Store entry widgets for easy access (already defined above init)
        
    def create_label_and_entry(self, label_text, row, entry_name):
        """Helper to create a label and an entry field."""
        tk.Label(self.master, text=label_text).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        entry = tk.Entry(self.master, width=60)
        entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        self.entries[entry_name] = entry

    def create_browse_button(self, command, text, row, column):
        """Helper to create a browse button."""
        tk.Button(self.master, text=text, command=command, relief=tk.RAISED, bd=2).grid(row=row, column=column, padx=5, pady=5)

    def browse_main_file(self):
        """Opens a file dialog to select the main Python script."""
        file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if file_path:
            self.entries["main_file_path"].delete(0, tk.END)
            self.entries["main_file_path"].insert(0, file_path)

    def browse_target_dir(self):
        """Opens a directory dialog to select the output directory."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.entries["target_dir_path"].delete(0, tk.END)
            self.entries["target_dir_path"].insert(0, dir_path)

    def browse_icon_file(self):
        """Opens a file dialog to select the icon file."""
        file_path = filedialog.askopenfilename(filetypes=[("Icon files", "*.ico"), ("All files", "*.*")])
        if file_path:
            self.entries["icon_file_path"].delete(0, tk.END)
            self.entries["icon_file_path"].insert(0, file_path)

    def log_output(self, message):
        """Appends a message to the output log."""
        self.output_log.insert(tk.END, message + "\n")
        self.output_log.see(tk.END) # Scroll to the end

    def start_build_thread(self):
        """Starts the build process in a separate thread to keep the UI responsive."""
        self.build_button.config(state=tk.DISABLED) # Disable button during build
        self.output_log.delete(1.0, tk.END) # Clear previous output
        self.log_output("Build process started...")
        build_thread = threading.Thread(target=self.build_app)
        build_thread.start()

    def build_app(self):
        """Constructs and runs the PyInstaller command, then copies files."""
        main_file = self.entries["main_file_path"].get().strip()
        target_dir = self.entries["target_dir_path"].get().strip()
        icon_file = self.entries["icon_file_path"].get().strip()
        no_console = self.no_console_var.get()
        external_copy_files_str = self.external_copy_files_entry.get().strip()
        add_data_str = self.add_data_entry.get().strip()

        if not main_file:
            self.log_output("Error: Main Python File is required.")
            messagebox.showerror("Error", "Main Python File is required.")
            self.build_button.config(state=tk.NORMAL)
            return
        if not target_dir:
            self.log_output("Error: Target Output Directory is required.")
            messagebox.showerror("Error", "Target Output Directory is required.")
            self.build_button.config(state=tk.NORMAL)
            return

        # Get the directory of the main Python file to set as CWD for PyInstaller
        main_file_dir = os.path.dirname(main_file)
        if not main_file_dir: # If main_file is just a filename, assume current directory
            main_file_dir = os.getcwd()

        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)

        pyinstaller_cmd = ["pyinstaller", "--onefile"]

        if no_console:
            pyinstaller_cmd.append("--noconsole")

        if icon_file:
            if not os.path.exists(icon_file):
                self.log_output(f"Warning: Icon file not found at '{icon_file}'. Skipping icon.")
            else:
                pyinstaller_cmd.append(f"--icon={icon_file}")

        # Add --add-data arguments
        if add_data_str:
            data_pairs = [pair.strip() for pair in add_data_str.split(',') if pair.strip()]
            for pair in data_pairs:
                if ';' in pair:
                    pyinstaller_cmd.append(f"--add-data={pair}")
                else:
                    self.log_output(f"Warning: Invalid --add-data format '{pair}'. Expected SOURCE;DEST. Skipping.")

        # PyInstaller's --distpath specifies where the final executable goes.
        # PyInstaller creates a 'dist' folder inside the CWD or --distpath.
        # So, we'll set --distpath to a temporary location and then move the exe.
        # This prevents PyInstaller from creating 'dist' directly in the user's target_dir,
        # which might not be what they want if they just want the exe and external files.
        temp_build_dir = os.path.join(main_file_dir, "pyinstaller_build_temp")
        os.makedirs(temp_build_dir, exist_ok=True)
        pyinstaller_cmd.append(f"--distpath={temp_build_dir}")

        # Add the main script (use only the basename if CWD is set to its directory)
        pyinstaller_cmd.append(os.path.basename(main_file))

        self.log_output(f"\nRunning PyInstaller command from directory: {main_file_dir}\n")
        self.log_output(f"Command: {' '.join(pyinstaller_cmd)}\n")

        try:
            # Run PyInstaller with cwd set to the main file's directory
            process = subprocess.Popen(
                pyinstaller_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, # Decode output as text
                encoding='utf-8',
                errors='replace', # Handle decoding errors
                cwd=main_file_dir # Set the current working directory for the subprocess
            )

            # Stream output to the log
            for line in process.stdout:
                self.master.after(0, self.log_output, line.strip()) # Update UI in main thread
            for line in process.stderr:
                self.master.after(0, self.log_output, line.strip())

            process.wait() # Wait for PyInstaller to complete

            if process.returncode == 0:
                self.master.after(0, self.log_output, "\nPyInstaller build successful!")
                self.master.after(0, self.copy_files_after_build, main_file, temp_build_dir, target_dir, external_copy_files_str)
            else:
                self.master.after(0, self.log_output, f"\nPyInstaller build failed with exit code {process.returncode}.")
                self.master.after(0, messagebox.showerror, "Build Failed", f"PyInstaller build failed with exit code {process.returncode}.")

        except FileNotFoundError:
            self.master.after(0, self.log_output, "Error: PyInstaller not found. Please ensure it is installed and in your system's PATH.")
            self.master.after(0, messagebox.showerror, "Error", "PyInstaller not found. Please install it (`pip install pyinstaller`) or ensure it's in your PATH.")
        except Exception as e:
            self.master.after(0, self.log_output, f"An unexpected error occurred during build: {e}")
            self.master.after(0, messagebox.showerror, "Error", f"An unexpected error occurred during build: {e}")
        finally:
            self.master.after(0, self.build_button.config, state=tk.NORMAL) # Re-enable button

    def copy_files_after_build(self, main_file, temp_build_dir, target_dir, external_copy_files_str):
        """Copies the built executable and additional files/folders to the target directory."""
        try:
            main_file_name_without_ext = os.path.splitext(os.path.basename(main_file))[0]
            # For --onefile, the executable is directly in the dist folder
            built_exe_path = os.path.join(temp_build_dir, f"{main_file_name_without_ext}.exe")

            if not os.path.exists(built_exe_path):
                self.log_output(f"Error: Built executable not found at {built_exe_path}. PyInstaller might have failed or created it elsewhere.")
                messagebox.showerror("Copy Error", "Built executable not found. Check PyInstaller output.")
                return

            # Copy the main .exe
            final_exe_path = os.path.join(target_dir, os.path.basename(built_exe_path))
            shutil.copy2(built_exe_path, final_exe_path)
            self.log_output(f"Copied main executable to: {final_exe_path}")

            # Copy external files/folders
            if external_copy_files_str:
                files_to_copy = [f.strip() for f in external_copy_files_str.split(',') if f.strip()]
                for item_path in files_to_copy:
                    if not os.path.exists(item_path):
                        self.log_output(f"Warning: External file/folder not found: '{item_path}'. Skipping.")
                        continue

                    dest_path = os.path.join(target_dir, os.path.basename(item_path))
                    try:
                        if os.path.isfile(item_path):
                            shutil.copy2(item_path, dest_path)
                            self.log_output(f"Copied file: '{item_path}' to '{dest_path}'")
                        elif os.path.isdir(item_path):
                            # Remove existing directory at destination if it exists to avoid errors
                            if os.path.exists(dest_path):
                                shutil.rmtree(dest_path)
                            shutil.copytree(item_path, dest_path)
                            self.log_output(f"Copied folder: '{item_path}' to '{dest_path}'")
                        else:
                            self.log_output(f"Warning: '{item_path}' is neither a file nor a directory. Skipping.")
                    except Exception as copy_error:
                        self.log_output(f"Error copying '{item_path}': {copy_error}")

            self.log_output("\nAll specified files/folders copied successfully!")
            messagebox.showinfo("Build Complete", "Application built and files copied successfully!")

        except Exception as e:
            self.log_output(f"An error occurred during file copying: {e}")
            messagebox.showerror("Copy Error", f"An error occurred during file copying: {e}")
        finally:
            # Clean up temporary PyInstaller build directory
            if os.path.exists(temp_build_dir):
                try:
                    shutil.rmtree(temp_build_dir)
                    self.log_output(f"Cleaned up temporary build directory: {temp_build_dir}")
                except Exception as clean_error:
                    self.log_output(f"Error cleaning up temporary build directory: {clean_error}")

# Main application setup
if __name__ == "__main__":
    root = tk.Tk()
    app = PyInstallerGUI(root)
    root.mainloop()
