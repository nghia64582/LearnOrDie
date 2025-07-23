import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import shutil # For deleting files/folders

class FileFolderApp:
    def __init__(self, master):
        self.master = master
        master.title("File and Folder Explorer")
        master.geometry("800x600")
        master.resizable(True, True)
        master.configure(bg="#e0e0e0") # Light grey background for the main window

        self.current_directory = os.getcwd() # Start in current working directory

        # --- Top Frame: Path Entry and Navigation Buttons ---
        self.top_frame = tk.Frame(master, padx=15, pady=15, bg="#f5f5f5", relief=tk.RAISED, bd=2)
        self.top_frame.pack(fill=tk.X, pady=(10, 5), padx=10)

        # Updated font to "Times New Roman", size 12
        self.path_label = tk.Label(self.top_frame, text="Current Path:", font=("JetBrains Mono", 12, "bold"), bg="#f5f5f5", fg="#333333")
        self.path_label.pack(side=tk.LEFT, padx=(0, 10))

        # Updated font to "Times New Roman", size 12
        self.path_entry = tk.Entry(self.top_frame, width=60, font=("JetBrains Mono", 12), bd=2, relief=tk.SUNKEN, bg="white", fg="#333333")
        self.path_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 15))
        self.path_entry.insert(0, self.current_directory)
        self.path_entry.bind("<Return>", self.go_to_path_event) # Bind Enter key

        # Updated font to "Times New Roman", size 12
        self.go_button = tk.Button(self.top_frame, text="Go", command=self.go_to_path, font=("JetBrains Mono", 12, "bold"), bg="#4CAF50", fg="white", relief=tk.RAISED, bd=2, activebackground="#45a049", cursor="hand2")
        self.go_button.pack(side=tk.LEFT, padx=(0, 8))

        # Updated font to "Times New Roman", size 12
        self.back_button = tk.Button(self.top_frame, text="Back", command=self.go_back, font=("JetBrains Mono", 12, "bold"), bg="#2196F3", fg="white", relief=tk.RAISED, bd=2, activebackground="#0b7dda", cursor="hand2")
        self.back_button.pack(side=tk.LEFT, padx=(0, 0))

        # --- Separator ---
        ttk.Separator(master, orient='horizontal').pack(fill='x', pady=10, padx=10)

        # --- Content Frame: Scrollable Area for Files/Folders ---
        self.content_frame = tk.Frame(master, bg="#ffffff", bd=2, relief=tk.SUNKEN)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(self.content_frame, bg="#ffffff", highlightthickness=0) # Remove default canvas border
        self.scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")

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

        # --- Table Headers ---
        self.header_frame = tk.Frame(self.scrollable_frame, bg="#e0e0e0", bd=1, relief=tk.SOLID)
        self.header_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 5))

        # Updated font to "Times New Roman", size 12
        tk.Label(self.header_frame, text="Name", font=("JetBrains Mono", 12, "bold"), width=30, anchor="w", bg="#e0e0e0", fg="#333333", padx=2, pady=0, bd=1, relief=tk.SOLID).grid(row=0, column=0, sticky="w")
        # Updated font to "Times New Roman", size 12
        tk.Label(self.header_frame, text="Size", font=("JetBrains Mono", 12, "bold"), width=10, anchor="w", bg="#e0e0e0", fg="#333333", padx=2, pady=0, bd=1, relief=tk.SOLID).grid(row=0, column=1, sticky="w")
        # Updated font to "Times New Roman", size 12
        tk.Label(self.header_frame, text="Action", font=("JetBrains Mono", 12, "bold"), width=10, anchor="w", bg="#e0e0e0", fg="#333333", padx=2, pady=0, bd=1, relief=tk.SOLID).grid(row=0, column=2, sticky="w")
        # Updated font to "Times New Roman", size 12
        tk.Label(self.header_frame, text="Delete", font=("JetBrains Mono", 12, "bold"), width=10, anchor="w", bg="#e0e0e0", fg="#333333", padx=2, pady=0, bd=1, relief=tk.SOLID).grid(row=0, column=3, sticky="w")

        self.update_display()

    def get_folder_info(self, folder_path):
        """
        Calculates the total size and file count of a given folder,
        optimized for large numbers of files/directories.
        """
        total_size = 0
        file_count = 0
        try:
            for entry in os.scandir(folder_path):
                if entry.is_file():
                    total_size += entry.stat().st_size
                    file_count += 1
                elif entry.is_dir():
                    # Recursively call for subdirectories
                    subdir_size, subdir_count = self.get_folder_info(entry.path)
                    total_size += subdir_size
                    file_count += subdir_count
            return total_size, file_count
        except OSError as e:
            # Handle permission errors or other OS-related issues
            print(f"Error accessing {folder_path}: {e}")
            return 0, 0

    def get_size_readable(self, size_in_bytes):
        """Converts bytes to a human-readable format (KB, MB, GB, etc.)."""
        if size_in_bytes == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} PB" # Fallback for extremely large sizes

    def clear_display(self):
        """Clears all widgets from the scrollable frame except headers."""
        for widget in self.scrollable_frame.winfo_children():
            if widget != self.header_frame: # Don't destroy the header frame
                widget.destroy()

    def update_display(self):
        """Updates the display with files and folders of the current directory."""
        self.clear_display()
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, self.current_directory)

        row_num = 1 # Start content from row 1 (after headers)

        try:
            # Get directories first, then files, sorted alphabetically
            self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            entries = sorted(os.scandir(self.current_directory), key=lambda e: e.name.lower())
            folders = [e for e in entries if e.is_dir()]
            files = [e for e in entries if e.is_file()]

            for entry in folders + files:
                name = entry.name
                full_path = entry.path
                size_str = ""
                is_dir = entry.is_dir()

                if is_dir:
                    # Calculate folder size in a separate thread for large folders
                    # For simplicity, doing it directly here, but for very large
                    # directories, this might cause the UI to freeze.
                    # A more advanced version would use threading.
                    size, _ = self.get_folder_info(full_path)
                    size_str = self.get_size_readable(size)
                else:
                    try:
                        size_str = self.get_size_readable(os.path.getsize(full_path))
                    except OSError:
                        size_str = "N/A" # Handle cases where file size cannot be accessed

                # Name Label - Updated font to "Times New Roman", size 12
                tk.Label(self.scrollable_frame, text=name, anchor="w", font=("JetBrains Mono", 12, "bold"), width=30, bg="#6ab370", fg="#333333", padx=2, pady=8, bd=1, relief=tk.SOLID).grid(row=row_num, column=0, sticky="ew")
                # Size Label - Updated font to "Times New Roman", size 12
                tk.Label(self.scrollable_frame, text=size_str, anchor="w", font=("JetBrains Mono", 12, "bold"), width=10, bg="#ffffff", fg="#333333", padx=2, pady=8, bd=1, relief=tk.SOLID).grid(row=row_num, column=1, sticky="ew")

                # Action Button (Open for folders)
                # show border
                if is_dir:
                    # Updated font to "Times New Roman", size 12
                    open_button = tk.Button(self.scrollable_frame, text="Open", command=lambda p=full_path: self.open_item(p), font=("JetBrains Mono", 12, "bold"), width=10, bg="#8BC34A", fg="white", relief=tk.RAISED, bd=1, activebackground="#7cb342", cursor="hand2")
                    open_button.grid(row=row_num, column=2, padx=2, pady=8, sticky="ew")
                else:
                    # Updated font to "Times New Roman", size 12
                    tk.Label(self.scrollable_frame, text="file", font=("JetBrains Mono", 12, "bold"), width=10, bg="#ffffff", padx=2, pady=8, bd=1, relief=tk.SOLID).grid(row=row_num, column=2, sticky="ew") # Placeholder for files

                # Delete Button - Updated font to "Times New Roman", size 12
                delete_button = tk.Button(self.scrollable_frame, text="Delete", command=lambda p=full_path, i_d=is_dir: self.delete_item(p, i_d), font=("JetBrains Mono", 12, "bold"), width=10, bg="#F44336", fg="#f3d0d0", relief=tk.RAISED, bd=1, activebackground="#e53935", cursor="hand2")
                delete_button.grid(row=row_num, column=3, padx=2, pady=8, sticky="ew")

                row_num += 1

            # Configure column weights for resizing
            self.scrollable_frame.grid_columnconfigure(0, weight=4) # Name
            self.scrollable_frame.grid_columnconfigure(1, weight=1) # Size
            self.scrollable_frame.grid_columnconfigure(2, weight=1) # Action
            self.scrollable_frame.grid_columnconfigure(3, weight=1) # Delete
            # add scrolling binding
            self.canvas.bind_all("<MouseWheel>", lambda event: self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")) # For Windows/Linux
            # reset scrolling after updating display
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))


        except FileNotFoundError:
            messagebox.showerror("Error", f"Directory not found: {self.current_directory}")
            self.current_directory = os.getcwd() # Reset to a known good path
            self.update_display() # Re-render with the default path
        except PermissionError:
            messagebox.showerror("Error", f"Permission denied to access: {self.current_directory}")
            # If permission is denied, try to go to the parent directory
            parent_dir = os.path.dirname(self.current_directory)
            if parent_dir != self.current_directory: # Ensure we don't loop if at root
                self.current_directory = parent_dir
                self.update_display()
            else:
                self.current_directory = os.getcwd() # Reset to a known good path
                self.update_display()
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.current_directory = os.getcwd() # Reset to a known good path
            self.update_display()

    def open_item(self, path):
        """Opens a folder."""
        if os.path.isdir(path):
            self.current_directory = path
            self.update_display()
        else:
            messagebox.showinfo("Info", "This is a file, not a folder.")

    def delete_item(self, path, is_dir):
        """Deletes a file or folder."""
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete:\n{path}?"):
            try:
                if is_dir:
                    shutil.rmtree(path) # Deletes directory and all its contents
                else:
                    os.remove(path) # Deletes file
                messagebox.showinfo("Success", f"Deleted: {os.path.basename(path)}")
                self.update_display() # Refresh display after deletion
            except OSError as e:
                messagebox.showerror("Error", f"Could not delete {os.path.basename(path)}: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred during deletion: {e}")

    def go_to_path_event(self, event=None):
        """Handles 'Go' button click or Enter key press."""
        self.go_to_path()

    def go_to_path(self):
        """Changes the current directory to the path entered in the entry field."""
        new_path = self.path_entry.get()
        if os.path.isdir(new_path):
            self.current_directory = new_path
            self.update_display()
        else:
            messagebox.showerror("Invalid Path", "The entered path is not a valid directory.")
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, self.current_directory) # Revert to current valid path

    def go_back(self):
        """Navigates to the parent directory."""
        parent_directory = os.path.dirname(self.current_directory)
        if parent_directory != self.current_directory: # Check to prevent going above root
            self.current_directory = parent_directory
            self.update_display()
        else:
            messagebox.showinfo("Navigation", "You are already at the root of the drive/filesystem.")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileFolderApp(root)
    root.mainloop()
