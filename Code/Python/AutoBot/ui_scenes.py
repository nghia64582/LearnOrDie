# ui_scenes.py
# This file contains the Tkinter UI classes for the application's scenes.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Import models and manager
from scenario_model import Scenario, Step, STEP_TYPES
from scenario_manager import ScenarioManager

class AllScenarios(ttk.Frame):
    """
    Scene 1: Displays a list of all available scenarios.
    """
    def __init__(self, parent, controller, scenario_manager):
        super().__init__(parent)
        self.controller = controller
        self.scenario_manager = scenario_manager
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Main frame for the content
        main_frame = ttk.Frame(self, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="All Scenarios", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        # Treeview to display scenarios
        self.scenarios_tree = ttk.Treeview(main_frame, columns=("Description", "Steps"), show="headings", height=10)
        self.scenarios_tree.heading("Description", text="Description")
        self.scenarios_tree.heading("Steps", text="Steps Count")
        
        self.scenarios_tree.column("Description", width=300)
        self.scenarios_tree.column("Steps", width=100, anchor=tk.CENTER)
        self.scenarios_tree.grid(row=1, column=0, sticky="nsew")

        # Scrollbar for the treeview
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.scenarios_tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.scenarios_tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind events
        self.scenarios_tree.bind("<Double-1>", self.on_scenario_select)
        self.scenarios_tree.bind("<<TreeviewSelect>>", self.on_treeview_select)
        
        # Action buttons frame
        button_frame = ttk.Frame(main_frame, padding="10 0")
        button_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        
        self.add_button = ttk.Button(button_frame, text="Add New Scenario", command=self.add_new_scenario)
        self.add_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.edit_button = ttk.Button(button_frame, text="Edit Scenario", command=self.edit_scenario, state=tk.DISABLED)
        self.edit_button.grid(row=0, column=1, padx=5, sticky="ew")

        self.delete_button = ttk.Button(button_frame, text="Delete Scenario", command=self.delete_scenario, state=tk.DISABLED)
        self.delete_button.grid(row=0, column=2, padx=5, sticky="ew")

    def show(self, data=None):
        """
        Called when this scene is displayed. Loads and populates the scenario list.
        The 'data' parameter is accepted for consistency with other scenes but is not used.
        """
        self.populate_scenario_list()
        self.edit_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)

    def populate_scenario_list(self):
        """
        Clears the current list and re-populates it with scenarios from the manager.
        """
        for item in self.scenarios_tree.get_children():
            self.scenarios_tree.delete(item)
        
        scenarios = self.scenario_manager.load_scenarios()
        for scenario in scenarios:
            self.scenarios_tree.insert("", "end", iid=scenario.name, text=scenario.name, 
                                        values=(scenario.description, len(scenario.steps)))

    def on_treeview_select(self, event):
        """
        Enables the edit/delete buttons when a scenario is selected.
        """
        if self.scenarios_tree.selection():
            self.edit_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
        else:
            self.edit_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)

    def on_scenario_select(self, event):
        """
        Opens the details page for the selected scenario.
        """
        selected_item = self.scenarios_tree.focus()
        if selected_item:
            scenario_name = self.scenarios_tree.item(selected_item, "text")
            scenario = self.scenario_manager.load_scenario(scenario_name)
            if scenario:
                self.controller.show_frame("ScenarioDetails", scenario)

    def add_new_scenario(self):
        """
        Navigates to the Add/Edit Scenario scene for creating a new scenario.
        """
        self.controller.show_frame("AddEditScenario")
    
    def edit_scenario(self):
        """
        Navigates to the Add/Edit Scenario scene for editing an existing scenario.
        """
        selected_item = self.scenarios_tree.focus()
        if selected_item:
            scenario_name = self.scenarios_tree.item(selected_item, "text")
            scenario = self.scenario_manager.load_scenario(scenario_name)
            if scenario:
                self.controller.show_frame("AddEditScenario", scenario)

    def delete_scenario(self):
        """
        Deletes the selected scenario after a confirmation dialog.
        """
        selected_item = self.scenarios_tree.focus()
        if selected_item:
            scenario_name = self.scenarios_tree.item(selected_item, "text")
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete scenario '{scenario_name}'?"):
                self.scenario_manager.delete_scenario(scenario_name)
                self.populate_scenario_list()


