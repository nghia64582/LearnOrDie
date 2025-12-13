# app.py
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import datetime as dt
import threading
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import pandas as pd
# ------- DPI FIX -------
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()
# -----------------------

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
        
        # Tab Single Symbol
        self.single_symbol_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.single_symbol_tab, text="Single Symbol")
        self.setup_single_symbol()

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
        self.start_date_picker.set_date(dt.datetime(2025, 1, 1))
        self.start_date_picker.pack(side=tk.LEFT, padx=(0, 10))

        # End Date Picker
        ttk.Label(controls_frame, text="End Date:").pack(side=tk.LEFT, padx=(0, 5))
        self.end_date_picker = DateEntry(controls_frame, date_pattern='yyyy-mm-dd', locale='en_US')
        self.end_date_picker.set_date(dt.datetime.now().date() - dt.timedelta(days=1))
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
            
            start_date = dt.datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = dt.datetime.strptime(end_date_str, "%Y-%m-%d")

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
    
    def setup_single_symbol(self):
        frame = ttk.Frame(self.single_symbol_tab)
        frame.pack(pady=20, padx=20, anchor="nw")

        # Stock symbol
        ttk.Label(frame, text="Stock Symbol:").grid(row=0, column=0, sticky="w")
        self.symbol_entry = ttk.Entry(frame, width=15)
        self.symbol_entry.grid(row=0, column=1, padx=5)

        # End date (default = hôm qua)
        default_end = (dt.datetime.today() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
        ttk.Label(frame, text="End Date (YYYY-MM-DD):").grid(row=1, column=0, sticky="w")
        self.end_date_entry = ttk.Entry(frame, width=15)
        self.end_date_entry.insert(0, default_end)
        self.end_date_entry.grid(row=1, column=1, padx=5)

        # Start date (default = 7 ngày trước end_date)
        default_start = (dt.datetime.today() - dt.timedelta(days=8)).strftime("%Y-%m-%d")
        ttk.Label(frame, text="Start Date (YYYY-MM-DD):").grid(row=2, column=0, sticky="w")
        self.start_date_entry = ttk.Entry(frame, width=15)
        self.start_date_entry.insert(0, default_start)
        self.start_date_entry.grid(row=2, column=1, padx=5)

        # Time ranges
        ttk.Label(frame, text="Time Range:").grid(row=3, column=0, sticky="w")

        self.range_var = tk.StringVar(value="1W")
        ranges = {
            "1 Week": "1W",
            "1 Month": "1M",
            "3 Months": "3M",
            "6 Months": "6M",
            "1 Year": "1Y",
            "2 Years": "2Y",
            "Custom": "C"
        }

        col = 1
        for label, value in ranges.items():
            rb = ttk.Radiobutton(
                frame,
                text=label,
                variable=self.range_var,
                value=value,
                command=self.update_dates_from_range
            )
            rb.grid(row=3, column=col, padx=5, sticky="w")
            col += 1

        # Khi user thay đổi start_date hoặc end_date -> set Custom
        self.start_date_entry.bind("<KeyRelease>", lambda e: self.range_var.set("C"))
        self.end_date_entry.bind("<KeyRelease>", lambda e: self.range_var.set("C"))

        # Button
        self.plot_btn = ttk.Button(frame, text="Show Chart", command=self.plot_single_symbol)
        self.plot_btn.grid(row=4, column=0, columnspan=2, pady=10)

        # Chart area
        self.chart_frame = ttk.Frame(self.single_symbol_tab)
        self.chart_frame.pack(fill="both", expand=True)

    def update_dates_from_range(self):
        """Cập nhật start_date dựa trên end_date khi chọn radio button"""
        if self.range_var.get() == "C":
            return  # Custom thì không động tới
        try:
            end_date = dt.datetime.strptime(self.end_date_entry.get().strip(), "%Y-%m-%d")
        except ValueError:
            return

        if self.range_var.get() == "1W":
            start_date = end_date - dt.timedelta(weeks=1)
        elif self.range_var.get() == "1M":
            start_date = end_date - dt.timedelta(days=30)
        elif self.range_var.get() == "3M":
            start_date = end_date - dt.timedelta(days=90)
        elif self.range_var.get() == "6M":
            start_date = end_date - dt.timedelta(days=180)
        elif self.range_var.get() == "1Y":
            start_date = end_date - dt.timedelta(days=365)
        elif self.range_var.get() == "2Y":
            start_date = end_date - dt.timedelta(days=730)
        else:
            return

        self.start_date_entry.delete(0, tk.END)
        self.start_date_entry.insert(0, start_date.strftime("%Y-%m-%d"))

    def plot_single_symbol(self):
        symbol = self.symbol_entry.get().strip().upper()
        start_date_str = self.start_date_entry.get().strip()
        end_date_str = self.end_date_entry.get().strip()

        if not symbol or not end_date_str or not start_date_str:
            messagebox.showerror("Error", "Please enter stock symbol, start date and end date")
            return

        try:
            start_date = dt.datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = dt.datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return

        if start_date > end_date:
            messagebox.showerror("Error", "Start date must be before end date")
            return

        file_path = f"stock_prices/{symbol}.csv"

        try:
            df = pd.read_csv(file_path, parse_dates=["time"])
        except FileNotFoundError:
            messagebox.showerror("Error", f"CSV file for {symbol} not found")
            return

        # Filter date range
        df_filtered = df[(df["time"] >= start_date) & (df["time"] <= end_date)]
        if df_filtered.empty:
            messagebox.showinfo("No Data", "No data in the selected range")
            return

        # Clear old chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(df_filtered["time"], df_filtered["close"], label="Close Price", color="blue")
        ax.set_title(f"{symbol} Stock Prices")
        ax.set_xlabel("Date")
        ax.set_ylabel("Close Price")
        ax.legend()
        ax.grid(True)

        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

if __name__ == '__main__':
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()