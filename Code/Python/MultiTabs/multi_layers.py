import tkinter as tk
from tkinter import ttk

def create_multi_layer_tabs():
    # Create the main application window
    global root
    global main_notebook
    global main_tab1_frame, main_tab2_frame, main_tab3_frame


    # Set up main font
    font = ("Inter", 12)

    root = tk.Tk()
    root.title("Tkinter Multi-Layer Tab App")
    root.geometry("800x600")
    root.option_add("*TButton*font", font)
    root.option_add("*TLabel*font", font)
    root.option_add("*TEntry*font", font)
    root.option_add("*TScale*font", font)
    root.option_add("*TFrame*font", font)
    root.option_add("*TNotebook*font", font)

    # --- Main Notebook ---
    main_notebook = ttk.Notebook(root)
    main_notebook.pack(expand=True, fill="both", padx=10, pady=10)

    # --- Main Tab 1: Dashboard ---
    main_tab1_frame = ttk.Frame(main_notebook)
    main_tab1_frame.pack(fill="both", expand=True)
    main_notebook.add(main_tab1_frame, text="Dashboard")
    ttk.Label(main_tab1_frame, text="Welcome to the Dashboard!").pack(pady=20)

    # --- Main Tab 2: Data View (This will contain sub-tabs) ---
    main_tab2_frame = ttk.Frame(main_notebook)
    main_tab2_frame.pack(fill="both", expand=True)
    main_notebook.add(main_tab2_frame, text="Data View")

    # --- Create a SUB-NOTEBOOK inside main_tab2_frame ---
    sub_notebook = ttk.Notebook(main_tab2_frame) # Parent is main_tab2_frame
    sub_notebook.pack(expand=True, fill="both", padx=10, pady=10)

    # --- Sub-Tab 2.1: Raw Data ---
    sub_tab1_frame = ttk.Frame(sub_notebook)
    sub_tab1_frame.pack(fill="both", expand=True)
    sub_notebook.add(sub_tab1_frame, text="Raw Data")
    ttk.Label(sub_tab1_frame, text="Displaying Raw Data here.").pack(pady=20)
    ttk.Entry(sub_tab1_frame, width=50).pack()

    # --- Sub-Tab 2.2: Summaries ---
    sub_tab2_frame = ttk.Frame(sub_notebook)
    sub_tab2_frame.pack(fill="both", expand=True)
    sub_notebook.add(sub_tab2_frame, text="Summaries")
    ttk.Label(sub_tab2_frame, text="Data Summaries and Aggregations.").pack(pady=20)
    ttk.Label(sub_tab2_frame, text="Chart placeholder...").pack()

    # --- Sub-Tab 2.3: Reports ---
    sub_tab3_frame = ttk.Frame(sub_notebook)
    sub_tab3_frame.pack(fill="both", expand=True)
    sub_notebook.add(sub_tab3_frame, text="Reports")
    ttk.Label(sub_tab3_frame, text="Generate and view reports.").pack(pady=20)
    ttk.Button(sub_tab3_frame, text="Generate Report").pack()

    # --- Main Tab 3: Configuration ---
    main_tab3_frame = ttk.Frame(main_notebook)
    main_tab3_frame.pack(fill="both", expand=True)
    main_notebook.add(main_tab3_frame, text="Configuration")
    ttk.Label(main_tab3_frame, text="App Configuration Options.").pack(pady=20)
    ttk.Scale(main_tab3_frame, from_=0, to_=100, orient="horizontal", length=300).pack(pady=10)

    root.mainloop()

# Run the multi-layer tabbed app
create_multi_layer_tabs()