# main.py
# This is the main application entry point.

import tkinter as tk
from tkinter import ttk

# Import application components from their new files
from scenario_manager import ScenarioManager
from all_scenarios import AllScenarios
from scenario_details import ScenarioDetails
from add_edit_scenario import AddEditScenario
from add_edit_step_dialog import AddEditStepDialog # Not directly used here, but good practice to have it available

class App(tk.Tk):
    """
    Main application class for the AutoBot.
    This class handles the window creation and switching between different scenes.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("AutoBot - Scenario Automation Tool")
        self.geometry("800x600")
        self.resizable(True, True)

        # Apply a theme
        style = ttk.Style(self)
        style.theme_use("clam")

        self.scenario_manager = ScenarioManager()

        # Create a main container frame to hold all other frames
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        
        # Instantiate all scenes and add them to the frames dictionary
        for F in (AllScenarios, ScenarioDetails, AddEditScenario):
            frame_name = F.__name__
            frame = F(parent=container, controller=self, scenario_manager=self.scenario_manager)
            self.frames[frame_name] = frame
            # Put all frames in the same location
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("AllScenarios")

    def show_frame(self, frame_name, data=None):
        """
        Raises the specified frame to the top and shows it.
        The `data` parameter allows passing data to the new frame's `show` method.
        """
        frame = self.frames[frame_name]
        frame.show(data)
        frame.tkraise()

if __name__ == "__main__":
    app = App()
    app.mainloop()

