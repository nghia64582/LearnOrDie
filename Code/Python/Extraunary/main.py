import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from tkcalendar import Calendar
import requests
import threading
import pandas as pd
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ExtraunaryManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Extraunary")
        self.root.geometry("800x600")

        # Create tabs
        self.tab_control = ttk.Notebook(root)
        
        # Add Data Tab
        self.add_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.add_tab, text='Add Data')
        
        # View Data Tab
        self.view_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.view_tab, text='View Data')

        # Statistics Tab
        self.stats_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.stats_tab, text='Statistics')

        self.tab_control.pack(expand=1, fill='both')

        # Setup Add Data Tab
        self.setup_add_data_tab()
        self.setup_view_data_tab()
        self.setup_stats_data_tab()

    def setup_add_data_tab(self):
        # Configure font
        self.custom_font = ("Times New Roman", 14)

        # Name Entry
        tk.Label(self.add_tab, text="Name:", font=self.custom_font).grid(row=0, column=0, padx=10, pady=10)
        self.name_entry_add = tk.Entry(self.add_tab, font=self.custom_font)
        self.name_entry_add.grid(row=0, column=1, padx=10, pady=10)
        # Focus on name entry and add tab
        self.add_tab.bind("<Visibility>", lambda e: self.name_entry_add.focus())
        self.name_entry_add.focus_set()

        # Score Entry
        tk.Label(self.add_tab, text="Score:", font=self.custom_font).grid(row=1, column=0, padx=10, pady=10)
        self.score_entry = tk.Entry(self.add_tab, font=self.custom_font)
        self.score_entry.grid(row=1, column=1, padx=10, pady=10)

        # Date Entry (Default to today)
        tk.Label(self.add_tab, text="Date:", font=self.custom_font).grid(row=2, column=0, padx=10, pady=10)
        today = datetime.now().strftime('%Y-%m-%d')
        self.date_entry = tk.Entry(self.add_tab, font=self.custom_font)
        self.date_entry.insert(0, today)
        self.date_entry.grid(row=2, column=1, padx=10, pady=10)

        # Add Button
        add_button = tk.Button(self.add_tab, text="Add Data", font=self.custom_font, command=self.add_data)
        add_button.grid(row=3, column=0, columnspan=2, pady=20)
        self.root.bind('<Return>', lambda event: self.add_data())

    def add_data(self):
        name = self.name_entry_add.get()
        score = self.score_entry.get()
        date = self.date_entry.get()
        print(name, score, date)
        # date format: YYYY-MM-DD
        year, month, day = map(int, date.split('-'))
        print(year, month, day)
        if not all([name, score, date]):
            messagebox.showwarning("Input Error", "Please fill all fields")
            return

        try:
            score = float(score)
        except ValueError:
            messagebox.showwarning("Input Error", "Score must be a number")
            return

        # Add confirmation dialog
        confirm = messagebox.askyesno("Confirm", 
            f"Are you sure you want to add the following data?\n\n" +
            f"Name: {name}\n" +
            f"Score: {score}\n" +
            f"Date: {date}")
        
        if not confirm:
            return

        # using http api instead of direct mysql connection for better security
        url = "http://nghia64582.online/record" 
        # Reading by const { name, score, created_at } = req.body;
        # date format 'dd-mm-yyyy'
        payload = {
            "name": name,
            "score": score,
            "created_at": f"{day:02d}-{month:02d}-{year}"
        }
        response = requests.post(url, json=payload)

        if response.status_code == 201:
            messagebox.showinfo("Success", "Data added successfully")
        else:
            messagebox.showerror("API Error", f"Error adding data: {response.text}")

    def setup_view_data_tab(self):
        self.custom_font = ("Times New Roman", 14)

        style = ttk.Style()
        style.configure('Custom.TRadiobutton', font=self.custom_font)
        style.configure('Custom.Treeview', font=self.custom_font)
        style.configure('Custom.Treeview.Heading', font=self.custom_font)  # <-- Add this line

        # Period Selection Frame
        period_frame = ttk.Frame(self.view_tab)
        period_frame.pack(pady=10)

        # Period Selection
        tk.Label(period_frame, text="Select Period:", font=self.custom_font).pack(side=tk.LEFT, padx=5)
        self.period_var = tk.StringVar(value="week")
        ttk.Radiobutton(period_frame, text="Week", variable=self.period_var, 
                       value="week", style='Custom.TRadiobutton').pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(period_frame, text="Month", variable=self.period_var, 
                       value="month", style='Custom.TRadiobutton').pack(side=tk.LEFT, padx=5)

        # Date Selection Frame
        date_frame = ttk.Frame(self.view_tab)
        date_frame.pack(pady=10)

        # Date Picker
        tk.Label(date_frame, text="Select Date:", font=self.custom_font).pack(side=tk.LEFT, padx=5)
        self.cal = Calendar(date_frame, selectmode='day', date_pattern='yyyy-mm-dd',
                          font=self.custom_font)
        self.cal.pack(pady=10)

        # Search Button
        search_button = tk.Button(self.view_tab, text="Search Data", 
                                font=self.custom_font, command=self.search_data)
        search_button.pack(pady=10)

        # Result Treeview
        self.tree = ttk.Treeview(self.view_tab, columns=("ID", "Name", "Score", "Date"), 
                            show='headings', style='Custom.Treeview')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Score", text="Score")
        self.tree.heading("Date", text="Date")
        self.tree.pack(pady=10, fill=tk.BOTH, expand=True)

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(self.view_tab, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

    def search_data(self):
        def get_first_day_of_period(date, period):
            if period == "week":
                return date - timedelta(days=date.weekday())
            elif period == "month":
                return date.replace(day=1)
            return date

        def get_last_day_of_period(date, period):
            if period == "week":
                return date + timedelta(days=6 - date.weekday())
            elif period == "month":
                next_month = date.replace(day=28) + timedelta(days=4)
                return next_month - timedelta(days=next_month.day)
            return date
        
        selected_date_st = self.cal.get_date()
        selected_date = datetime.strptime(selected_date_st, '%Y-%m-%d')
        period = self.period_var.get()
        # const startDate = moment(startTimeStr, 'DD-MM-YYYY').startOf('day').format('YYYY-MM-DD HH:mm:ss');
        # const endDate = moment(endTimeStr, 'DD-MM-YYYY').endOf('day').format('YYYY-MM-DD HH:mm:ss');

        start_date = get_first_day_of_period(selected_date, period)
        start_date_str = start_date.strftime('%d-%m-%Y')
        end_date = get_last_day_of_period(selected_date, period)
        end_date_str = end_date.strftime('%d-%m-%Y')
        print(start_date_str, end_date_str)
        # Using http instead of directly mysql connection
        # endpoint = "http://nghia64582.online/record", method GET
        # Reading by const { 'start-time': startTimeStr, 'end-time': endTimeStr } = req.query;
        headers = {
            "Content-Type": "application/json"
        }

        response = requests.get(f"http://nghia64582.online/record?start-time={start_date_str}&end-time={end_date_str}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.tree.delete(*self.tree.get_children())
            for date_data in data:
                row = (date_data['id'], date_data['name'], date_data['score'], date_data['created_at'])
                self.tree.insert("", tk.END, values=row)

            # Process the data as needed
        else:
            messagebox.showerror("HTTP Error", f"Error fetching data: {response.status_code}")
    
    def setup_stats_data_tab(self):
        # Main frame for controls (input field and button)
        controls_frame = ttk.Frame(self.stats_tab, padding="10")
        controls_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(controls_frame, text="Enter Name:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.name_entry = ttk.Entry(controls_frame, width=30)
        self.name_entry.pack(side=tk.LEFT, padx=(0, 10))

        get_stats_button = ttk.Button(controls_frame, text="Get Stats", command=self.get_and_display_stats)
        get_stats_button.pack(side=tk.LEFT)

        # Matplotlib chart area
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.stats_tab)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Initial empty plot
        self.ax.set_title("Score vs. Date")
        self.ax.set_xlabel("Date")
        self.ax.set_ylabel("Score")
        self.canvas.draw()

    def get_and_display_stats(self):
        # A simple spinner or message to show that data is being loaded
        loading_label = ttk.Label(self.stats_tab, text="Loading...", foreground="blue")
        loading_label.pack(side=tk.BOTTOM, pady=5)
        
        # Get the name from the entry field
        name = self.name_entry.get()
        if not name:
            loading_label.configure(text="Please enter a name.", foreground="red")
            return

        # Use a separate thread to prevent the GUI from freezing during the network request
        thread = threading.Thread(target=self._fetch_and_plot, args=(name, loading_label))
        thread.start()

    def _fetch_and_plot(self, name, loading_label):
        endpoint = "http://nghia64582.online/record-by-name"
        try:
            params = {'name': name}
            response = requests.get(endpoint, params=params)
            response.raise_for_status() # Raise an exception for bad status codes
            
            data = response.json()
            
            # Update the UI with the fetched data
            self.root.after(0, self._update_plot_with_data, data, loading_label)

        except requests.exceptions.RequestException as e:
            self.root.after(0, lambda: loading_label.configure(text=f"Request failed: {e}", foreground="red"))
        except json.JSONDecodeError:
            self.root.after(0, lambda: loading_label.configure(text="Invalid JSON response.", foreground="red"))

    def _update_plot_with_data(self, data, loading_label):
        loading_label.destroy()

        if not data:
            self.ax.clear()
            self.ax.set_title("No Data Found")
            self.ax.set_xlabel("Date")
            self.ax.set_ylabel("Score")
            self.canvas.draw()
            return

        # Convert the JSON data to a Pandas DataFrame
        df = pd.DataFrame(data)

        # Convert 'created_at' to datetime objects for plotting
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Sort the data by date to ensure the chart is in chronological order
        df = df.sort_values(by='created_at')

        # Clear the previous plot and draw the new one
        self.ax.clear()
        
        self.ax.plot(df['created_at'], df['score'], marker='o', linestyle='-')

        self.ax.set_title(f"Score History for {df['name'].iloc[0]}")
        self.ax.set_xlabel("Date")
        self.ax.set_ylabel("Score")
        
        # Adjust layout and redraw the canvas
        self.fig.autofmt_xdate()
        self.fig.tight_layout()
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = ExtraunaryManager(root)
    root.mainloop()