import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import math

# Main application class for the SVG editor
class SVGCutterApp:
    def __init__(self, master):
        self.master = master
        master.title("SVG Laser Cutter Editor")
        master.geometry("1000x700") # Set initial window size

        # List to store dictionaries of shape properties
        # Each dictionary will contain 'type' and 'properties'
        self.shapes = []

        self._create_widgets()
        self.redraw_canvas() # Initial drawing of the empty canvas

    def _create_widgets(self):
        # --- Left Panel: Controls ---
        control_frame = ttk.Frame(self.master, padding="10", relief=tk.RAISED, borderwidth=1)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control_frame, text="Shapes", font=("Inter", 12, "bold")).pack(pady=5)

        # Listbox to display the added shapes
        self.shape_listbox = tk.Listbox(control_frame, height=20, width=40, font=("Inter", 10), selectmode=tk.SINGLE)
        self.shape_listbox.pack(pady=5, fill=tk.BOTH, expand=True)
        # Bind an event to handle shape selection (optional)
        self.shape_listbox.bind("<<ListboxSelect>>", self._on_shape_select)

        # Frame for action buttons (Add, Edit, Remove)
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=10, fill=tk.X)

        ttk.Button(button_frame, text="Add Shape", command=self._add_shape_dialog).pack(side=tk.LEFT, expand=True, padx=2, ipadx=5, ipady=5)
        ttk.Button(button_frame, text="Edit Shape", command=self._edit_selected_shape).pack(side=tk.LEFT, expand=True, padx=2, ipadx=5, ipady=5)
        ttk.Button(button_frame, text="Remove Shape", command=self._remove_selected_shape).pack(side=tk.LEFT, expand=True, padx=2, ipady=5)

        # Button to save the current drawing to an SVG file
        ttk.Button(control_frame, text="Save SVG", command=self._save_svg).pack(pady=10, fill=tk.X, ipadx=5, ipady=5)

        # --- Right Panel: Canvas for drawing preview ---
        canvas_frame = ttk.Frame(self.master, padding="10", relief=tk.SUNKEN, borderwidth=1)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="white", relief=tk.GROOVE, borderwidth=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # Bind the <Configure> event to handle canvas resizing
        self.canvas.bind("<Configure>", self.redraw_canvas)

    def _on_shape_select(self, event):
        """
        Event handler for when a shape is selected in the Listbox.
        Currently, it just passes.
        """
        pass

    def redraw_canvas(self, event=None):
        """
        Redraws all shapes directly onto the Tkinter canvas.
        This method is called whenever shapes are added, edited, or removed.
        It also handles resizing by the user.
        """
        self.canvas.delete("all") # Clear previous content

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Add a small gap from the corner
        gap = 10 
        self.canvas.create_line(gap, gap, canvas_width - gap, gap, fill="gray")
        self.canvas.create_line(gap, gap, gap, canvas_height - gap, fill="gray")
        self.canvas.create_line(canvas_width - gap, gap, canvas_width - gap, canvas_height - gap, fill="gray")
        self.canvas.create_line(gap, canvas_height - gap, canvas_width - gap, canvas_height - gap, fill="gray")

        # Draw a grid with different line widths
        for i in range(0, int(canvas_width), 10):
            if i % 500 == 0:  # Bold line for 5 cm (50 mm)
                self.canvas.create_line(i + gap, gap, i + gap, canvas_height - gap, fill="black", width=2)
            elif i % 50 == 0:  # Medium line for 5 mm
                self.canvas.create_line(i + gap, gap, i + gap, canvas_height - gap, fill="black", width=1)
            elif i % 10 == 0:  # Thin line for 1 cm (10 mm)
                self.canvas.create_line(i + gap, gap, i + gap, canvas_height - gap, fill="lightgray", width=0.5)

        for i in range(0, int(canvas_height), 10):
            if i % 500 == 0:  # Bold line for 5 cm (50 mm)
                self.canvas.create_line(gap, i + gap, canvas_width - gap, i + gap, fill="black", width=2)
            elif i % 50 == 0:  # Medium line for 5 mm
                self.canvas.create_line(gap, i + gap, canvas_width - gap, i + gap, fill="black", width=1)
            elif i % 10 == 0:  # Thin line for 1 cm (10 mm)
                self.canvas.create_line(gap, i + gap, canvas_width - gap, i + gap, fill="lightgray", width=0.5)

        for shape_data in self.shapes:
            shape_type = shape_data['type']
            props = shape_data['properties']

            # Add the gap to the coordinates of each shape for visual clarity
            if shape_type == "line":
                self.canvas.create_line(props['x1'] + gap, props['y1'] + gap, props['x2'] + gap, props['y2'] + gap,
                                        fill="black", width=2)
            elif shape_type == "circle":
                # Tkinter's create_oval requires bounding box coordinates (x1, y1, x2, y2)
                x1 = props['cx'] - props['r'] + gap
                y1 = props['cy'] - props['r'] + gap
                x2 = props['cx'] + props['r'] + gap
                y2 = props['cy'] + props['r'] + gap
                self.canvas.create_oval(x1, y1, x2, y2, outline="black", width=2)
            elif shape_type == "polygon":
                # Tkinter's create_polygon takes a list of coordinates
                points = []
                for x, y in props['points']:
                    points.append(x + gap)
                    points.append(y + gap)
                self.canvas.create_polygon(points, outline="black", fill="", width=2)

    def _add_shape_dialog(self):
        """
        Opens a new dialog window for adding different types of shapes.
        """
        dialog = tk.Toplevel(self.master)
        dialog.title("Add Shape")
        dialog.transient(self.master) # Make dialog transient to the main window
        dialog.grab_set() # Make dialog modal

        shape_type_var = tk.StringVar(value="line") # Default shape type

        # Radio buttons for selecting shape type
        ttk.Radiobutton(dialog, text="Line", variable=shape_type_var, value="line", command=lambda: self._show_shape_inputs(dialog, shape_type_var.get())).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Radiobutton(dialog, text="Circle", variable=shape_type_var, value="circle", command=lambda: self._show_shape_inputs(dialog, shape_type_var.get())).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Radiobutton(dialog, text="Polygon", variable=shape_type_var, value="polygon", command=lambda: self._show_shape_inputs(dialog, shape_type_var.get())).pack(anchor=tk.W, padx=10, pady=5)

        # Frame to hold dynamic input fields for selected shape type
        input_frame = ttk.Frame(dialog)
        input_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        dialog.input_frame = input_frame # Store reference to clear content later

        self._show_shape_inputs(dialog, "line") # Show line inputs initially

        def add_shape_action():
            """
            Validates input, creates the shape properties dictionary, and adds it to the list.
            """
            shape_type = shape_type_var.get()
            try:
                shape_data = {"type": shape_type} # Store shape properties for editing/saving
                shape_name = ""

                if shape_type == "line":
                    x1 = float(dialog.entries["x1"].get())
                    y1 = float(dialog.entries["y1"].get())
                    x2 = float(dialog.entries["x2"].get())
                    y2 = float(dialog.entries["y2"].get())
                    shape_data.update({"properties": {"x1":x1, "y1":y1, "x2":x2, "y2":y2}})
                    shape_name = f"Line ({x1},{y1})-({x2},{y2})"
                elif shape_type == "circle":
                    cx = float(dialog.entries["cx"].get())
                    cy = float(dialog.entries["cy"].get())
                    r = float(dialog.entries["r"].get())
                    if r <= 0:
                        raise ValueError("Radius must be greater than 0.")
                    shape_data.update({"properties": {"cx":cx, "cy":cy, "r":r}})
                    shape_name = f"Circle ({cx},{cy}) R={r}"
                elif shape_type == "polygon":
                    points_str = dialog.entries["points"].get()
                    points_coords = []
                    parts = points_str.split(',')
                    # Validate polygon input format (even number of parts, at least 3 points = 6 parts)
                    if len(parts) % 2 != 0 or len(parts) < 6:
                        raise ValueError("Polygon points must be comma-separated x,y pairs (e.g., '10,10,20,30,40,20') and have at least 3 points.")
                    for i in range(0, len(parts), 2):
                        points_coords.append((float(parts[i]), float(parts[i+1])))
                    shape_data.update({"properties": {"points":points_coords}})
                    shape_name = f"Polygon with {len(points_coords)} points"

                # Add the new shape's data to our internal list
                self.shapes.append(shape_data)
                self.shape_listbox.insert(tk.END, shape_name) # Add to listbox
                self.redraw_canvas() # Update the canvas display
                dialog.destroy() # Close the dialog

            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid input: {e}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=dialog)

        ttk.Button(dialog, text="Add", command=add_shape_action).pack(pady=10, ipadx=5, ipady=5)
        self.master.wait_window(dialog) # Wait for dialog to close

    def _show_shape_inputs(self, dialog, shape_type):
        """
        Dynamically clears and displays appropriate input fields
        based on the selected shape type in the Add/Edit dialog.
        """
        # Clear any previously displayed input widgets
        for widget in dialog.input_frame.winfo_children():
            widget.destroy()
        dialog.entries = {} # Dictionary to easily access entry widgets

        if shape_type == "line":
            ttk.Label(dialog.input_frame, text="Point 1 (x, y):").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["x1"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["x1"].grid(row=0, column=1, padx=5, pady=2)
            dialog.entries["y1"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["y1"].grid(row=0, column=2, padx=5, pady=2)
            ttk.Label(dialog.input_frame, text="Point 2 (x, y):").grid(row=1, column=0, sticky=tk.W, pady=2)
            dialog.entries["x2"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["x2"].grid(row=1, column=1, padx=5, pady=2)
            dialog.entries["y2"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["y2"].grid(row=1, column=2, padx=5, pady=2)
        elif shape_type == "circle":
            ttk.Label(dialog.input_frame, text="Center (cx, cy):").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["cx"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["cx"].grid(row=0, column=1, padx=5, pady=2)
            dialog.entries["cy"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["cy"].grid(row=0, column=2, padx=5, pady=2)
            ttk.Label(dialog.input_frame, text="Radius (r):").grid(row=1, column=0, sticky=tk.W, pady=2)
            dialog.entries["r"] = ttk.Entry(dialog.input_frame, width=15); dialog.entries["r"].grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky=tk.EW)
        elif shape_type == "polygon":
            ttk.Label(dialog.input_frame, text="Points (x1,y1,x2,y2,...):").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["points"] = ttk.Entry(dialog.input_frame, width=50); dialog.entries["points"].grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky=tk.EW)

    def _edit_selected_shape(self):
        """
        Opens a dialog to edit the properties of the selected shape.
        """
        selected_indices = self.shape_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select a shape to edit.")
            return

        index = selected_indices[0] # Get the index of the selected shape
        shape_data = self.shapes[index] # Retrieve its data

        dialog = tk.Toplevel(self.master)
        dialog.title(f"Edit {shape_data['type'].capitalize()}")
        dialog.transient(self.master)
        dialog.grab_set()

        input_frame = ttk.Frame(dialog)
        input_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        dialog.entries = {}

        # Populate input fields with current shape properties
        props = shape_data["properties"]
        if shape_data["type"] == "line":
            ttk.Label(input_frame, text="Point 1 (x, y):").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["x1"] = ttk.Entry(input_frame, width=15); dialog.entries["x1"].grid(row=0, column=1, padx=5, pady=2); dialog.entries["x1"].insert(0, str(props["x1"]))
            dialog.entries["y1"] = ttk.Entry(input_frame, width=15); dialog.entries["y1"].grid(row=0, column=2, padx=5, pady=2); dialog.entries["y1"].insert(0, str(props["y1"]))
            ttk.Label(input_frame, text="Point 2 (x, y):").grid(row=1, column=0, sticky=tk.W, pady=2)
            dialog.entries["x2"] = ttk.Entry(input_frame, width=15); dialog.entries["x2"].grid(row=1, column=1, padx=5, pady=2); dialog.entries["x2"].insert(0, str(props["x2"]))
            dialog.entries["y2"] = ttk.Entry(input_frame, width=15); dialog.entries["y2"].grid(row=1, column=2, padx=5, pady=2); dialog.entries["y2"].insert(0, str(props["y2"]))
        elif shape_data["type"] == "circle":
            ttk.Label(input_frame, text="Center (cx, cy):").grid(row=0, column=0, sticky=tk.W, pady=2)
            dialog.entries["cx"] = ttk.Entry(input_frame, width=15); dialog.entries["cx"].grid(row=0, column=1, padx=5, pady=2); dialog.entries["cx"].insert(0, str(props["cx"]))
            dialog.entries["cy"] = ttk.Entry(input_frame, width=15); dialog.entries["cy"].grid(row=0, column=2, padx=5, pady=2); dialog.entries["cy"].insert(0, str(props["cy"]))
            ttk.Label(input_frame, text="Radius (r):").grid(row=1, column=0, sticky=tk.W, pady=2)
            dialog.entries["r"] = ttk.Entry(input_frame, width=15); dialog.entries["r"].grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky=tk.EW); dialog.entries["r"].insert(0, str(props["r"]))
        elif shape_data["type"] == "polygon":
            ttk.Label(input_frame, text="Points (x1,y1,x2,y2,...):").grid(row=0, column=0, sticky=tk.W, pady=2)
            # Convert list of point tuples to a comma-separated string for display
            points_str = ",".join(f"{x},{y}" for x, y in props["points"])
            dialog.entries["points"] = ttk.Entry(input_frame, width=50); dialog.entries["points"].grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky=tk.EW); dialog.entries["points"].insert(0, points_str)

        def update_shape_action():
            """
            Validates new input and updates the shape properties in the list.
            """
            try:
                new_properties = {"type": shape_data["type"]}
                shape_name = ""

                if shape_data["type"] == "line":
                    x1 = float(dialog.entries["x1"].get())
                    y1 = float(dialog.entries["y1"].get())
                    x2 = float(dialog.entries["x2"].get())
                    y2 = float(dialog.entries["y2"].get())
                    new_properties = {"x1":x1, "y1":y1, "x2":x2, "y2":y2}
                    shape_name = f"Line ({x1},{y1})-({x2},{y2})"
                elif shape_data["type"] == "circle":
                    cx = float(dialog.entries["cx"].get())
                    cy = float(dialog.entries["cy"].get())
                    r = float(dialog.entries["r"].get())
                    if r <= 0:
                        raise ValueError("Radius must be greater than 0.")
                    new_properties = {"cx":cx, "cy":cy, "r":r}
                    shape_name = f"Circle ({cx},{cy}) R={r}"
                elif shape_data["type"] == "polygon":
                    points_str = dialog.entries["points"].get()
                    points_coords = []
                    parts = points_str.split(',')
                    if len(parts) % 2 != 0 or len(parts) < 6:
                        raise ValueError("Polygon points must be comma-separated x,y pairs (e.g., '10,10,20,30,40,20') and have at least 3 points.")
                    for i in range(0, len(parts), 2):
                        points_coords.append((float(parts[i]), float(parts[i+1])))
                    new_properties = {"points":points_coords}
                    shape_name = f"Polygon with {len(points_coords)} points"

                # Update the selected shape's properties
                self.shapes[index]["properties"] = new_properties
                self.shape_listbox.delete(index) # Update the listbox entry
                self.shape_listbox.insert(index, shape_name)
                self.redraw_canvas() # Redraw the canvas with the updated shape
                dialog.destroy()

            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid input: {e}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=dialog)

        ttk.Button(dialog, text="Update", command=update_shape_action).pack(pady=10, ipadx=5, ipady=5)
        self.master.wait_window(dialog)

    def _remove_selected_shape(self):
        """
        Removes the selected shape from the list and updates the UI.
        """
        selected_indices = self.shape_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select a shape to remove.")
            return

        # Confirmation dialog before removal
        if messagebox.askyesno("Confirm Removal", "Are you sure you want to remove the selected shape?"):
            index = selected_indices[0]
            self.shapes.pop(index) # Remove from internal list
            self.shape_listbox.delete(index) # Remove from listbox
            self.redraw_canvas() # Redraw the canvas

    def _save_svg(self):
        """
        Prompts the user for a file path and saves the current drawing as an SVG file.
        This function now manually generates the SVG XML content with 'mm' units.
        """
        file_path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")],
            title="Save SVG As"
        )
        if file_path:
            try:
                # Standard conversion from pixels (96 DPI) to millimeters (25.4 mm per inch)
                PX_TO_MM = 25.4 / 96

                # Get the current canvas dimensions in pixels
                canvas_width_px = self.canvas.winfo_width()
                canvas_height_px = self.canvas.winfo_height()
                
                # Convert canvas dimensions to millimeters
                canvas_width_mm = canvas_width_px * PX_TO_MM
                canvas_height_mm = canvas_height_px * PX_TO_MM

                # Start the SVG XML content with mm units
                svg_content = f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
                svg_content += f'<svg width="{canvas_width_mm:.2f}mm" height="{canvas_height_mm:.2f}mm" viewBox="0 0 {canvas_width_px} {canvas_height_px}" xmlns="http://www.w3.org/2000/svg">\n'
                
                # Iterate through shapes and generate corresponding SVG tags
                for shape_data in self.shapes:
                    shape_type = shape_data['type']
                    props = shape_data['properties']

                    if shape_type == "line":
                        svg_content += f'  <line x1="{props["x1"]}" y1="{props["y1"]}" x2="{props["x2"]}" y2="{props["y2"]}" stroke="black" stroke-width="2" />\n'
                    elif shape_type == "circle":
                        svg_content += f'  <circle cx="{props["cx"]}" cy="{props["cy"]}" r="{props["r"]}" fill="none" stroke="black" stroke-width="2" />\n'
                    elif shape_type == "polygon":
                        points_str = " ".join(f"{x},{y}" for x, y in props['points'])
                        svg_content += f'  <polygon points="{points_str}" fill="none" stroke="black" stroke-width="2" />\n'

                # End the SVG XML content
                svg_content += '</svg>'

                with open(file_path, 'w') as f:
                    f.write(svg_content)
                
                messagebox.showinfo("Save SVG", f"SVG saved successfully to {file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save SVG: {e}")


# Main application entry point
if __name__ == "__main__":
    root = tk.Tk()
    # Apply a modern theme to the tkinter window
    style = ttk.Style()
    style.theme_use('clam') # 'clam', 'alt', 'default', 'classic'

    app = SVGCutterApp(root)
    root.mainloop()
