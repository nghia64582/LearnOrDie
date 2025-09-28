import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("Modern Tkinter App")

style = ttk.Style(root)
root.tk.call("source", "azure.tcl")  # tải file theme azure.tcl
style.theme_use("azure")             # dùng theme azure

# Nếu muốn dark mode
# style.theme_use("azure-dark")

ttk.Button(root, text="Click me").pack(padx=20, pady=20)
root.mainloop()
