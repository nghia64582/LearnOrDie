from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from models.step import StepType
from models.workflow import Workflow

NODE_COLORS = {
    StepType.WAIT_IMAGE: "#e8f4fc",
    StepType.CLICK_IMAGE: "#e7f6ed",
    StepType.CLICK_COORDINATE: "#fff4e5",
    StepType.TYPE_TEXT: "#f3e8ff",
    StepType.PRESS_KEY: "#fde8ef",
}

NODE_WIDTH = 220
NODE_HEIGHT = 68
NODE_X = 36


class WorkflowCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc, on_select: Callable[[str], None]) -> None:
        super().__init__(
            master,
            background="#f4f6f8",
            highlightthickness=1,
            highlightbackground="#c5c9d0",
        )
        self._on_select = on_select
        self._step_boxes: list[tuple[str, int, int, int, int]] = []
        self.bind("<Button-1>", self._on_click)

    def render(
        self,
        workflow: Workflow | None,
        selected_id: str | None,
        image_lookup: dict[str, str],
        running_id: str | None = None,
        completed_ids: set[str] | None = None,
        failed_id: str | None = None,
    ) -> None:
        self.delete("all")
        self._step_boxes = []
        if workflow is None or not workflow.steps:
            self.create_text(
                16,
                16,
                anchor="nw",
                fill="#667085",
                font=("Segoe UI", 10),
                text="Chưa có bước nào.\nThêm bước để thiết kế workflow.",
            )
            self.configure(scrollregion=(0, 0, 280, 120))
            return

        completed_ids = completed_ids or set()
        for index, step in enumerate(workflow.steps):
            x1 = NODE_X
            y1 = 20 + index * 96
            x2 = x1 + NODE_WIDTH
            y2 = y1 + NODE_HEIGHT
            fill = NODE_COLORS.get(step.type, "#ffffff")
            if step.id == failed_id:
                fill, outline, width = "#fee4e2", "#d92d20", 3
            elif step.id == running_id:
                fill, outline, width = "#fef0c7", "#dc6803", 3
            elif step.id in completed_ids:
                outline, width = "#12b76a", 2
            elif step.id == selected_id:
                outline, width = "#1d4ed8", 3
            else:
                outline, width = "#98a2b3", 1
            self.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)
            self.create_text(
                x1 + 12,
                y1 + 12,
                anchor="nw",
                font=("Segoe UI", 9, "bold"),
                text=f"{index + 1}. {step.type.label}",
            )
            self.create_text(
                x1 + 12,
                y1 + 34,
                anchor="nw",
                font=("Segoe UI", 9),
                width=NODE_WIDTH - 24,
                text=step.summary(image_lookup),
            )
            self._step_boxes.append((step.id, x1, y1, x2, y2))
            if index < len(workflow.steps) - 1:
                self.create_line(
                    (x1 + x2) / 2,
                    y2,
                    (x1 + x2) / 2,
                    y2 + 28,
                    arrow=tk.LAST,
                    fill="#667085",
                )

        bottom = 20 + len(workflow.steps) * 96 + 20
        self.configure(scrollregion=(0, 0, NODE_X + NODE_WIDTH + 40, bottom))

    def _on_click(self, event: tk.Event) -> None:
        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)
        for step_id, x1, y1, x2, y2 in self._step_boxes:
            if x1 <= canvas_x <= x2 and y1 <= canvas_y <= y2:
                self._on_select(step_id)
                return
