import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import math

STICKS_FILE = "sticks.txt"

# --- Utility: read/write sticks file ---
def ensure_sample_sticks_file(path=STICKS_FILE):
    if os.path.exists(path):
        return
    sample = [
        "# Format: name,length_mm,width_mm",
        "Classic,100,10",
        "Slim,90,8",
        "Long,150,12",
        "Short,70,10"
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sample))

def load_sticks(path=STICKS_FILE):
    sticks = []
    if not os.path.exists(path):
        return sticks
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) < 3:
                continue
            name = parts[0]
            try:
                length = float(parts[1])
                width = float(parts[2])
            except:
                continue
            sticks.append({"name": name, "length": length, "width": width})
    return sticks

# --- SVG writer ---
def save_rectangle_svg(file_path, rect_length, rect_width):
    """
    Create an SVG in mm units:
    - bottom-left at (0,5)
    - top-right at (rect_length, 5 + rect_width)
    - a tiny alignment line (0,0)-(0,0.1)
    """
    min_x = 0.0
    min_y = 5.0
    max_x = rect_length
    max_y = 5.0 + rect_width
    width_mm = max_x - min_x
    height_mm = max_y - min_y

    # viewBox 0 0 width height in mm; we also flip y to have +y up via transform
    svg = []
    svg.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    svg.append(f'<svg width="{width_mm:.4f}mm" height="{height_mm:.4f}mm" viewBox="0 0 {width_mm:.6f} {height_mm:.6f}" xmlns="http://www.w3.org/2000/svg" version="1.1">')
    # transform to make y positive up and translate to put min_x/min_y at origin of viewbox
    # We want coordinates relative to viewBox 0..width, 0..height.
    # So translate(-min_x, -min_y) then scale(1,-1) translate(0,height_mm)
    svg.append(f'  <g transform="translate(0,{height_mm:.6f}) scale(1,-1) translate({-min_x:.6f},{-min_y:.6f})">')
    stroke = 0.1  # mm stroke width, similar to your earlier code
    svg.append(f'    <rect x="{min_x:.6f}" y="{min_y:.6f}" width="{width_mm:.6f}" height="{height_mm:.6f}" stroke="black" stroke-width="{stroke:.4f}" fill="none" />')
    # small alignment line at (0,0)-(0,0.1)
    svg.append(f'    <line x1="0.000000" y1="0.000000" x2="0.000000" y2="0.100000" stroke="black" stroke-width="{stroke:.4f}" />')
    svg.append("  </g>")
    svg.append("</svg>")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

