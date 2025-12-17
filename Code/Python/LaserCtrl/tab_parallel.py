import tkinter as tk
from tkinter import messagebox


class ParallelTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.font = app.font
        self.build_ui()

    def build_ui(self):
        row = 0

        def add(label):
            nonlocal row
            tk.Label(self, text=label, font=self.font).grid(
                row=row, column=0, sticky="e", padx=5, pady=3
            )
            row += 1

        # -------- Inputs --------

        add("Number of lines:")
        self.entry_n_line = tk.Entry(self, width=30, font=self.font)
        self.entry_n_line.insert(0, "5")
        self.entry_n_line.grid(row=row - 1, column=1)

        add("Distance (mm):")
        self.entry_distance = tk.Entry(self, width=30, font=self.font)
        self.entry_distance.insert(0, "5")
        self.entry_distance.grid(row=row - 1, column=1)

        add("Line length (mm):")
        self.entry_length = tk.Entry(self, width=30, font=self.font)
        self.entry_length.insert(0, "100")
        self.entry_length.grid(row=row - 1, column=1)

        add("Feedrate:")
        self.entry_feedrate = tk.Entry(self, width=30, font=self.font)
        self.entry_feedrate.insert(0, "280")
        self.entry_feedrate.grid(row=row - 1, column=1)

        add("Power:")
        self.entry_power = tk.Entry(self, width=30, font=self.font)
        self.entry_power.insert(0, "1000")
        self.entry_power.grid(row=row - 1, column=1)

        # -------- Button --------

        tk.Button(
            self,
            text="Generate GCODE",
            font=self.font,
            command=self.generate_gcode
        ).grid(row=row, column=1, pady=10)

    # ======================================================

    def generate_gcode(self):
        try:
            n_line = int(self.entry_n_line.get())
            distance = float(self.entry_distance.get())
            length = float(self.entry_length.get())
            feedrate = float(self.entry_feedrate.get())
            power = float(self.entry_power.get())

            if n_line < 1:
                raise ValueError("n_line must be >= 1")

            lines = []

            # ---- Header ----
            lines.append("G90")          # absolute positioning
            lines.append("G21")          # mm
            lines.append(f"F{feedrate}")

            # ---- Generate parallel cuts ----
            for i in range(n_line):
                y = i * distance
                x_start = -1
                x_end = length + 1

                lines.append(f"G0 X{x_start:.3f} Y{y:.3f}")
                lines.append(f"M3 S{int(power)}")
                lines.append(f"G1 X{x_end:.3f} Y{y:.3f}")
                lines.append("M5")

            # ---- Footer ----
            lines.append("G0 X0 Y0")

            with open("cut_plan.gcode", "w") as f:
                f.write("\n".join(lines))

            messagebox.showinfo("OK", "Parallel GCODE generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", str(e))
