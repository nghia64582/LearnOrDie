import tkinter as tk
from tkinter import ttk

def create_hierarchy_tree(root):
    # Create a Treeview widget
    tree = ttk.Treeview(root)
    tree.pack(pady=10, padx=10, fill="both", expand=True)

    # Define columns (optional, for tabular data)
    # tree["columns"] = ("col1", "col2")
    # tree.heading("#0", text="Hierarchy") # Default column for tree structure
    # tree.heading("col1", text="Value 1")
    # tree.heading("col2", text="Value 2")

    # Add root items
    parent1 = tree.insert("", "end", text="Parent 1", open=True)
    parent2 = tree.insert("", "end", text="Parent 2", open=True)

    # Add children to Parent 1
    child1_1 = tree.insert(parent1, "end", text="Child 1.1")
    child1_2 = tree.insert(parent1, "end", text="Child 1.2", open=True)

    # Add grand-children to Child 1.2
    tree.insert(child1_2, "end", text="Grandchild 1.2.1")
    tree.insert(child1_2, "end", text="Grandchild 1.2.2")

    # Add children to Parent 2
    tree.insert(parent2, "end", text="Child 2.1")
    child2_2 = tree.insert(parent2, "end", text="Child 2.2")

    # Add a custom icon (optional, requires an image file)
    # try:
    #     folder_icon = tk.PhotoImage(file="folder_icon.png") # Make sure folder_icon.png exists
    #     tree.insert(parent2, "end", text="Child with Icon", image=folder_icon)
    # except tk.TclError:
    #     print("Could not load folder_icon.png. Make sure the file exists.")

    # You can also add values to columns if defined
    # tree.insert(parent1, "end", text="Item with values", values=("Value A", "Value B"))

    return tree


if __name__ == "__main__":
    app = tk.Tk()
    app.title("Hierarchy Treeview Example")
    app.geometry("400x300")

    tree_widget = create_hierarchy_tree(app)

    app.mainloop()