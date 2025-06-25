import tkinter as tk
from tkinter import ttk, messagebox
from model_keys import load_model_keys
from api_client import get_data, put_data, login
from utils import normalize_json
from tkinter import font
import json

class DataTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Couchbase Data Tool")

        self.model_keys = load_model_keys()
        self.custom_font = font.Font(family="Consolas", size=16)
        self.create_widgets()

    def create_widgets(self):
        # Configure column and row weights
        tk.Button(self.root, text="Login", command=self.login, font=self.custom_font, bd=2, relief="solid").grid(row=0, column=0, columnspan=2, sticky="ew")

        # Row 0: Bucket Label and Entry
        tk.Label(self.root, text="Bucket:", font=self.custom_font).grid(row=1, column=0, sticky="ew")
        self.bucket_entry = tk.Entry(self.root, font=self.custom_font)
        self.bucket_entry.grid(row=1, column=1, sticky="ew")

        # Then move User ID and below down one row
        tk.Label(self.root, text="User ID:", font=self.custom_font).grid(row=2, column=0, sticky="ew")
        self.uid_entry = tk.Entry(self.root, font=self.custom_font)
        self.uid_entry.grid(row=2, column=1, sticky="ew")

        tk.Label(self.root, text="Model:", font=self.custom_font).grid(row=3, column=0, sticky="ew")
        self.model_dropdown = ttk.Combobox(self.root, values=list(self.model_keys.keys()), font=self.custom_font)
        self.model_dropdown.grid(row=3, column=1, sticky="ew")

        tk.Button(self.root, text="Read", command=self.read_data, font=self.custom_font, bd=2, relief="solid").grid(row=4, column=0, sticky="ew")
        tk.Button(self.root, text="Write", command=self.write_data, font=self.custom_font, bd=2, relief="solid").grid(row=4, column=1, sticky="ew")

        self.raw_text = tk.Text(self.root, height=10, font=self.custom_font)
        self.raw_text.grid(row=5, column=0, columnspan=2, sticky="nsew")
        tk.Button(self.root, text="Copy Raw", command=lambda: self.copy_to_clipboard(self.raw_text), font=self.custom_font, bd=2, relief="solid").grid(row=6, column=0, columnspan=2, sticky="ew")

        self.normalized_text = tk.Text(self.root, height=10, font=self.custom_font)
        self.normalized_text.grid(row=7, column=0, columnspan=2, sticky="nsew")
        tk.Button(self.root, text="Copy Normalized", command=lambda: self.copy_to_clipboard(self.normalized_text), font=self.custom_font, bd=2, relief="solid").grid(row=8, column=0, columnspan=2, sticky="ew")

        # Update row weights to match new layout
        self.root.grid_rowconfigure(4, weight=1)
        self.root.grid_rowconfigure(6, weight=1)

    def login(self):
        login()

    def copy_to_clipboard(self, widget):
        self.root.clipboard_clear()
        self.root.clipboard_append(widget.get("1.0", tk.END))

    def read_data(self):
        uid = self.uid_entry.get()
        model = self.model_dropdown.get()
        try:
            data = get_data(self.model_keys[model], int(uid), "acc")["json"]
            data_json = json.dumps(data, indent=4)
            self.raw_text.delete("1.0", tk.END)
            self.raw_text.insert(tk.END, data_json)
            # If you have a mapping, normalize here
            normalized = normalize_json(data, {})  # Supply a real mapping if needed
            self.normalized_text.delete("1.0", tk.END)
            self.normalized_text.insert(tk.END, json.dumps(normalized, indent=4))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def write_data(self):
        uid = self.uid_entry.get()
        model = self.model_dropdown.get()
        try:
            data = eval(self.raw_text.get("1.0", tk.END))  # Consider using `json.loads` for safety
            result = put_data(self.model_keys[model], int(uid), data, "acc")
            messagebox.showinfo("Success", "Data updated!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = DataTool(root)
    root.mainloop()
