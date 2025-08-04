# all_scenarios.py
# This file contains the main view for displaying and managing all scenarios.

import tkinter as tk
from tkinter import ttk, messagebox

# Import necessary application components
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

