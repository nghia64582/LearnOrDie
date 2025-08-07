# scenario_details.py
# This file contains the UI for displaying a single scenario and running it.

import tkinter as tk
from tkinter import ttk, messagebox

# Import necessary application components
from scenario_model import Scenario, Step, STEP_TYPES
from scenario_manager import ScenarioManager

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
        self.after(200, self._execute_next_step)
