import tkinter as tk
from tkinter import ttk
import random as rd

# -------- DATA --------

def generate_random_tree():
    data = {"n_0": []}
    for i in range(1, 100):
        parent = f"n_{rd.randint(0, i - 1)}"
        node = f"n_{i}"
        data.setdefault(parent, []).append(node)
        data[node] = []
    return data

DATA = generate_random_tree()

# -------- UI --------

root = tk.Tk()
root.geometry("500x600")

tree = ttk.Treeview(root, columns=("action",))
tree.heading("#0", text="Node")
tree.heading("action", text="Action")
tree.pack(expand=True, fill="both")

tree.tag_configure("root", foreground="red", font=("Times New Roman", 12))
tree.tag_configure("leaf", foreground="gray", font=("Times New Roman", 12))
tree.tag_configure("normal", foreground="black", font=("Times New Roman", 12))

# -------- LAZY LOAD --------

def insert_node(parent, node):
    tags = ()
    if node == "n_0":
        tags = ("root",)
    else:
        tags = ("leaf",)

    item = tree.insert(parent, "end", text=node, values=("Edit",), tags=tags)

    if DATA[node]:
        tree.insert(item, "end")  # dummy

def on_open(event):
    item = tree.focus()
    children = tree.get_children(item)
    if len(children) == 1 and tree.item(children[0], "text") == "":
        tree.delete(children[0])
        node = tree.item(item, "text")
        for c in DATA[node]:
            insert_node(item, c)

tree.bind("<<TreeviewOpen>>", on_open)

# -------- ACTION COLUMN --------

def on_click(event):
    region = tree.identify("region", event.x, event.y)
    if region == "cell":
        col = tree.identify_column(event.x)
        if col == "#1":
            item = tree.focus()
            print("Edit node:", tree.item(item, "text"))

tree.bind("<Button-1>", on_click)

# -------- OPEN / CLOSE --------

def open_all(item=""):
    for c in tree.get_children(item):
        tree.item(c, open=True)
        open_all(c)

def close_all(item=""):
    for c in tree.get_children(item):
        tree.item(c, open=False)
        close_all(c)

# -------- BUTTONS --------

btns = tk.Frame(root)
btns.pack(fill="x")

tk.Button(btns, text="Open All", command=open_all).pack(side="left")
tk.Button(btns, text="Close All", command=close_all).pack(side="left")

# -------- INIT --------

insert_node("", "n_0")

root.mainloop()
