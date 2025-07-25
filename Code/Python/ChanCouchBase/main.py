import tkinter as tk
from tkinter import ttk, messagebox
from model_keys import load_model_keys
from api_client import get_data, put_data, login
from utils import *
from tkinter import font
import json
import trace
import datetime

class DataTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Couchbase Data Tool")

        self.model_keys = load_model_keys()
        self.custom_font = font.Font(family="Times New Roman", size=14)
        self.get_dict_users()
        self.create_widgets()
        self.login()

    def create_widgets(self):
        # Configure column and row weights
        tk.Button(self.root, text="Login", command=self.login, font=self.custom_font, bd=2, relief="solid").grid(row=0, column=0, columnspan=2, sticky="ew")

        # Row 0: Bucket Label and Entry
        tk.Label(self.root, text="Bucket:", font=self.custom_font).grid(row=1, column=0, sticky="ew")
        self.bucket_entry = ttk.Combobox(self.root, values=["acc", "fodi"], font=self.custom_font)
        self.bucket_entry.grid(row=1, column=1, sticky="ew")
        self.bucket_entry.set("acc")  # Default bucket

        # Then move User ID and below down one row
        tk.Label(self.root, text="User ID:", font=self.custom_font).grid(row=2, column=0, sticky="ew")
        self.uid_entry = ttk.Combobox(self.root, values=list(self.users.keys()), font=self.custom_font)
        self.uid_entry.grid(row=2, column=1, sticky="ew")

        tk.Label(self.root, text="Model:", font=self.custom_font).grid(row=3, column=0, sticky="ew")
        self.model_dropdown = ttk.Combobox(self.root, values=list(self.model_keys.keys()), font=self.custom_font)
        self.model_dropdown.grid(row=3, column=1, sticky="ew")
        # set callback when model_dropdown changes
        self.model_dropdown.bind("<<ComboboxSelected>>", lambda event: self.raw_text.delete("1.0", tk.END))

        tk.Button(self.root, text="Read", command=self.read_data, font=self.custom_font, bd=2, relief="solid").grid(row=4, column=0, sticky="ew")
        tk.Button(self.root, text="Write", command=self.write_data, font=self.custom_font, bd=2, relief="solid").grid(row=4, column=1, sticky="ew")

        self.root.bind('<Control-z>', lambda event: self.raw_text.edit_undo())
        self.root.bind('<Control-Return>', lambda event: self.write_data())
        self.root.bind('<Return>', lambda event: self.read_data())

        self.raw_text = tk.Text(self.root, height=10, font=self.custom_font)
        self.raw_text.grid(row=5, column=0, columnspan=2, sticky="nsew")
        tk.Button(self.root, text="Copy Raw", command=lambda: self.copy_to_clipboard(self.raw_text), font=self.custom_font, bd=2, relief="solid").grid(row=6, column=0, columnspan=1, sticky="ew")

        self.normalized_text = tk.Text(self.root, height=10, font=self.custom_font)
        self.normalized_text.grid(row=7, column=0, columnspan=2, sticky="nsew")
        tk.Button(self.root, text="Copy Normalized", command=lambda: self.copy_to_clipboard(self.normalized_text), font=self.custom_font, bd=2, relief="solid").grid(row=8, column=0, columnspan=1, sticky="ew")

        tk.Button(self.root, text="Convert Normalized to Raw", command=lambda: self.convert_normal_to_raw(), font=self.custom_font, bd=2, relief="solid").grid(row=8, column=1, columnspan=1, sticky="ew")

        # Add 7 text fields, 6 for time numbers (year, month, day, hour, minute, second) and 1 for timestamp in second
        self.time_fields = {}
        time_labels = ["Year", "Month", "Day", "Hour", "Minute", "Second", "Timestamp"]
        for i, label in enumerate(time_labels):
            tk.Label(self.root, text=label + ":", font=self.custom_font).grid(row=9 + i, column=0, sticky="ew")
            self.time_fields[label.lower()] = tk.Entry(self.root, font=self.custom_font)
            self.time_fields[label.lower()].grid(row=9 + i, column=1, sticky="ew")
        # Set default values for time fields
        self.time_fields['year'].insert(0, "2025")
        self.time_fields['month'].insert(0, "10")
        self.time_fields['day'].insert(0, "01")
        self.time_fields['hour'].insert(0, "0")
        self.time_fields['minute'].insert(0, "00")
        self.time_fields['second'].insert(0, "00")
        self.time_fields['timestamp'].insert(0, "1709200000")  # Default timestamp for 2025-10-01 00:00:00

        # Setup auto calculate timestamp after edit time
        for field in ['year', 'month', 'day', 'hour', 'minute', 'second']:
            self.time_fields[field].bind("<KeyRelease>", lambda event: self.update_timestamp(event, "timestamp"))
        # Auto calculate datetime when the timestamp field is edited
        self.time_fields['timestamp'].bind("<KeyRelease>", lambda event: self.update_timestamp(event, "datetime"))

    def update_timestamp(self, event, type):
        if type == "timestamp":
            # If input is invalid, show timestamp as "invalid"
            try:
                year = int(self.time_fields['year'].get())
                month = int(self.time_fields['month'].get())
                day = int(self.time_fields['day'].get())
                hour = int(self.time_fields['hour'].get())
                minute = int(self.time_fields['minute'].get())
                second = int(self.time_fields['second'].get())
                timestamp = int(datetime.datetime(year, month, day, hour, minute, second).timestamp())
                self.time_fields['timestamp'].delete(0, tk.END)
                self.time_fields['timestamp'].insert(0, str(timestamp))
            except ValueError:
                self.time_fields['timestamp'].delete(0, tk.END)
                self.time_fields['timestamp'].insert(0, "invalid")
        elif type == "datetime":
            # If timestamp is valid, update the date and time fields
            try:
                timestamp = int(self.time_fields['timestamp'].get())
                dt = datetime.datetime.fromtimestamp(timestamp)
                self.time_fields['year'].delete(0, tk.END)
                self.time_fields['year'].insert(0, str(dt.year))
                self.time_fields['month'].delete(0, tk.END)
                self.time_fields['month'].insert(0, str(dt.month).zfill(2))
                self.time_fields['day'].delete(0, tk.END)
                self.time_fields['day'].insert(0, str(dt.day).zfill(2))
                self.time_fields['hour'].delete(0, tk.END)
                self.time_fields['hour'].insert(0, str(dt.hour).zfill(2))
                self.time_fields['minute'].delete(0, tk.END)
                self.time_fields['minute'].insert(0, str(dt.minute).zfill(2))
                self.time_fields['second'].delete(0, tk.END)
                self.time_fields['second'].insert(0, str(dt.second).zfill(2))
            except ValueError:
                pass

    def login(self):
        login()

    def copy_to_clipboard(self, widget):
        self.root.clipboard_clear()
        self.root.clipboard_append(widget.get("1.0", tk.END))

    def convert_normal_to_raw(self):
        data = json.loads(self.normalized_text.get("1.0", tk.END))
        raw_data = minify_json(data, self.model_keys[self.model_dropdown.get()])
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert(tk.END, json.dumps(raw_data, indent=4))

    def read_data(self):
        uid = self.uid_entry.get()
        uid = self.users.get(uid, uid)
        model_name = self.model_dropdown.get()
        bucket = self.bucket_entry.get()
        model_key = self.model_keys.get(model_name, model_name)
        try:
            response = get_data(model_key, int(uid), bucket)
            data = response.get("json", {})
            data_json = json.dumps(data, indent=4, ensure_ascii=False)
            self.raw_text.delete("1.0", tk.END)
            self.raw_text.insert(tk.END, data_json)
            # If you have a mapping, normalize here
            normalized = normalize_json(data, model_key)  # Supply a real mapping if needed
            self.normalized_text.delete("1.0", tk.END)
            self.normalized_text.insert(tk.END, json.dumps(normalized, indent=4, ensure_ascii=False))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def write_data(self):
        uid = self.uid_entry.get()
        uid = self.users.get(uid, uid)
        model = self.model_dropdown.get()
        model = self.model_keys.get(model, model)
        bucket = self.bucket_entry.get()
        try:
            data = json.loads(self.raw_text.get("1.0", tk.END))
            result = put_data(model, int(uid), data, bucket=bucket)
            messagebox.showinfo("Success", "Data updated!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
   
    def get_dict_users(self):
        # read "uids.txt" and return dict
        self.users = {}
        try:
            with open("uids.txt", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or '-' not in line:
                        continue
                    uid, username = line.split('-', 1)
                    self.users[uid] = username
        except FileNotFoundError:
            messagebox.showerror("Error", "uids.txt file not found.")
    
if __name__ == "__main__":
    root = tk.Tk()
    app = DataTool(root)
    root.mainloop()
