# scenario_model.py
# This file defines the data structures for a Step and a Scenario.

import json
from typing import List

# Define the possible types of steps.
STEP_TYPES = [
    "Wait for image",
    "Click image",
    "Type word",
    "Press button"
]

class Step:
    """
    Represents a single step in a scenario.
    """
    def __init__(self, step_id: int, name: str, step_type: str, content: str = None):
        """
        Initializes a Step object.

        Args:
            step_id (int): The unique ID of the step within a scenario.
            name (str): A descriptive name for the step.
            step_type (str): The type of action for this step (e.g., 'Click image').
            content (str, optional): The content associated with the step.
                                     For image steps, this is the file path.
                                     For text/button steps, this is the string to type/press.
        """
        self.step_id = step_id
        self.name = name
        self.step_type = step_type
        self.content = content

    def to_dict(self):
        """
        Converts the Step object to a dictionary for JSON serialization.
        """
        return {
            "step_id": self.step_id,
            "name": self.name,
            "step_type": self.step_type,
            "content": self.content
        }

    @classmethod
    def from_dict(cls, data: dict):
        """
        Creates a Step object from a dictionary.
        """
        return cls(
            step_id=data.get("step_id"),
            name=data.get("name"),
            step_type=data.get("step_type"),
            content=data.get("content")
        )

class Scenario:
    """
    Represents an entire automation scenario.
    """
    def __init__(self, name: str, description: str, steps: List[Step] = None):
        """
        Initializes a Scenario object.

        Args:
            name (str): The name of the scenario. This will also be the filename.
            description (str): A detailed description of what the scenario does.
            steps (List[Step], optional): A list of Step objects that make up the scenario.
        """
        self.name = name
        self.description = description
        self.steps = steps if steps is not None else []

    def to_dict(self):
        """
        Converts the Scenario object to a dictionary for JSON serialization.
        """
        return {
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps]
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """
        Creates a Scenario object from a dictionary.
        """
        return cls(
            name=data.get("name"),
            description=data.get("description"),
            steps=[Step.from_dict(step_data) for step_data in data.get("steps", [])]
        )
