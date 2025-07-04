import tkinter as tk
from tkinter import ttk

def create_main_tabs():
    root = tk.Tk()
    root.title("Tkinter Multi-Tab App")
    root.geometry("600x400")

    # Create a Notebook (tabbed widget)
    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill="both", padx=10, pady=10)

    # --- Tab 1: Home ---
    tab1_frame = ttk.Frame(notebook) # Create a frame to hold content for Tab 1
    tab1_frame.pack(fill="both", expand=True)

    notebook.add(tab1_frame, text="Home") # Add the frame to the notebook with a tab title

    ttk.Label(tab1_frame, text="Welcome to the Home Tab!").pack(pady=20)
    ttk.Button(tab1_frame, text="Click Me!").pack()

    # --- Tab 2: Settings ---
    tab2_frame = ttk.Frame(notebook)
    tab2_frame.pack(fill="both", expand=True)

    notebook.add(tab2_frame, text="Settings")

    ttk.Label(tab2_frame, text="Configure your settings here.").pack(pady=20)
    ttk.Checkbutton(tab2_frame, text="Enable Feature X").pack()
    ttk.Entry(tab2_frame, width=30).pack(pady=5)

    # --- Tab 3: About ---
    tab3_frame = ttk.Frame(notebook)
    tab3_frame.pack(fill="both", expand=True)

    notebook.add(tab3_frame, text="About")

    ttk.Label(tab3_frame, text="This is a simple Tkinter tabbed application.").pack(pady=20)
    ttk.Label(tab3_frame, text="Version 1.0").pack()

    root.mainloop()

# Run the basic tabbed app
create_main_tabs()