# --- Main GUI App ---
class PopsicleApp:
    def __init__(self, root):
        self.root = root
        root.title("Popsicle → Rectangle SVG demo")
        root.geometry("820x520")

        ensure_sample_sticks_file(STICKS_FILE)
        self.sticks = load_sticks(STICKS_FILE)  # list of dicts
        # state for last computed results
        self.last_results = []  # list of dicts {stick, usable, count, total_width}

        self._build_ui()

    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tab1 = ttk.Frame(nb)
        nb.add(tab1, text="Rectangle → Sticks")

        # Left: input panel
        left = ttk.Frame(tab1, padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left, text="Rectangle size (mm)", font=("Arial", 11, "bold")).pack(pady=(0,6))
        frm = ttk.Frame(left)
        frm.pack()

        ttk.Label(frm, text="Length (long side) mm:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.length_var = tk.StringVar(value="63")
        ttk.Entry(frm, textvariable=self.length_var, width=12).grid(row=0, column=1, pady=4, padx=6)

        ttk.Label(frm, text="Width (short side) mm:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.width_var = tk.StringVar(value="60")
        ttk.Entry(frm, textvariable=self.width_var, width=12).grid(row=1, column=1, pady=4, padx=6)

        ttk.Button(left, text="Compute for all sticks", command=self.on_compute_all).pack(pady=(8,4), fill=tk.X)
        ttk.Button(left, text="Refresh sticks list", command=self.reload_sticks).pack(pady=(0,8), fill=tk.X)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        ttk.Label(left, text="Selected stick (for SVG)", font=("Arial", 10)).pack(pady=(4,2))
        self.selected_stick_var = tk.StringVar()
        self.stick_combo = ttk.Combobox(left, textvariable=self.selected_stick_var, state="readonly", width=24)
        self._populate_stick_combobox()
        self.stick_combo.pack(pady=4)

        ttk.Button(left, text="Create SVG with selected stick", command=self.on_create_svg_selected).pack(pady=6, fill=tk.X)
        ttk.Button(left, text="Create SVG (generic, no stick)", command=self.on_create_svg_generic).pack(pady=(0,10), fill=tk.X)

        ttk.Label(left, text="Notes:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(6,2))
        notes = ("- Stick usable length = length - 10mm (trim both rounded ends).\n"
                 "- A stick is usable iff usable_length >= rectangle length.\n"
                 "- Count = ceil(rect_width / stick_width).\n"
                 "- SVG bottom-left is at (0,5), top-right at (L, 5+W).")
        ttk.Label(left, text=notes, wraplength=220).pack()

        # Right: results table + preview (simple)
        right = ttk.Frame(tab1, padding=8)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Available sticks (from sticks.txt)", font=("Arial", 11, "bold")).pack(anchor=tk.W)
        self.sticks_tree = ttk.Treeview(right, columns=("len","wid"), show="headings", height=6)
        self.sticks_tree.heading("len", text="Length (mm)")
        self.sticks_tree.heading("wid", text="Width (mm)")
        self.sticks_tree.column("len", width=120, anchor=tk.CENTER)
        self.sticks_tree.column("wid", width=120, anchor=tk.CENTER)
        self.sticks_tree.pack(fill=tk.X, pady=6)
        self._refresh_sticks_tree()

        ttk.Label(right, text="Compute results (per stick type)", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(8,0))
        self.result_tree = ttk.Treeview(right, columns=("usable","count","totalw"), show="headings")
        self.result_tree.heading("usable", text="Usable?")
        self.result_tree.heading("count", text="Count")
        self.result_tree.heading("totalw", text="Total width (mm)")
        self.result_tree.column("usable", width=80, anchor=tk.CENTER)
        self.result_tree.column("count", width=80, anchor=tk.CENTER)
        self.result_tree.column("totalw", width=120, anchor=tk.CENTER)
        self.result_tree.pack(fill=tk.BOTH, expand=True, pady=6)

    def _populate_stick_combobox(self):
        items = [f"{s['name']} (L={s['length']} W={s['width']})" for s in self.sticks]
        self.stick_combo['values'] = items
        if items:
            self.stick_combo.current(0)

    def _refresh_sticks_tree(self):
        for r in self.sticks_tree.get_children():
            self.sticks_tree.delete(r)
        for s in self.sticks:
            self.sticks_tree.insert("", tk.END, values=(s['length'], s['width']), text=s['name'])

    def reload_sticks(self):
        self.sticks = load_sticks(STICKS_FILE)
        self._refresh_sticks_tree()
        self._populate_stick_combobox()
        messagebox.showinfo("Reloaded", f"Loaded {len(self.sticks)} stick types from {STICKS_FILE}")

    def on_compute_all(self):
        try:
            L = float(self.length_var.get())
            W = float(self.width_var.get())
            if L <= 0 or W <= 0:
                raise ValueError("Dimensions must be positive.")
        except Exception as e:
            messagebox.showerror("Input error", f"Invalid rectangle size: {e}")
            return

        self.last_results = []
        for s in self.sticks:
            usable_len = s['length'] - 10.0  # trim both rounded ends
            usable = usable_len >= L - 1e-9
            if usable:
                count = math.ceil(W / s['width'])
                totalw = count * s['width']
            else:
                count = None
                totalw = None
            self.last_results.append({"stick": s, "usable": usable, "count": count, "total_width": totalw})
        self._refresh_results_table()
        messagebox.showinfo("Done", f"Computed for {len(self.sticks)} stick types.")

    def _refresh_results_table(self):
        for r in self.result_tree.get_children():
            self.result_tree.delete(r)
        for res in self.last_results:
            s = res['stick']
            usable = "Yes" if res['usable'] else "No"
            cnt = "-" if res['count'] is None else str(res['count'])
            tot = "-" if res['total_width'] is None else f"{res['total_width']:.2f}"
            label = f"{s['name']} (L={s['length']} W={s['width']})"
            self.result_tree.insert("", tk.END, values=(usable, cnt, tot), text=label)

    def on_create_svg_selected(self):
        # create SVG using currently selected stick type (for naming or for reference)
        try:
            L = float(self.length_var.get())
            W = float(self.width_var.get())
            if L <= 0 or W <= 0:
                raise ValueError("Dimensions must be positive.")
        except Exception as e:
            messagebox.showerror("Input error", f"Invalid rectangle size: {e}")
            return

        sel = self.stick_combo.current()
        if sel < 0 or sel >= len(self.sticks):
            messagebox.showwarning("No stick selected", "Please select a stick type.")
            return
        stick = self.sticks[sel]
        # check usability
        usable_len = stick['length'] - 10.0
        if usable_len < L:
            if not messagebox.askyesno("Stick too short", f"Selected stick usable length {usable_len:.1f} mm is < rectangle length {L:.1f} mm.\nCreate SVG anyway?"):
                return

        # ask where to save
        initial_name = f"rec_{int(L)}_{int(W)}.svg"
        save_path = filedialog.asksaveasfilename(title="Save SVG as", defaultextension=".svg", initialfile=initial_name, filetypes=[("SVG file","*.svg")])
        if not save_path:
            return
        try:
            save_rectangle_svg(save_path, L, W)
            messagebox.showinfo("Saved", f"SVG saved to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save SVG: {e}")

    def on_create_svg_generic(self):
        # same as above but no stick selection, just save
        try:
            L = float(self.length_var.get())
            W = float(self.width_var.get())
            if L <= 0 or W <= 0:
                raise ValueError("Dimensions must be positive.")
        except Exception as e:
            messagebox.showerror("Input error", f"Invalid rectangle size: {e}")
            return
        initial_name = f"rec_{int(L)}_{int(W)}.svg"
        save_path = filedialog.asksaveasfilename(title="Save SVG as", defaultextension=".svg", initialfile=initial_name, filetypes=[("SVG file","*.svg")])
        if not save_path:
            return
        try:
            save_rectangle_svg(save_path, L, W)
            messagebox.showinfo("Saved", f"SVG saved to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save SVG: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("vista")
    except:
        pass
    app = PopsicleApp(root)
    root.mainloop()
