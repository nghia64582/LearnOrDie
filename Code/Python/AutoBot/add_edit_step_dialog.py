# add_edit_step_dialog.py
# This file contains the dialog for adding or editing a single step.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Import necessary application components
from scenario_model import Step, STEP_TYPES

class AddEditStepDialog(tk.Toplevel):
    """
    A dialog window for adding or editing a single step.
    """
    def __init__(self, parent, title, step_id, callback, step=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x250")
        self.transient(parent)
        self.grab_set()
        
        self.callback = callback
        self.step_id = step_id
        self.step = step
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        main_frame = ttk.Frame(self, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(1, weight=1)
        
        # Step Name
        ttk.Label(main_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Step Type dropdown
        ttk.Label(main_frame, text="Type:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.type_var = tk.StringVar()
        self.type_dropdown = ttk.Combobox(main_frame, textvariable=self.type_var, values=STEP_TYPES, state="readonly")
        self.type_dropdown.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.type_dropdown.bind("<<ComboboxSelected>>", self.update_content_ui)
        
        # Dynamic content UI frame
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.content_frame.columnconfigure(1, weight=1)
        
        # Save and cancel buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        ttk.Button(button_frame, text="Save", command=self.save_step).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(button_frame, text="Cancel", command=self.destroy).grid(row=0, column=1, padx=5, sticky="ew")
        
        self.content_var = tk.StringVar()
        if self.step:
            self.name_var.set(self.step.name)
            self.type_var.set(self.step.step_type)
            self.update_content_ui()
            self.content_var.set(self.step.content)

    def update_content_ui(self, event=None):
        """
        Dynamically changes the UI for the step's content based on its type.
        """
        # Clear existing content widgets
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        selected_type = self.type_var.get()
        
        if selected_type in ["Wait for image", "Click image"]:
            ttk.Label(self.content_frame, text="Image Path:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
            self.content_entry = ttk.Entry(self.content_frame, textvariable=self.content_var)
            self.content_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
            ttk.Button(self.content_frame, text="Browse...", command=self.browse_image).grid(row=0, column=2, padx=5)
        elif selected_type in ["Type word", "Press button"]:
            ttk.Label(self.content_frame, text="Content:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
            self.content_entry = ttk.Entry(self.content_frame, textvariable=self.content_var)
            self.content_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=2)

    def browse_image(self):
        """
        Opens a file dialog to select an image file.
        """
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if file_path:
            self.content_var.set(file_path)

    def save_step(self):
        """
        Saves the step and calls the callback function.
        """
        name = self.name_var.get().strip()
        step_type = self.type_var.get()
        content = self.content_var.get().strip() if hasattr(self, 'content_var') else ""

        if not name or not step_type or not content:
            messagebox.showerror("Error", "All fields must be filled.", parent=self)
            return

        new_step = Step(step_id=self.step_id, name=name, step_type=step_type, content=content)
        self.callback(new_step)
        self.destroy()

