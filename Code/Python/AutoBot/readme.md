DESCRIPTION:
    - One Tool to create and perform many scenarios of autobot, each scenario contain several steps
      like clicking image/button, waiting for an image to appear, write a word, type a button, ...

FEATURE:
    - Manage all auto scenarios (CRUD scenarios)
    - Show/edit/perform one scenario
    - Each scenario has multiple steps
    - Each step could be one of these types:
        - Wait for an image to appear
        - Click into one image in a zone (defined by a rectangle)
        - Type a word/button

NOTES:
    - The bot can jump from one step to another
    - We can start the scenario at a specific step, not alway at step 1

MAIN SCENES:
    1. All scenarios:
        - List all scenarios with their details (name, description, steps count, etc.)
        - Each scenario can be clicked to view its details.
        - Each scenario can be edited or deleted.
        - A button to add new scenario (scene 3)
    2. Scenarios details:
        - Show scenario details (name, description, steps list, etc.)
        - Each step can be clicked to view its details.
        - Each step can be edited or deleted.
        - A start button to perform the scenario.
        - A "run" button to run the scenario (write the function later)
    3. Add new scenario:
        - Textfield: name, description
        - Contain a table of steps, each step has id (1 -> n), name, type
        - Each step could be deleted
        - Each step belong one of 4 types and corresponding contents or components:
            - Click an image: image path / file browser
            - Wait for an image to appear: image path / file browser
            - Write a word: string / text field
            - Press a button: string / text field
        - The base type is None, after choosing the type, components are displayed to clarify the step
        - A "save" button to save scenario, the folder is /scenarios, file name is <scenario_name>.txt

TOOLS:
    - tkinter, python

DONE:
    - Create basic UI and logic to manage all scenarios and steps
TODO:
    - Implement logic to run a scenario
    - 