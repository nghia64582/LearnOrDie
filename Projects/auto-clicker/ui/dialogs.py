"""Standard dialog helpers for the UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Literal, Optional


def prompt_save_changes(
    parent: tk.Widget, workflow_name: str
) -> Literal["save", "discard", "cancel"]:
    """Ask the user whether to save changes before discarding or closing.

    Returns 'save', 'discard', or 'cancel'.
    """
    box = messagebox.askyesnocancel(
        title="Unsaved Changes",
        message=f"Workflow '{workflow_name}' has unsaved changes.\nDo you want to save before continuing?",
        parent=parent,
    )
    if box is True:
        return "save"
    elif box is False:
        return "discard"
    else:
        return "cancel"


def confirm_action(parent: tk.Widget, title: str, message: str) -> bool:
    """Show a confirmation Yes/No dialog."""
    return messagebox.askyesno(title=title, message=message, parent=parent)


def prompt_text(
    parent: tk.Widget, title: str, prompt: str, initial_value: str = ""
) -> Optional[str]:
    """Prompt the user for a text string."""
    return simpledialog.askstring(
        title=title, prompt=prompt, initialvalue=initial_value, parent=parent
    )


def show_error(parent: tk.Widget, title: str, message: str) -> None:
    """Show an error message box."""
    messagebox.showerror(title=title, message=message, parent=parent)


def show_info(parent: tk.Widget, title: str, message: str) -> None:
    """Show an informational message box."""
    messagebox.showinfo(title=title, message=message, parent=parent)


def show_warning(parent: tk.Widget, title: str, message: str) -> None:
    """Show a warning message box."""
    messagebox.showwarning(title=title, message=message, parent=parent)
