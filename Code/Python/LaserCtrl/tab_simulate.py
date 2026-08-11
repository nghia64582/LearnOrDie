import tkinter as tk
from tkinter import ttk, filedialog
import re

class TabSimulate(ttk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app

        # --------------------------------------------------
        # Data
        # --------------------------------------------------

        self.steps = []
        self.current_step = 0

        self.min_x = 0
        self.max_x = 100
        self.min_y = 0
        self.max_y = 100

        # --------------------------------------------------
        # Layout
        # --------------------------------------------------

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Canvas bên trái
        canvas_frame = ttk.Frame(self)
        canvas_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=5,
            pady=5
        )

        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_frame,
            background="white"
        )

        self.canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # --------------------------------------------------
        # Control panel bên phải
        # --------------------------------------------------

        control = ttk.Frame(self, width=250)

        control.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=10,
            pady=10
        )

        # Không cho panel bị co
        control.grid_propagate(False)

        # --------------------------------------------------
        # File
        # --------------------------------------------------

        ttk.Label(
            control,
            text="G-code"
        ).pack(anchor="w")

        file_frame = ttk.Frame(control)
        file_frame.pack(
            fill="x",
            pady=(3, 10)
        )

        self.file_var = tk.StringVar(
            value="cut_plan.gcode"
        )

        self.file_entry = ttk.Entry(
            file_frame,
            textvariable=self.file_var
        )

        self.file_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            file_frame,
            text="...",
            width=3,
            command=self.select_file
        ).pack(
            side="right",
            padx=(5, 0)
        )

        ttk.Button(
            control,
            text="Load G-code",
            command=self.load_gcode
        ).pack(
            fill="x",
            pady=(0, 15)
        )

        # --------------------------------------------------
        # Step info
        # --------------------------------------------------

        ttk.Label(
            control,
            text="Simulation"
        ).pack(anchor="w")

        self.step_label = ttk.Label(
            control,
            text="Step: 0 / 0"
        )

        self.step_label.pack(
            anchor="w",
            pady=(5, 0)
        )

        self.type_label = ttk.Label(
            control,
            text="Type: -"
        )

        self.type_label.pack(
            anchor="w"
        )

        self.command_label = ttk.Label(
            control,
            text="Command: -"
        )

        self.command_label.pack(
            anchor="w"
        )

        self.position_label = ttk.Label(
            control,
            text="Position: (0, 0)"
        )

        self.position_label.pack(
            anchor="w"
        )

        # --------------------------------------------------
        # Navigation buttons
        # --------------------------------------------------

        button_frame = ttk.Frame(control)

        button_frame.pack(
            fill="x",
            pady=20
        )

        self.previous_button = ttk.Button(
            button_frame,
            text="◀ Previous",
            command=self.previous_step
        )

        self.previous_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 3)
        )

        self.next_button = ttk.Button(
            button_frame,
            text="Next ▶",
            command=self.next_step
        )

        self.next_button.pack(
            side="right",
            fill="x",
            expand=True,
            padx=(3, 0)
        )

        # --------------------------------------------------
        # Reset
        # --------------------------------------------------

        ttk.Button(
            control,
            text="Reset",
            command=self.reset_simulation
        ).pack(
            fill="x"
        )

        # --------------------------------------------------
        # Legend
        # --------------------------------------------------

        ttk.Separator(
            control
        ).pack(
            fill="x",
            pady=20
        )

        ttk.Label(
            control,
            text="Legend"
        ).pack(anchor="w")

        ttk.Label(
            control,
            text="━  Cutting (G1)",
            foreground="black"
        ).pack(anchor="w")

        ttk.Label(
            control,
            text="━  Rapid movement (G0)",
            foreground="blue"
        ).pack(anchor="w")

        # --------------------------------------------------
        # Mouse resize
        # --------------------------------------------------

        self.canvas.bind(
            "<Configure>",
            self.on_canvas_resize
        )

    # ======================================================
    # FILE
    # ======================================================

    def select_file(self):

        path = filedialog.askopenfilename(
            title="Select G-code",
            filetypes=[
                ("G-code", "*.gcode"),
                ("Text", "*.txt"),
                ("All files", "*.*")
            ]
        )

        if path:
            self.file_var.set(path)
            self.load_gcode()

    # ======================================================
    # PARSE G-CODE
    # ======================================================

    def load_gcode(self):

        path = self.file_var.get()

        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:

                content = f.read()

        except Exception as e:

            self.show_error(
                f"Cannot open file:\n{e}"
            )

            return

        self.steps = self.parse_gcode(content)

        self.current_step = 0

        self.calculate_bounds()

        self.draw()

        self.update_ui()

    # ======================================================
    # PARSER
    # ======================================================

    def parse_gcode(self, content):

        steps = []

        # Current machine position
        current_x = 0.0
        current_y = 0.0

        lines = content.splitlines()

        for line_number, raw_line in enumerate(lines, start=1):

            line = raw_line.strip()

            if not line:
                continue

            # Remove comments
            line = re.sub(
                r"\(.*?\)",
                "",
                line
            )

            line = re.sub(
                r";.*$",
                "",
                line
            )

            line = line.strip()

            if not line:
                continue

            # ------------------------------------------------
            # G0
            # ------------------------------------------------

            match = re.match(
                r"^G0+\s+(.*)$",
                line,
                re.IGNORECASE
            )

            if match:

                params = match.group(1)

                x = self.extract_axis(
                    params,
                    "X",
                    current_x
                )

                y = self.extract_axis(
                    params,
                    "Y",
                    current_y
                )

                steps.append({
                    "type": "travel",
                    "command": line,
                    "line": line_number,

                    "x1": current_x,
                    "y1": current_y,

                    "x2": x,
                    "y2": y,
                })

                current_x = x
                current_y = y

                continue

            # ------------------------------------------------
            # G1
            # ------------------------------------------------

            match = re.match(
                r"^G1\s+(.*)$",
                line,
                re.IGNORECASE
            )

            if match:

                params = match.group(1)

                x = self.extract_axis(
                    params,
                    "X",
                    current_x
                )

                y = self.extract_axis(
                    params,
                    "Y",
                    current_y
                )

                steps.append({
                    "type": "cut",
                    "command": line,
                    "line": line_number,

                    "x1": current_x,
                    "y1": current_y,

                    "x2": x,
                    "y2": y,
                })

                current_x = x
                current_y = y

                continue

        return steps

    # ======================================================
    # EXTRACT X / Y
    # ======================================================

    def extract_axis(
        self,
        text,
        axis,
        default
    ):

        match = re.search(
            rf"{axis}(-?\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )

        if match:
            return float(match.group(1))

        return default

    # ======================================================
    # BOUNDS
    # ======================================================

    def calculate_bounds(self):

        if not self.steps:

            self.min_x = 0
            self.max_x = 100
            self.min_y = 0
            self.max_y = 100

            return

        xs = []
        ys = []

        for step in self.steps:

            xs.extend([
                step["x1"],
                step["x2"]
            ])

            ys.extend([
                step["y1"],
                step["y2"]
            ])

        self.min_x = min(xs)
        self.max_x = max(xs)

        self.min_y = min(ys)
        self.max_y = max(ys)

        # Tránh width/height = 0
        if self.min_x == self.max_x:

            self.min_x -= 10
            self.max_x += 10

        if self.min_y == self.max_y:

            self.min_y -= 10
            self.max_y += 10

    # ======================================================
    # COORDINATE TRANSFORM
    # ======================================================

    def transform(self, x, y):

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width <= 1:
            width = 800

        if height <= 1:
            height = 600

        margin = 40

        available_width = width - margin * 2
        available_height = height - margin * 2

        data_width = self.max_x - self.min_x
        data_height = self.max_y - self.min_y

        scale_x = available_width / data_width
        scale_y = available_height / data_height

        scale = min(
            scale_x,
            scale_y
        )

        # Center
        drawing_width = data_width * scale
        drawing_height = data_height * scale

        offset_x = (
            width - drawing_width
        ) / 2

        offset_y = (
            height - drawing_height
        ) / 2

        sx = (
            offset_x
            + (x - self.min_x) * scale
        )

        # Canvas Y ngược với tọa độ machine
        sy = (
            offset_y
            + (self.max_y - y) * scale
        )

        return sx, sy

    # ======================================================
    # DRAW
    # ======================================================

    def draw(self):

        self.canvas.delete("all")

        # --------------------------------------------------
        # Draw all executed steps
        # --------------------------------------------------

        for i in range(
            self.current_step
        ):

            step = self.steps[i]

            x1, y1 = self.transform(
                step["x1"],
                step["y1"]
            )

            x2, y2 = self.transform(
                step["x2"],
                step["y2"]
            )

            if step["type"] == "cut":

                self.canvas.create_line(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill="black",
                    width=3
                )

            else:

                self.canvas.create_line(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill="blue",
                    width=2,
                    dash=(6, 4)
                )

        # --------------------------------------------------
        # Current machine position
        # --------------------------------------------------

        if self.current_step > 0:

            step = self.steps[
                self.current_step - 1
            ]

            x, y = self.transform(
                step["x2"],
                step["y2"]
            )

            r = 5

            self.canvas.create_oval(
                x - r,
                y - r,
                x + r,
                y + r,
                fill="red",
                outline=""
            )

    # ======================================================
    # NEXT
    # ======================================================

    def next_step(self):

        if self.current_step >= len(
            self.steps
        ):
            return

        self.current_step += 1

        self.draw()
        self.update_ui()

    # ======================================================
    # PREVIOUS
    # ======================================================

    def previous_step(self):

        if self.current_step <= 0:
            return

        self.current_step -= 1

        self.draw()
        self.update_ui()

    # ======================================================
    # RESET
    # ======================================================

    def reset_simulation(self):

        self.current_step = 0

        self.draw()
        self.update_ui()

    # ======================================================
    # UI
    # ======================================================

    def update_ui(self):

        total = len(self.steps)

        self.step_label.config(
            text=f"Step: {self.current_step} / {total}"
        )

        if self.current_step == 0:

            self.type_label.config(
                text="Type: -"
            )

            self.command_label.config(
                text="Command: -"
            )

            self.position_label.config(
                text="Position: (0.000, 0.000)"
            )

            self.previous_button.config(
                state="disabled"
            )

            if total > 0:
                self.next_button.config(
                    state="normal"
                )
            else:
                self.next_button.config(
                    state="disabled"
                )

            return

        step = self.steps[
            self.current_step - 1
        ]

        if step["type"] == "cut":

            self.type_label.config(
                text="Type: CUT"
            )

        else:

            self.type_label.config(
                text="Type: RAPID"
            )

        self.command_label.config(
            text=f"Command: {step['command']}"
        )

        self.position_label.config(
            text=(
                f"Position: "
                f"({step['x2']:.3f}, "
                f"{step['y2']:.3f})"
            )
        )

        self.previous_button.config(
            state="normal"
        )

        if self.current_step >= total:

            self.next_button.config(
                state="disabled"
            )

        else:

            self.next_button.config(
                state="normal"
            )

    # ======================================================
    # RESIZE
    # ======================================================

    def on_canvas_resize(self, event):

        self.draw()

    # ======================================================
    # ERROR
    # ======================================================

    def show_error(self, message):

        # Không cần messagebox riêng nếu muốn đơn giản.
        # Hiển thị trực tiếp trên canvas.

        self.canvas.delete("all")

        self.canvas.create_text(
            self.canvas.winfo_width() / 2,
            self.canvas.winfo_height() / 2,
            text=message,
            fill="red",
            justify="center"
        )