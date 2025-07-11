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
        master.geometry("800x750") # Adjusted window size after removing a row
        master.resizable(True, True) # Allow resizing
        self.entries = {}

        # Configure font
        self.default_font = tkFont.Font(family="Times New Roman", size=14)

        # Apply font to all widgets by default (optional, but good for consistency)
        master.option_add("*Font", self.default_font)

        # --- UI Elements ---

        # Main File
        self.create_label_and_entry("Main Python File (.py):", 0, "main_file_path")
        self.create_browse_button(self.browse_main_file, "Browse...", 0, 2)

        # Files/Folders to Bundle (--add-data)
        tk.Label(master, text="Files/Folders to Bundle (--add-data, SOURCE;DEST, comma-separated):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.add_data_entry = tk.Entry(master, width=60)
        self.add_data_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.add_data_entry.insert(0, "minify;minify,model_key_name.txt;.,uids.txt;.")

        # No Console Option
        self.no_console_var = tk.BooleanVar(value=True) # Default to True
        tk.Checkbutton(master, text="No Console Window (--noconsole)", variable=self.no_console_var).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # Auto-confirm Option
        self.noconfirm_var = tk.BooleanVar(value=True) # Default to True
        tk.Checkbutton(master, text="Auto-confirm (overwrite existing spec/build) (--noconfirm)", variable=self.noconfirm_var).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # Target Directory
        self.create_label_and_entry("Target Output Directory:", 4, "target_dir_path")
        self.create_browse_button(self.browse_target_dir, "Browse...", 4, 2)

        # Icon File
        self.create_label_and_entry("Icon File (.ico):", 5, "icon_file_path")
        self.create_browse_button(self.browse_icon_file, "Browse...", 5, 2)

        # Executable Name
        self.create_label_and_entry("Executable Name (without .exe):", 6, "executable_name")
        self.entries["executable_name"].insert(0, "main")  # Default name

        # Build Button
        self.build_button = tk.Button(master, text="Build App", command=self.start_build_thread, bg="#4CAF50", fg="white", activebackground="#45a049", relief=tk.RAISED, bd=3)
        self.build_button.grid(row=7, column=0, columnspan=3, pady=20)

        # Output Log
        tk.Label(master, text="PyInstaller Output:").grid(row=8, column=0, sticky="w", padx=10, pady=5)
        self.output_log = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=90, height=20, bg="#f0f0f0", fg="#333", relief=tk.SUNKEN, bd=2)
        self.output_log.grid(row=9, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        # Configure grid weights for resizing
        master.grid_rowconfigure(8, weight=1)
        master.grid_columnconfigure(1, weight=1)

        # Pre-fill entries
        self.entries["main_file_path"].insert(0, "D:/Workspace/LearnOrDie/Code/Python/ChanCouchBase/main.py")
        self.entries["target_dir_path"].insert(0, "D:/Workspace/LearnOrDie/Code/Python/Tools")

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

    def _read_stream(self, stream, callback):
        """Helper function to read a stream line by line and call a callback."""
        for line in stream:
            callback(line.strip())

    def build_app(self):
        """Constructs and runs the PyInstaller command, then copies files."""
        main_file = self.entries["main_file_path"].get().strip()
        target_dir = self.entries["target_dir_path"].get().strip()
        icon_file = self.entries["icon_file_path"].get().strip()
        no_console = self.no_console_var.get()
        noconfirm = self.noconfirm_var.get()
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

        main_file_dir = os.path.dirname(main_file)
        if not main_file_dir:
            main_file_dir = os.getcwd()

        os.makedirs(target_dir, exist_ok=True)

        pyinstaller_cmd_parts = ["pyinstaller"]

        if no_console:
            pyinstaller_cmd_parts.append("--noconsole")
            
        if noconfirm:
            pyinstaller_cmd_parts.append("--noconfirm")

        if icon_file:
            if not os.path.exists(icon_file):
                self.log_output(f"Warning: Icon file not found at '{icon_file}'. Skipping icon.")
            else:
                pyinstaller_cmd_parts.append(f'--icon="{icon_file}"')

        if add_data_str:
            data_pairs = [pair.strip() for pair in add_data_str.split(',') if pair.strip()]
            for pair in data_pairs:
                if ';' in pair:
                    pyinstaller_cmd_parts.append(f'--add-data "{pair}"')
                else:
                    self.log_output(f"Warning: Invalid --add-data format '{pair}'. Expected SOURCE;DEST. Skipping.")

        pyinstaller_cmd_parts.append(f'"{os.path.basename(main_file)}"')

        pyinstaller_cmd_str = " ".join(pyinstaller_cmd_parts)

        self.log_output(f"\nRunning PyInstaller command from directory: {main_file_dir}\n")
        self.log_output(f"Command: {pyinstaller_cmd_str}\n")

        process = None
        try:
            process = subprocess.Popen(
                pyinstaller_cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=main_file_dir
            )

            stdout_thread = threading.Thread(target=self._read_stream, args=(process.stdout, lambda msg: self.master.after(0, self.log_output, msg)))
            stderr_thread = threading.Thread(target=self._read_stream, args=(process.stderr, lambda msg: self.master.after(0, self.log_output, msg)))
            
            stdout_thread.start()
            stderr_thread.start()

            process.wait()

            stdout_thread.join()
            stderr_thread.join()

            if process.returncode == 0:
                self.master.after(0, self.log_output, "\nPyInstaller build successful!")
                self.master.after(0, self.copy_files_after_build, main_file, main_file_dir, target_dir, add_data_str)
            else:
                self.master.after(0, self.log_output, f"\nPyInstaller build failed with exit code {process.returncode}.")
                self.master.after(0, messagebox.showerror, "Build Failed", f"PyInstaller build failed with exit code {process.returncode}.")
                self.master.after(0, lambda: self.build_button.config(state=tk.NORMAL))

        except FileNotFoundError:
            self.master.after(0, self.log_output, "Error: PyInstaller not found. Please ensure it is installed and in your system's PATH.")
            self.master.after(0, messagebox.showerror, "Error", "PyInstaller not found. Please install it (`pip install pyinstaller`) or ensure it's in your PATH.")
            self.master.after(0, lambda: self.build_button.config(state=tk.NORMAL))
        except Exception as e:
            self.master.after(0, self.log_output, f"An unexpected error occurred during build: {e}")
            self.master.after(0, messagebox.showerror("Error", f"An unexpected error occurred during build: {e}"))
            self.master.after(0, lambda: self.build_button.config(state=tk.NORMAL))
        finally:
            if process and process.stdout:
                process.stdout.close()
            if process and process.stderr:
                process.stderr.close()

    def copy_files_after_build(self, main_file, main_file_dir, target_dir, add_data_str):
        """
        Copies the built executable and its associated dependencies to the target directory.
        For --onedir builds, it copies main.exe and specified --add-data items to target_dir,
        and moves _internal to target_dir/_internal.
        """
        try:
            main_file_name_without_ext = os.path.splitext(os.path.basename(main_file))[0]
            
            # This is the crucial fix: app_folder_in_dist should be relative to main_file_dir,
            # not potentially target_dir.
            dist_folder_path = os.path.join(main_file_dir, 'dist')
            app_folder_in_dist = os.path.join(dist_folder_path, main_file_name_without_ext)
            
            self.log_output(f"Received add_data_str in copy_files_after_build: '{add_data_str}'")
            self.log_output(f"Expected PyInstaller app folder (source) at: {app_folder_in_dist}")

            if not os.path.exists(app_folder_in_dist) or not os.path.isdir(app_folder_in_dist):
                self.log_output(f"Error: PyInstaller application folder '{main_file_name_without_ext}' not found or is not a directory inside '{dist_folder_path}'.")
                messagebox.showerror("Copy Error", "PyInstaller application folder not found. Build likely failed or output elsewhere.")
                return

            self.log_output(f"Contents of PyInstaller source folder '{app_folder_in_dist}': {os.listdir(app_folder_in_dist)}")

            # Clear the target directory before copying to ensure a clean state
            if os.path.exists(target_dir):
                self.log_output(f"Clearing existing contents of target directory: {target_dir}")
                # Ensure it's empty, but don't remove target_dir itself if it's the root of a drive or important
                for item in os.listdir(target_dir):
                    item_path = os.path.join(target_dir, item)
                    if os.path.isfile(item_path):
                        try:
                            os.remove(item_path)
                        except OSError as e:
                            self.log_output(f"Permission Error: Could not remove file '{item_path}': {e}. Please ensure no processes are using this file.")
                            messagebox.showerror("Permission Error", f"Could not remove file '{item_path}': {e}. Please ensure no processes are using this file and try again.")
                            return # Stop copy operation if clearing fails
                    elif os.path.isdir(item_path):
                        try:
                            shutil.rmtree(item_path)
                        except OSError as e:
                            self.log_output(f"Permission Error: Could not remove directory '{item_path}': {e}. Please ensure no processes are using files within this directory.")
                            messagebox.showerror("Permission Error", f"Could not remove directory '{item_path}': {e}. Please ensure no processes are using files within this directory and try again.")
                            return # Stop copy operation if clearing fails
            else:
                os.makedirs(target_dir) # Create if it doesn't exist

            # Copy main.exe to target_dir
            main_exe_filename = f"{main_file_name_without_ext}.exe"
            main_exe_source_path = os.path.join(app_folder_in_dist, main_exe_filename)
            main_exe_dest_path = os.path.join(target_dir, main_exe_filename)

            if os.path.exists(main_exe_source_path):
                shutil.copy2(main_exe_source_path, main_exe_dest_path)
                self.log_output(f"Copied main executable: '{main_exe_filename}' to '{target_dir}'")
            else:
                self.log_output(f"Warning: Main executable '{main_exe_filename}' not found in '{app_folder_in_dist}'.")

            # Copy _internal folder to target_dir/_internal
            internal_folder_source_path = os.path.join(app_folder_in_dist, "_internal")
            internal_folder_dest_path = os.path.join(target_dir, "_internal")

            if os.path.isdir(internal_folder_source_path):
                # shutil.copytree will create the destination directory if it doesn't exist
                shutil.copytree(internal_folder_source_path, internal_folder_dest_path)
                self.log_output(f"Copied '_internal' folder from '{internal_folder_source_path}' to '{internal_folder_dest_path}'")
            else:
                self.log_output(f"Warning: '_internal' folder not found at '{internal_folder_source_path}'. This is unusual for a PyInstaller build.")

            # Copy additional files specified in --add-data from <target_dir>/main/_internal into <target_dir>/main
            if add_data_str:
                data_pairs = [pair.strip() for pair in add_data_str.split(',') if pair.strip()]
                for pair in data_pairs:
                    if ';' in pair:
                        source, dest = pair.split(';', 1)
                        source_path = os.path.join(app_folder_in_dist, "_internal", source.strip())
                        dest_path = os.path.join(target_dir, dest.strip()) if dest != '.' else target_dir
                        self.log_output(f"Processing --add-data pair: SOURCE='{source_path}', DEST='{dest_path}'")
                        if os.path.exists(source_path):
                            if os.path.isdir(source_path):
                                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                                self.log_output(f"Copied directory '{source}' to '{dest}'")
                            else:
                                shutil.copy2(source_path, dest_path)
                                self.log_output(f"Copied file '{source}' to '{dest}'")
                        else:
                            self.log_output(f"Warning: Source '{source}' not found in '{app_folder_in_dist}'. Skipping.")
                    else:
                        self.log_output(f"Warning: Invalid --add-data format '{pair}'. Expected SOURCE;DEST. Skipping.")

            # Rename <target_dir>/main.exe to custom executable name if specified
            executable_name = self.entries["executable_name"].get().strip()
            if executable_name:
                if not executable_name.endswith('.exe'):
                    executable_name += '.exe'
                custom_exe_path = os.path.join(target_dir, executable_name)
                if os.path.exists(main_exe_dest_path):
                    os.rename(main_exe_dest_path, custom_exe_path)
                    self.log_output(f"Renamed main executable to '{executable_name}'")
                else:
                    self.log_output(f"Warning: Main executable '{main_exe_filename}' not found for renaming to '{executable_name}'.")

            # Copy file to C:/ProgramData/Microsoft/Windows/Start Menu/Programs for easy access
            # Need to run as admin to write to this location
            start_menu_path = f"C:/ProgramData/Microsoft/Windows/Start Menu/Programs"
            start_menu_app_path = os.path.join(start_menu_path, f"{executable_name}")
            self.log_output(f"Start menu app path: {start_menu_app_path}")
            if not os.path.exists(start_menu_app_path):
                shutil.copy2(custom_exe_path, start_menu_app_path)
                self.log_output(f"Copied '{custom_exe_path}' to '{start_menu_app_path}' for easy access.")
            else:
                self.log_output(f"Warning: Start menu shortcut '{start_menu_app_path}' already exists.")

            self.log_output("\nApplication built and files copied successfully to target directory!")
            self.log_output(f"Your application is located in: {target_dir}")
            messagebox.showinfo("Build Complete", f"Application built and files copied successfully!\nYour app is in: {target_dir}")
        except PermissionError as pe:
            self.log_output(f"Permission Error: Could not copy to Start Menu: {pe}. Please run the application as administrator.")
            messagebox.showerror("Permission Denied", "Cannot copy to Start Menu. Please run this PyInstaller GUI application as an administrator to perform this action.")
        except Exception as e:
            self.log_output(f"An error occurred during file copying: {e}")
            messagebox.showerror("Copy Error", f"An error occurred during file copying: {e}")
        finally:
            self.master.after(0, lambda: self.build_button.config(state=tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = PyInstallerGUI(root)
    root.mainloop()