class ScenarioDetails(ttk.Frame):
    """
    Scene 2: Displays the details of a single scenario and its steps, and allows for execution.
    """
    def __init__(self, parent, controller, scenario_manager):
        super().__init__(parent)
        self.controller = controller
        self.scenario_manager = scenario_manager
        self.scenario = None
        self.current_step_index = 0
        self.is_running = False
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Main frame
        main_frame = ttk.Frame(self, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)

        # Title and back button
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)
        
        back_button = ttk.Button(top_frame, text="< Back", command=self.go_back)
        back_button.grid(row=0, column=0, sticky="w")
        
        self.title_label = ttk.Label(top_frame, text="Scenario Details", font=("Helvetica", 16, "bold"))
        self.title_label.grid(row=0, column=1, sticky="w", padx=10)

        # Details display
        details_frame = ttk.LabelFrame(main_frame, text="Details", padding="10")
        details_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        details_frame.columnconfigure(1, weight=1)

        ttk.Label(details_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.name_label = ttk.Label(details_frame, text="")
        self.name_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(details_frame, text="Description:").grid(row=1, column=0, sticky="nw", padx=5, pady=2)
        self.description_label = ttk.Label(details_frame, text="", wraplength=450)
        self.description_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        # Steps list
        steps_frame = ttk.LabelFrame(main_frame, text="Steps", padding="10")
        steps_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        steps_frame.columnconfigure(0, weight=1)
        steps_frame.rowconfigure(0, weight=1)

        self.steps_tree = ttk.Treeview(steps_frame, columns=("Type", "Content"), show="headings", height=10)
        self.steps_tree.heading("#0", text="ID")
        self.steps_tree.heading("Type", text="Type")
        self.steps_tree.heading("Content", text="Content")
        
        self.steps_tree.column("#0", width=30, anchor=tk.CENTER)
        self.steps_tree.column("Type", width=150)
        self.steps_tree.column("Content", width=300)
        
        self.steps_tree.grid(row=0, column=0, sticky="nsew")
        
        steps_scrollbar = ttk.Scrollbar(steps_frame, orient="vertical", command=self.steps_tree.yview)
        steps_scrollbar.grid(row=0, column=1, sticky="ns")
        self.steps_tree.configure(yscrollcommand=steps_scrollbar.set)
        
        # Status Label
        status_frame = ttk.Frame(main_frame, padding="10 0")
        status_frame.grid(row=3, column=0, sticky="ew")
        status_frame.columnconfigure(0, weight=1)

        self.current_step_label = ttk.Label(status_frame, text="Status: Ready", font=("Helvetica", 10, "italic"))
        self.current_step_label.grid(row=0, column=0, sticky="w")
        
        # Action buttons
        button_frame = ttk.Frame(main_frame, padding="10 0")
        button_frame.grid(row=4, column=0, sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        ttk.Button(button_frame, text="Edit Scenario", command=self.edit_scenario).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(button_frame, text="Delete Scenario", command=self.delete_scenario).grid(row=0, column=1, padx=5, sticky="ew")
        
        self.run_button = ttk.Button(button_frame, text="Run Scenario", command=self.run_scenario)
        self.run_button.grid(row=0, column=2, columnspan=2, padx=5, sticky="ew")

    def show(self, data):
        """
        Called when this scene is displayed. Populates the UI with scenario data.
        """
        self.scenario = data
        self.is_running = False
        self.current_step_index = 0
        self.title_label.config(text=f"Scenario Details: {self.scenario.name}")
        self.name_label.config(text=self.scenario.name)
        self.description_label.config(text=self.scenario.description)
        self.populate_steps_list()
        self.current_step_label.config(text="Status: Ready")
        self.run_button.config(text="Run Scenario", command=self.run_scenario, state=tk.NORMAL)

    def populate_steps_list(self):
        """
        Clears the step list and populates it with the steps from the current scenario.
        """
        for item in self.steps_tree.get_children():
            self.steps_tree.delete(item)
            
        for step in self.scenario.steps:
            self.steps_tree.insert("", "end", iid=str(step.step_id), text=step.step_id, values=(step.step_type, step.content))
            
    def go_back(self):
        """
        Navigates back to the All Scenarios scene.
        """
        # Stop any running process before leaving the scene
        if self.is_running:
            self.stop_scenario()
        self.controller.show_frame("AllScenarios")

    def edit_scenario(self):
        """
        Navigates to the Add/Edit Scenario scene to edit the current scenario.
        """
        self.controller.show_frame("AddEditScenario", self.scenario)

    def delete_scenario(self):
        """
        Deletes the current scenario and returns to the main list.
        """
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete scenario '{self.scenario.name}'?"):
            self.scenario_manager.delete_scenario(self.scenario.name)
            self.controller.show_frame("AllScenarios")

    def run_scenario(self):
        """
        Starts the execution of the scenario.
        """
        if not self.scenario.steps:
            messagebox.showinfo("Run Scenario", "This scenario has no steps to run.")
            return

        self.is_running = True
        self.current_step_index = 0
        self.run_button.config(text="Stop", command=self.stop_scenario)
        self._execute_next_step()

    def stop_scenario(self):
        """
        Stops the execution of the scenario.
        """
        self.is_running = False
        self.run_button.config(text="Run Scenario", command=self.run_scenario)
        self.current_step_label.config(text="Status: Execution stopped.")
        # Reset the treeview selection highlighting
        self.steps_tree.selection_remove(self.steps_tree.get_children())
        self.steps_tree.focus("")

    def _execute_next_step(self):
        """
        Executes the next step in the scenario or stops if finished.
        This method is called recursively using `self.after()`.
        """
        if not self.is_running or self.current_step_index >= len(self.scenario.steps):
            if self.is_running:
                self.current_step_label.config(text="Status: Scenario completed.")
                self.run_button.config(text="Run Scenario", command=self.run_scenario)
                self.is_running = False
                # Reset the treeview selection highlighting
                self.steps_tree.selection_remove(self.steps_tree.get_children())
                self.steps_tree.focus("")
            return

        step = self.scenario.steps[self.current_step_index]
        self.current_step_label.config(text=f"Status: Executing step {step.step_id}: {step.name}")
        
        # Highlight the current step in the treeview
        self.steps_tree.selection_remove(self.steps_tree.get_children())
        self.steps_tree.selection_add(str(step.step_id))
        self.steps_tree.focus(str(step.step_id))
        
        # =======================================================
        # TODO: This is where you would integrate the automation logic
        # For now, it's a simple `print` and a delay.
        print(f"Executing step {step.step_id}: {step.name} - Type: {step.step_type}, Content: {step.content}")
        # =======================================================
        
        # Move to the next step after a delay (e.g., 2000 milliseconds)
        self.current_step_index += 1
        self.after(2000, self._execute_next_step)


class AddEditScenario(ttk.Frame):
    """
    Scene 3: Form to add a new scenario or edit an existing one.
    """
    def __init__(self, parent, controller, scenario_manager):
        super().__init__(parent)
        self.controller = controller
        self.scenario_manager = scenario_manager
        self.scenario = None
        self.current_step_id = 0
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        main_frame = ttk.Frame(self, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        
        # Title and back button
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)
        
        self.back_button = ttk.Button(top_frame, text="< Back", command=self.go_back)
        self.back_button.grid(row=0, column=0, sticky="w")
        
        self.title_label = ttk.Label(top_frame, text="Add New Scenario", font=("Helvetica", 16, "bold"))
        self.title_label.grid(row=0, column=1, sticky="w", padx=10)
        
        # Scenario details frame
        details_frame = ttk.LabelFrame(main_frame, text="Scenario Details", padding="10")
        details_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        details_frame.columnconfigure(1, weight=1)
        
        ttk.Label(details_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.name_entry = ttk.Entry(details_frame)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(details_frame, text="Description:").grid(row=1, column=0, sticky="nw", padx=5, pady=2)
        self.description_text = tk.Text(details_frame, height=4, width=50)
        self.description_text.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        # Steps management frame
        steps_frame = ttk.LabelFrame(main_frame, text="Steps", padding="10")
        steps_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        steps_frame.columnconfigure(0, weight=1)
        steps_frame.rowconfigure(0, weight=1)

        self.steps_tree = ttk.Treeview(steps_frame, columns=("Type", "Content"), show="headings", height=10)
        self.steps_tree.heading("#0", text="ID", anchor=tk.CENTER)
        self.steps_tree.heading("Type", text="Type")
        self.steps_tree.heading("Content", text="Content")
        
        self.steps_tree.column("#0", width=30, anchor=tk.CENTER)
        self.steps_tree.column("Type", width=150)
        self.steps_tree.column("Content", width=300)
        
        self.steps_tree.grid(row=0, column=0, sticky="nsew")
        
        steps_scrollbar = ttk.Scrollbar(steps_frame, orient="vertical", command=self.steps_tree.yview)
        steps_scrollbar.grid(row=0, column=1, sticky="ns")
        self.steps_tree.configure(yscrollcommand=steps_scrollbar.set)
        
        # Bind double click to edit step
        self.steps_tree.bind("<Double-1>", self.on_step_select)
        
        # Step action buttons
        step_button_frame = ttk.Frame(steps_frame)
        step_button_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        step_button_frame.columnconfigure(0, weight=1)
        step_button_frame.columnconfigure(1, weight=1)
        step_button_frame.columnconfigure(2, weight=1)

        ttk.Button(step_button_frame, text="Add Step", command=self.add_step).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(step_button_frame, text="Edit Step", command=self.edit_selected_step).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(step_button_frame, text="Delete Step", command=self.delete_selected_step).grid(row=0, column=2, padx=5, sticky="ew")
        
        # Save button
        save_button = ttk.Button(main_frame, text="Save Scenario", command=self.save_scenario)
        save_button.grid(row=3, column=0, sticky="e", pady=(10, 0))
    
    def show(self, data=None):
        """
        Called when this scene is displayed. Initializes for add or edit mode.
        """
        self.scenario = data
        self.current_step_id = 0
        self.name_entry.delete(0, tk.END)
        self.description_text.delete(1.0, tk.END)
        self.steps_tree.delete(*self.steps_tree.get_children())
        
        if self.scenario:
            self.title_label.config(text=f"Edit Scenario: {self.scenario.name}")
            self.name_entry.insert(0, self.scenario.name)
            self.description_text.insert(1.0, self.scenario.description)
            self.populate_steps_list()
        else:
            self.title_label.config(text="Add New Scenario")
            self.scenario = Scenario(name="", description="", steps=[])
            
    def go_back(self):
        """
        Navigates back to the All Scenarios scene.
        """
        self.controller.show_frame("AllScenarios")

    def populate_steps_list(self):
        """
        Clears the step list and populates it from the current scenario's steps.
        """
        self.steps_tree.delete(*self.steps_tree.get_children())
        for step in self.scenario.steps:
            self.steps_tree.insert("", "end", iid=str(step.step_id), text=step.step_id, values=(step.step_type, step.content))
        self.current_step_id = len(self.scenario.steps)
    
    def add_step(self):
        """
        Opens a dialog to add a new step to the scenario.
        """
        self.current_step_id += 1
        AddEditStepDialog(self, f"Add Step {self.current_step_id}", self.current_step_id, self.on_step_added)

    def edit_selected_step(self):
        """
        Opens a dialog to edit the selected step.
        """
        selected_item = self.steps_tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select a step to edit.")
            return

        step_id = int(self.steps_tree.item(selected_item, "text"))
        step_to_edit = next((step for step in self.scenario.steps if step.step_id == step_id), None)

        if step_to_edit:
            AddEditStepDialog(self, f"Edit Step {step_to_edit.step_id}", step_to_edit.step_id, self.on_step_updated, step_to_edit)
    
    def on_step_select(self, event):
        """
        Handles double-clicking a step to edit it.
        """
        self.edit_selected_step()

    def on_step_added(self, step):
        """
        Callback function for when a new step is added.
        """
        self.scenario.steps.append(step)
        self.populate_steps_list()
    
    def on_step_updated(self, step):
        """
        Callback function for when a step is updated.
        """
        # Find and replace the updated step
        for i, existing_step in enumerate(self.scenario.steps):
            if existing_step.step_id == step.step_id:
                self.scenario.steps[i] = step
                break
        self.populate_steps_list()

    def delete_selected_step(self):
        """
        Deletes the selected step from the scenario.
        """
        selected_item = self.steps_tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select a step to delete.")
            return
        
        step_id_to_delete = int(self.steps_tree.item(selected_item, "text"))
        self.scenario.steps = [step for step in self.scenario.steps if step.step_id != step_id_to_delete]
        
        # Re-index the steps to maintain sequential IDs
        for i, step in enumerate(self.scenario.steps):
            step.step_id = i + 1
        self.current_step_id = len(self.scenario.steps)
        
        self.populate_steps_list()

    def save_scenario(self):
        """
        Saves the current scenario to a file.
        """
        scenario_name = self.name_entry.get().strip()
        scenario_description = self.description_text.get(1.0, tk.END).strip()
        
        if not scenario_name:
            messagebox.showerror("Error", "Scenario name cannot be empty.")
            return
        
        # If we are editing, check if the name has changed to avoid creating a new file
        original_name = self.scenario.name if hasattr(self.scenario, 'name') else None
        
        # Handle the case where the scenario name is changed during an edit
        if original_name and original_name != scenario_name:
            if messagebox.askyesno("Rename Scenario", f"Are you sure you want to rename '{original_name}' to '{scenario_name}'? This will delete the old file.", parent=self):
                self.scenario_manager.delete_scenario(original_name)
            else:
                return

        self.scenario.name = scenario_name
        self.scenario.description = scenario_description
        
        self.scenario_manager.save_scenario(self.scenario)
        messagebox.showinfo("Success", f"Scenario '{scenario_name}' saved.")
        self.controller.show_frame("AllScenarios")
        

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

