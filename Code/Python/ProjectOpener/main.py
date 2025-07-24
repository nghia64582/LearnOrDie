import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import subprocess
import os

# Define the file to store IDE and project data
DATA_FILE = "ide_project_data.json"

class IDEProjectLauncherApp:
    def __init__(self, master):
        self.master = master
        master.title("IDE Project Launcher")
        master.geometry("800x600")
        master.resizable(True, True)

        # Apply a modern theme
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam', 'alt', 'default', 'classic'

        # Initialize data structures
        self.ides = []
        self.projects = []
        self.current_ide_name = None

        # Load data from file on startup
        self._load_data()

        # --- UI Setup ---
        self._create_widgets()
        self._update_all_ui() # Populate lists and labels on startup

    def _create_widgets(self):
        # Main frames
        self.ide_frame = ttk.LabelFrame(self.master, text="IDE Management", padding="10")
        self.ide_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.current_ide_frame = ttk.Frame(self.master, padding="10")
        self.current_ide_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.project_frame = ttk.LabelFrame(self.master, text="Project Management", padding="10")
        self.project_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # --- IDE Management Widgets ---
        # Input for IDE Name
        ttk.Label(self.ide_frame, text="IDE Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.ide_name_entry = ttk.Entry(self.ide_frame, width=30)
        self.ide_name_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # Input for IDE Path
        ttk.Label(self.ide_frame, text="Executable Path:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.ide_path_entry = ttk.Entry(self.ide_frame, width=40)
        self.ide_path_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(self.ide_frame, text="Browse", command=self._browse_ide_path).grid(row=1, column=2, padx=5, pady=2)

        # Buttons for IDE actions
        ttk.Button(self.ide_frame, text="Add IDE", command=self._add_ide).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(self.ide_frame, text="Delete Selected IDE", command=self._delete_ide).grid(row=2, column=1, padx=5, pady=5)

        # Listbox for IDEs
        self.ide_listbox = tk.Listbox(self.ide_frame, height=5, selectmode=tk.SINGLE, exportselection=False)
        self.ide_listbox.grid(row=0, column=3, rowspan=3, padx=10, pady=2, sticky="nsew")
        self.ide_listbox.bind('<<ListboxSelect>>', self._on_ide_select) # Bind selection event

        ide_scrollbar = ttk.Scrollbar(self.ide_frame, orient="vertical", command=self.ide_listbox.yview)
        ide_scrollbar.grid(row=0, column=4, rowspan=3, sticky="ns")
        self.ide_listbox.config(yscrollcommand=ide_scrollbar.set)

        self.ide_frame.grid_columnconfigure(1, weight=1) # Allow IDE path entry to expand
        self.ide_frame.grid_columnconfigure(3, weight=1) # Allow IDE listbox to expand
        self.ide_frame.grid_rowconfigure(0, weight=1) # Allow rows to expand if needed

        # --- Current IDE Display ---
        ttk.Label(self.current_ide_frame, text="Current IDE:").pack(side=tk.LEFT, padx=5)
        self.current_ide_label = ttk.Label(self.current_ide_frame, text="None Selected", foreground="blue", font=("Helvetica", 10, "bold"))
        self.current_ide_label.pack(side=tk.LEFT, padx=5)

        # --- Project Management Widgets ---
        # Input for Project Name
        ttk.Label(self.project_frame, text="Project Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.project_name_entry = ttk.Entry(self.project_frame, width=30)
        self.project_name_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # Input for Project Path
        ttk.Label(self.project_frame, text="Folder Path:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.project_path_entry = ttk.Entry(self.project_frame, width=40)
        self.project_path_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(self.project_frame, text="Browse", command=self._browse_project_path).grid(row=1, column=2, padx=5, pady=2)

        # Buttons for Project actions
        ttk.Button(self.project_frame, text="Add Project", command=self._add_project).grid(row=2, column=0, padx=5, pady=5)
        # Removed the problematic "Delete Selected Project" button as it was not functional with current UI
        # ttk.Button(self.project_frame, text="Delete Selected Project", command=self._delete_project).grid(row=2, column=1, padx=5, pady=5)

        # Frame to hold project buttons (scrollable)
        self.project_buttons_frame = ttk.Frame(self.project_frame)
        self.project_buttons_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

        # Canvas and Scrollbar for project buttons
        self.project_canvas = tk.Canvas(self.project_buttons_frame, borderwidth=0, background="#f0f0f0")
        self.project_canvas.pack(side="left", fill="both", expand=True)

        self.project_scrollbar = ttk.Scrollbar(self.project_buttons_frame, orient="vertical", command=self.project_canvas.yview)
        self.project_scrollbar.pack(side="right", fill="y")

        self.project_canvas.configure(yscrollcommand=self.project_scrollbar.set)
        self.project_canvas.bind('<Configure>', lambda e: self.project_canvas.configure(scrollregion = self.project_canvas.bbox("all")))

        self.inner_project_frame = ttk.Frame(self.project_canvas)
        self.project_canvas.create_window((0, 0), window=self.inner_project_frame, anchor="nw")

        self.project_frame.grid_columnconfigure(1, weight=1) # Allow project path entry to expand
        self.project_frame.grid_rowconfigure(3, weight=1) # Allow project buttons frame to expand

    def _load_data(self):
        """Loads IDEs and projects from the data file."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    self.ides = data.get("ides", [])
                    self.projects = data.get("projects", [])
                    self.current_ide_name = data.get("current_ide_name")
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Could not decode data file. Starting with empty data.")
                self.ides = []
                self.projects = []
                self.current_ide_name = None
        else:
            self.ides = []
            self.projects = []
            self.current_ide_name = None

    def _save_data(self):
        """Saves current IDEs, projects, and selected IDE to the data file."""
        data = {
            "ides": self.ides,
            "projects": self.projects,
            "current_ide_name": self.current_ide_name
        }
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            messagebox.showerror("Error", f"Could not save data: {e}")

    def _update_all_ui(self):
        """Updates all UI elements (listboxes, labels, buttons)."""
        self._update_ide_listbox()
        self._update_current_ide_label()
        self._update_project_buttons()

    def _update_ide_listbox(self):
        """Populates the IDE listbox with current IDEs."""
        self.ide_listbox.delete(0, tk.END)
        for ide in self.ides:
            self.ide_listbox.insert(tk.END, ide["name"])

        # Select the current IDE in the listbox if it exists
        if self.current_ide_name:
            for i, ide in enumerate(self.ides):
                if ide["name"] == self.current_ide_name:
                    self.ide_listbox.selection_set(i)
                    self.ide_listbox.see(i) # Scroll to it if off-screen
                    break

    def _update_current_ide_label(self):
        """Updates the label showing the currently selected IDE."""
        if self.current_ide_name:
            self.current_ide_label.config(text=self.current_ide_name)
        else:
            self.current_ide_label.config(text="None Selected")

    def _update_project_buttons(self):
        """Clears and recreates project buttons in the scrollable frame."""
        # Clear existing buttons
        for widget in self.inner_project_frame.winfo_children():
            widget.destroy()

        if not self.projects:
            ttk.Label(self.inner_project_frame, text="No projects added yet.").pack(padx=10, pady=10)
            self.project_canvas.config(scrollregion=self.project_canvas.bbox("all"))
            return

        for i, project in enumerate(self.projects):
            project_frame_row = ttk.Frame(self.inner_project_frame)
            project_frame_row.pack(fill=tk.X, padx=5, pady=2)

            # Project Name Label
            ttk.Label(project_frame_row, text=project["name"], width=20, anchor="w").pack(side=tk.LEFT, padx=5)

            # Open Button
            ttk.Button(project_frame_row, text="Open", command=lambda p=project: self._open_project(p["path"])).pack(side=tk.LEFT, padx=5)

            # Delete Button (for individual project)
            ttk.Button(project_frame_row, text="Delete", command=lambda p=project: self._confirm_delete_project(p)).pack(side=tk.RIGHT, padx=5)

        # Update scroll region after adding buttons
        self.master.update_idletasks() # Ensure widgets are rendered before bbox calculation
        self.project_canvas.config(scrollregion=self.project_canvas.bbox("all"))


    def _browse_ide_path(self):
        """Opens a file dialog to select the IDE executable path."""
        file_path = filedialog.askopenfilename(
            title="Select IDE Executable",
            filetypes=[("Executables", "*.exe *.cmd *.sh *.bat"), ("All Files", "*.*")]
        )
        if file_path:
            self.ide_path_entry.delete(0, tk.END)
            self.ide_path_entry.insert(0, file_path)

    def _add_ide(self):
        """Adds a new IDE to the list."""
        name = self.ide_name_entry.get().strip()
        path = self.ide_path_entry.get().strip()

        if not name or not path:
            messagebox.showwarning("Input Error", "IDE Name and Path cannot be empty.")
            return
        if not os.path.exists(path):
            messagebox.showwarning("Path Error", "IDE Executable Path does not exist.")
            return
        if any(ide["name"] == name for ide in self.ides):
            messagebox.showwarning("Duplicate", f"An IDE named '{name}' already exists.")
            return

        self.ides.append({"name": name, "path": path})
        self._save_data()
        self._update_ide_listbox()
        self.ide_name_entry.delete(0, tk.END)
        self.ide_path_entry.delete(0, tk.END)

        # If this is the first IDE, set it as current
        if len(self.ides) == 1:
            self.current_ide_name = name
            self._update_current_ide_label()

    def _on_ide_select(self, event):
        """Handles selection of an IDE from the listbox."""
        selected_indices = self.ide_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            selected_ide_name = self.ide_listbox.get(index)
            self.current_ide_name = selected_ide_name
            self._save_data()
            self._update_current_ide_label()

    def _delete_ide(self):
        """Deletes the selected IDE from the list."""
        selected_indices = self.ide_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select an IDE to delete.")
            return

        index_to_delete = selected_indices[0]
        ide_name_to_delete = self.ides[index_to_delete]["name"]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete IDE: '{ide_name_to_delete}'?"):
            del self.ides[index_to_delete]
            if self.current_ide_name == ide_name_to_delete:
                self.current_ide_name = None # Clear current IDE if deleted

            self._save_data()
            self._update_ide_listbox()
            self._update_current_ide_label()

    def _browse_project_path(self):
        """Opens a directory dialog to select the project folder path."""
        folder_path = filedialog.askdirectory(title="Select Project Folder")
        if folder_path:
            self.project_path_entry.delete(0, tk.END)
            self.project_path_entry.insert(0, folder_path)

    def _add_project(self):
        """Adds a new project to the list."""
        name = self.project_name_entry.get().strip()
        path = self.project_path_entry.get().strip()

        if not name or not path:
            messagebox.showwarning("Input Error", "Project Name and Path cannot be empty.")
            return
        if not os.path.isdir(path):
            messagebox.showwarning("Path Error", "Project Folder Path does not exist or is not a directory.")
            return
        if any(project["name"] == name for project in self.projects):
            messagebox.showwarning("Duplicate", f"A project named '{name}' already exists.")
            return

        self.projects.append({"name": name, "path": path})
        self._save_data()
        self._update_project_buttons()
        self.project_name_entry.delete(0, tk.END)
        self.project_path_entry.delete(0, tk.END)

    def _confirm_delete_project(self, project_to_delete):
        """Confirms and deletes a project."""
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete project: '{project_to_delete['name']}'?"):
            self.projects = [p for p in self.projects if p != project_to_delete]
            self._save_data()
            self._update_project_buttons()

    def _open_project(self, project_path):
        """Opens the specified project with the current IDE."""
        if not self.current_ide_name:
            messagebox.showwarning("No IDE Selected", "Please select an IDE first.")
            return

        selected_ide = next((ide for ide in self.ides if ide["name"] == self.current_ide_name), None)
        if not selected_ide:
            messagebox.showerror("Error", f"Selected IDE '{self.current_ide_name}' not found. Please re-select or add it.")
            self.current_ide_name = None # Clear invalid selection
            self._update_current_ide_label()
            self._save_data()
            return

        ide_path = selected_ide["path"]

        if not os.path.exists(ide_path):
            messagebox.showerror("Error", f"IDE executable not found at: {ide_path}. Please update the path or delete the IDE.")
            return

        if not os.path.isdir(project_path):
            messagebox.showerror("Error", f"Project folder not found at: {project_path}. Please update the project path or delete the project.")
            return

        try:
            # Command to open the project with the IDE
            # For VS Code: code <path>
            # For IntelliJ IDEA: idea <path> (or idea64.exe <path> on Windows)
            # Use shell=True for Windows to correctly handle .cmd, .bat files
            # For cross-platform compatibility, it's often better to pass arguments as a list
            # and let subprocess handle quoting, but for simple `ide_exe path` it's usually fine.
            # Using shell=True for robustness with .cmd/.bat files on Windows.

            if os.name == 'nt': # Windows
                # For Windows, directly executing .exe, .cmd, .bat works well.
                # For VS Code, 'code.cmd' is often in PATH if installed via installer.
                # For IntelliJ, the 'idea' command is usually set up via Tools -> Create Command-line Launcher.
                # If the IDE path points to the actual executable, use that.
                # If it's a command like 'code' or 'idea' that's in the system PATH,
                # then just 'code' or 'idea' can be used.
                # Here, we assume the user provides the *full path* to the executable/command script.
                subprocess.Popen([ide_path, project_path], shell=True)
            else: # Unix-like (Linux, macOS)
                subprocess.Popen([ide_path, project_path])

        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch IDE: {e}")

# Main execution block
if __name__ == "__main__":
    root = tk.Tk()
    app = IDEProjectLauncherApp(root)
    root.mainloop()
