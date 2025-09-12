# app.py
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import datetime
import threading

# Import the external data handler module
from main import process

class StockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Market Tracker")
        self.root.geometry("900x700")

        self.tab_control = ttk.Notebook(root)
        self.tab_control.pack(expand=1, fill="both")

        self.highest_increase_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.highest_increase_tab, text="Highest Increase")
        
        # Placeholder for other tabs
        self.other_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.other_tab, text="Other Tab")

        self.setup_highest_increase_tab()

    def setup_highest_increase_tab(self):
        # Frame for controls (date pickers and button)
        controls_frame = ttk.Frame(self.highest_increase_tab, padding="10")
        controls_frame.pack(side=tk.TOP, fill=tk.X)

        # Start Date Picker
        ttk.Label(controls_frame, text="Start Date:").pack(side=tk.LEFT, padx=(0, 5))
        self.start_date_picker = DateEntry(controls_frame, date_pattern='yyyy-mm-dd', locale='en_US')
        self.start_date_picker.set_date(datetime.datetime(2025, 1, 1))
        self.start_date_picker.pack(side=tk.LEFT, padx=(0, 10))

        # End Date Picker
        ttk.Label(controls_frame, text="End Date:").pack(side=tk.LEFT, padx=(0, 5))
        self.end_date_picker = DateEntry(controls_frame, date_pattern='yyyy-mm-dd', locale='en_US')
        self.end_date_picker.set_date(datetime.datetime.now().date() - datetime.timedelta(days=1))
        self.end_date_picker.pack(side=tk.LEFT, padx=(0, 10))
        
        # Calculate Button
        self.calculate_button = ttk.Button(controls_frame, text="Calculate", command=self.calculate_and_display)
        self.calculate_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Update price button
        self.update_price_button = ttk.Button(controls_frame, text="Update Prices", command=self.update_prices)
        self.update_price_button.pack(side=tk.LEFT, padx=(0, 10))

        # A simple label to indicate loading state
        self.status_label = ttk.Label(controls_frame, text="")
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))

        # Using a Canvas to better manage layout and widgets (for potential scrolling)
        main_canvas = tk.Canvas(self.highest_increase_tab)
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(self.highest_increase_tab, orient=tk.VERTICAL, command=main_canvas.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        main_canvas.configure(yscrollcommand=scroll_y.set)

        # Frame to hold the Treeview inside the Canvas
        frame_inside_canvas = ttk.Frame(main_canvas)
        main_canvas.create_window((0, 0), window=frame_inside_canvas, anchor="nw", height=600)
        
        # Update scroll region when frame size changes
        frame_inside_canvas.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))

        # Treeview to display results
        columns = ("symbol", "start_price", "end_price", "increased_rate")
        self.tree = ttk.Treeview(frame_inside_canvas, columns=columns, show="headings")

        # Define column headings
        self.tree.heading("symbol", text="Symbol")
        self.tree.heading("start_price", text="Start Price (VND)")
        self.tree.heading("end_price", text="End Price (VND)")
        self.tree.heading("increased_rate", text="Increased Rate (%)")
        
        # Set column widths
        self.tree.column("symbol", width=120, anchor=tk.CENTER)
        self.tree.column("start_price", width=150, anchor=tk.CENTER)
        self.tree.column("end_price", width=150, anchor=tk.CENTER)
        self.tree.column("increased_rate", width=150, anchor=tk.CENTER)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def update_prices(self):
        # Disable the button and show a loading message
        self.update_price_button.config(state="disabled")
        self.status_label.config(text="Updating Prices (up to 30s)...", foreground="blue")

        from main import save_main_symbols_prices
        save_main_symbols_prices()

        self.status_label.config(text="Prices Updated.", foreground="green")
        self.update_price_button.config(state="normal")


    def calculate_and_display(self):
        try:
            start_date_str = self.start_date_picker.get()
            end_date_str = self.end_date_picker.get()
            
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")

            if start_date >= end_date:
                messagebox.showerror("Invalid Dates", "End date must be after start date.")
                return
            
            # Disable the button and show a loading message
            self.calculate_button.config(state="disabled")
            self.status_label.config(text="Calculating...", foreground="blue")
            
            # Use a thread to perform the calculation to avoid freezing the GUI
            thread = threading.Thread(target=self._run_calculation, args=(start_date, end_date))
            thread.start()

        except ValueError:
            messagebox.showerror("Invalid Date", "Please select valid dates.")

    def _run_calculation(self, start_date, end_date):
        try:
            # Call the external module's process function
            results = process(start_date, end_date)
            
            # Pass results back to the main thread
            self.root.after(0, self._update_treeview, results)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {e}"))
            self.root.after(0, self._enable_button)

    def _update_treeview(self, results):
        # Clear the current Treeview data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insert new data into the Treeview
        for item in results:
            self.tree.insert(
                "", 
                "end", 
                values=(
                    item["symbol"], 
                    item["start_price"], 
                    item["end_price"], 
                    item["increased_rate"]
                )
            )
        
        self._enable_button()
        self.status_label.config(text="Calculation Complete.", foreground="green")
    
    def _enable_button(self):
        self.calculate_button.config(state="normal")


if __name__ == '__main__':
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()