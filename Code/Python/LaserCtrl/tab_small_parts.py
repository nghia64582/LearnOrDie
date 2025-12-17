import tkinter as tk
from tkinter import messagebox
from typing import List

from cut_plan_builder import *
from extended_cut_export import *


class SmallPartsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.font = app.font
        self.build_ui()

    def build_ui(self):
        row = 0

        def add(label):
            nonlocal row
            tk.Label(self, text=label, font=self.font).grid(row=row, column=0, sticky="e")
            row += 1

        add("Stock Length (mm):")
        self.entry_stock_length = tk.Entry(self, width=40, font=self.font)
        self.entry_stock_length.insert(0, "100")
        self.entry_stock_length.grid(row=row-1, column=1)

        add("Width (mm):")
        self.entry_width = tk.Entry(self, width=40, font=self.font)
        self.entry_width.insert(0, "10")
        self.entry_width.grid(row=row-1, column=1)

        add("Gap (mm):")
        self.entry_gap = tk.Entry(self, width=40, font=self.font)
        self.entry_gap.insert(0, "5")
        self.entry_gap.grid(row=row-1, column=1)

        add("Hole Radius (mm):")
        self.entry_hole_radius = tk.Entry(self, width=40, font=self.font)
        self.entry_hole_radius.insert(0, "1.5")
        self.entry_hole_radius.grid(row=row-1, column=1)

        add("Feedrate:")
        self.entry_feedrate = tk.Entry(self, width=40, font=self.font)
        self.entry_feedrate.insert(0, "280")
        self.entry_feedrate.grid(row=row-1, column=1)

        add("Power:")
        self.entry_power = tk.Entry(self, width=40, font=self.font)
        self.entry_power.insert(0, "1000")
        self.entry_power.grid(row=row-1, column=1)

        add("Parts:")
        self.text_parts = tk.Text(self, width=40, height=8, font=self.font)
        self.text_parts.grid(row=row-1, column=1)

        tk.Button(
            self, text="Generate GCODE", font=self.font,
            command=self.on_generate
        ).grid(row=row, column=1, pady=10)

    def on_generate(self):
        try:
            parts = self.convert_text_to_parts(
                self.text_parts.get("1.0", tk.END)
            )

            cut_plan = build_cut_plan(
                stock_length=float(self.entry_stock_length.get()),
                parts=parts,
                width=float(self.entry_width.get()),
                gap=float(self.entry_gap.get()),
                hole_radius=float(self.entry_hole_radius.get())
            )

            export_gcode_extended(
                cut_plan,
                "cut_plan.gcode",
                feedrate=float(self.entry_feedrate.get()),
                power=float(self.entry_power.get())
            )

            messagebox.showinfo("OK", "GCODE generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def convert_text_to_parts(self, txt: str) -> List[Part]:
        parts = []
        for line in txt.strip().splitlines():
            t = [x.strip() for x in line.split(",")]
            parts.append(Part(
                length=float(t[0]),
                is_cut_down=bool(int(t[1])),
                is_cut_up=bool(int(t[2])),
                hole_centers=[float(x) for x in t[3:]]
            ))
        return parts
