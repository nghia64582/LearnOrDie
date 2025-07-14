import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
from tkcalendar import Calendar

class ExtraunaryManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Management System")
        self.root.geometry("800x600")

        # MySQL Configuration
        self.db_config = {
            'host': 'nghia64582.online',
            'user': 'qrucoqmt_nghia64582',
            'password': 'Nghi@131299',
            'database': 'qrucoqmt_nghia64582'
        }

        # Create tabs
        self.tab_control = ttk.Notebook(root)
        
        # Add Data Tab
        self.add_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.add_tab, text='Add Data')
        
        # View Data Tab
        self.view_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.view_tab, text='View Data')
        
        self.tab_control.pack(expand=1, fill='both')

        # Setup Add Data Tab
        self.setup_add_data_tab()
        self.setup_view_data_tab()

    def setup_add_data_tab(self):
        # Configure font
        self.custom_font = ("Times New Roman", 14)

        # Name Entry
        tk.Label(self.add_tab, text="Name:", font=self.custom_font).grid(row=0, column=0, padx=10, pady=10)
        self.name_entry = tk.Entry(self.add_tab, font=self.custom_font)
        self.name_entry.grid(row=0, column=1, padx=10, pady=10)

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

    def connect_to_database(self):
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            messagebox.showerror("Database Error", f"Error connecting to database: {e}")
            return None

    def add_data(self):
        name = self.name_entry.get()
        score = self.score_entry.get()
        date = self.date_entry.get()
        # date format: YYYY-MM-DD
        year, month, day = map(int, date.split('-'))
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

        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                query = "INSERT INTO extraunary (name, score, year, month, day) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (name, score, year, month, day))
                connection.commit()
                messagebox.showinfo("Success", "Data added successfully")
                
                # Clear entries
                self.name_entry.delete(0, tk.END)
                self.score_entry.delete(0, tk.END)
                self.date_entry.delete(0, tk.END)
                self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                
            except Error as e:
                messagebox.showerror("Database Error", f"Error adding data: {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()

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
        start_date = get_first_day_of_period(selected_date, period)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date = get_last_day_of_period(selected_date, period)
        end_date_str = end_date.strftime('%Y-%m-%d')
        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                query = "SELECT id, name, score, created_at FROM extraunary WHERE created_at BETWEEN %s AND %s;"
                cursor.execute(query, (start_date_str, end_date_str))
                rows = cursor.fetchall()
                
                # Clear previous results
                self.tree.delete(*self.tree.get_children())

                for row in rows:
                    self.tree.insert("", tk.END, values=row)
                if not rows:
                    messagebox.showinfo("No Results", "No data found for the selected period.")
            except Error as e:
                messagebox.showerror("Database Error", f"Error fetching data: {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
        # Remove these lines as they clear the tree after populating it
        # for item in self.tree.get_children():
        #     self.tree.delete(item)

if __name__ == "__main__":
    root = tk.Tk()
    app = ExtraunaryManager(root)
    root.mainloop()