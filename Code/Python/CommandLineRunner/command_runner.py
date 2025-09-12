import subprocess
import shlex
import os
import sys
from typing import List, Dict, Union, Tuple, Any

class CommandRunner:
    """
    A class to execute and manage command-line commands.
    """

    def __init__(self, cwd: str = None):
        """
        Initializes the CommandRunner instance.

        Args:
            cwd (str, optional): The default current working directory for all commands.
                                 If None, the system's default CWD is used.
        """
        self.cwd = cwd
        print(f"CommandRunner initialized. Default working directory: {self.cwd or 'Current'}")

    def run_command(self, command: str, *args: str, cwd: str = None, shell: bool = False) -> Dict[str, Any]:
        """
        Runs a single command with its arguments and captures the output.

        Args:
            command (str): The main command to execute (e.g., 'ls', 'dir', 'ping').
            *args (str): A variable number of arguments for the command.
            cwd (str, optional): The current working directory for this specific command.
                                 If None, the default CWD from the class instance is used.
            shell (bool, optional): If True, the command will be executed through the shell.
                                    WARNING: This can be a security risk if the command
                                    string is constructed from untrusted input. Defaults to False.

        Returns:
            A dictionary containing the command's execution details:
            - 'command': The full command string that was executed.
            - 'returncode': The exit code of the process. 0 typically indicates success.
            - 'stdout': The standard output of the command as a string.
            - 'stderr': The standard error of the command as a string.
        """
        # If shell=True, join the command and arguments into a single string.
        # Otherwise, pass them as a list for safer execution.
        if shell:
            # If the command itself contains spaces, wrap it in quotes for the shell.
            quoted_command = f'"{command}"' if ' ' in command and not (command.startswith('"') and command.endswith('"')) else command
            full_command = f"{quoted_command} {' '.join(list(args))}"
        else:
            full_command = [command] + list(args)
        print(f"Executing command: <{full_command}> (shell={shell})")
        
        # Determine the working directory for this command
        effective_cwd = cwd if cwd is not None else self.cwd
        
        try:
            # Use subprocess.run() for a high-level, convenient way to run processes.
            # capture_output=True: captures stdout and stderr.
            # text=True: decodes stdout and stderr as text.
            # check=False: prevents an exception from being raised for non-zero return codes.
            result = subprocess.run(
                full_command,
                cwd=effective_cwd,
                capture_output=True,
                text=True,
                check=False,
                shell=shell
            )
            return {
                "command": " ".join([command] + list(args)),
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except FileNotFoundError:
            return {
                "command": " ".join([command] + list(args)),
                "returncode": -1,
                "stdout": "",
                "stderr": f"Error: Command not found: '{command}'"
            }
        except Exception as e:
            return {
                "command": " ".join([command] + list(args)),
                "returncode": -2,
                "stdout": "",
                "stderr": f"An unexpected error occurred: {e}"
            }

    def run_commands(self, commands: List[Tuple[str, ...]], cwd: str = None, shell: bool = False) -> List[Dict[str, Any]]:
        """
        Runs a list of commands sequentially.

        Args:
            commands (List[Tuple[str, ...]]): A list where each element is a tuple
                                                representing a single command and its arguments.
                                                Example: [('ls', '-l'), ('echo', 'Hello World')]
            cwd (str, optional): The current working directory for all commands in this list.
                                 If None, the default CWD from the class instance is used.
            shell (bool, optional): If True, the commands will be executed through the shell.
                                    WARNING: This can be a security risk. Defaults to False.

        Returns:
            A list of dictionaries, where each dictionary is the result of a single
            command execution, as returned by run_command().
        """
        results = []
        effective_cwd = cwd if cwd is not None else self.cwd
        
        for cmd_tuple in commands:
            if not isinstance(cmd_tuple, tuple) or not cmd_tuple:
                results.append({
                    "command": "",
                    "returncode": -3,
                    "stdout": "",
                    "stderr": "Invalid command format. Expected a non-empty tuple."
                })
                continue
            
            command = cmd_tuple[0]
            args = cmd_tuple[1:]
            result = self.run_command(command, *args, cwd=effective_cwd, shell=shell)
            results.append(result)
            
        return results

if __name__ == "__main__":
    # Run this is current directory for demonstration purposes.
    runner = CommandRunner(cwd=".")

    if sys.platform == "win32":
        executable_path_with_spaces = "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE"

        # The `run_command` method's fix will correctly add quotes to the path.
        result_space = runner.run_commands(commands=[
            (executable_path_with_spaces, "/n"),  # Open a new instance of Word
            ("cmd", "/c", "echo Hello from Windows CMD")  # Simple echo command
        ], shell=False)