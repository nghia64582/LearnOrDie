# add_edit_scenario.py
# This file contains the UI for adding or editing a scenario.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Import necessary application components
from scenario_model import Scenario, Step, STEP_TYPES
from scenario_manager import ScenarioManager
from add_edit_step_dialog import AddEditStepDialog

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
