# scenario_manager.py
# This file handles saving, loading, and deleting scenarios from the file system.

import os
import json
from typing import List, Optional
from scenario_model import Scenario, Step

class ScenarioManager:
    """
    Manages the creation, retrieval, and deletion of scenario files.
    """
    def __init__(self, scenarios_dir="scenarios"):
        """
        Initializes the ScenarioManager and ensures the scenarios directory exists.

        Args:
            scenarios_dir (str, optional): The directory where scenarios are saved.
        """
        self.scenarios_dir = scenarios_dir
        if not os.path.exists(self.scenarios_dir):
            os.makedirs(self.scenarios_dir)

    def save_scenario(self, scenario: Scenario):
        """
        Saves a Scenario object to a file in the scenarios directory.
        The filename is based on the scenario's name.

        Args:
            scenario (Scenario): The Scenario object to be saved.
        """
        file_path = os.path.join(self.scenarios_dir, f"{scenario.name}.txt")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(scenario.to_dict(), f, indent=4)
            print(f"Scenario '{scenario.name}' saved successfully.")
        except IOError as e:
            print(f"Error saving scenario '{scenario.name}': {e}")

    def load_scenarios(self) -> List[Scenario]:
        """
        Loads all scenario files from the scenarios directory.

        Returns:
            List[Scenario]: A list of Scenario objects.
        """
        scenarios = []
        for filename in os.listdir(self.scenarios_dir):
            if filename.endswith(".txt"):
                file_path = os.path.join(self.scenarios_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        scenario = Scenario.from_dict(data)
                        scenarios.append(scenario)
                except (IOError, json.JSONDecodeError) as e:
                    print(f"Error loading scenario from '{filename}': {e}")
        return scenarios

    def load_scenario(self, scenario_name: str) -> Optional[Scenario]:
        """
        Loads a single scenario by name.

        Args:
            scenario_name (str): The name of the scenario to load.

        Returns:
            Optional[Scenario]: The Scenario object if found, otherwise None.
        """
        file_path = os.path.join(self.scenarios_dir, f"{scenario_name}.txt")
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Scenario.from_dict(data)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading scenario from '{scenario_name}.txt': {e}")
            return None

    def delete_scenario(self, scenario_name: str):
        """
        Deletes a scenario file.

        Args:
            scenario_name (str): The name of the scenario to delete.
        """
        file_path = os.path.join(self.scenarios_dir, f"{scenario_name}.txt")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Scenario '{scenario_name}' deleted successfully.")
            except OSError as e:
                print(f"Error deleting scenario '{scenario_name}': {e}")
        else:
            print(f"Scenario '{scenario_name}' not found.")

