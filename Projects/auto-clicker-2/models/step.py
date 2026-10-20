from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class StepType(str, Enum):
    WAIT_IMAGE = "wait_image"
    CLICK_IMAGE = "click_image"
    CLICK_COORDINATE = "click_coordinate"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    MOVE_MOUSE = "move_mouse"
    DRAG_MOUSE = "drag_mouse"
    ACTIVATE_WINDOW = "activate_window"
    SET_WINDOW = "set_window"
    MINIMIZE_WINDOW = "minimize_window"

    @property
    def label(self) -> str:
        return {
            StepType.WAIT_IMAGE: "Đợi ảnh",
            StepType.CLICK_IMAGE: "Click ảnh",
            StepType.CLICK_COORDINATE: "Click tọa độ",
            StepType.TYPE_TEXT: "Gõ text",
            StepType.PRESS_KEY: "Gõ phím",
            StepType.MOVE_MOUSE: "Di chuột",
            StepType.DRAG_MOUSE: "Kéo chuột",
            StepType.ACTIVATE_WINDOW: "Mở cửa sổ",
            StepType.SET_WINDOW: "Đặt vị trí cửa sổ",
            StepType.MINIMIZE_WINDOW: "Thu nhỏ cửa sổ",
        }[self]

    @property
    def is_window_step(self) -> bool:
        return self in (StepType.ACTIVATE_WINDOW, StepType.SET_WINDOW, StepType.MINIMIZE_WINDOW)


def default_params(step_type: StepType) -> dict[str, Any]:
    if step_type is StepType.WAIT_IMAGE:
        return {"image_id": "", "timeout_seconds": 10.0, "confidence": 0.8}
    if step_type is StepType.CLICK_IMAGE:
        return {
            "image_id": "",
            "confidence": 0.8,
            "button": "left",
            "clicks": 1,
        }
    if step_type is StepType.CLICK_COORDINATE:
        return {"x": 0, "y": 0, "button": "left", "clicks": 1}
    if step_type is StepType.TYPE_TEXT:
        return {"text": "", "interval": 0.05}
    if step_type is StepType.PRESS_KEY:
        return {"keys": "enter"}
    if step_type is StepType.MOVE_MOUSE:
        return {"x": 0, "y": 0, "duration": 0.2}
    if step_type is StepType.DRAG_MOUSE:
        return {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "button": "left", "duration": 0.5}
    if step_type in (StepType.ACTIVATE_WINDOW, StepType.MINIMIZE_WINDOW):
        return {"title": "", "timeout_seconds": 5.0}
    if step_type is StepType.SET_WINDOW:
        return {
            "title": "",
            "timeout_seconds": 5.0,
            "mode": "position",
            "left": 0,
            "top": 0,
            "width": 800,
            "height": 600,
        }
    raise ValueError(f"Unknown step type: {step_type}")


@dataclass
class Step:
    """Một bước trong workflow."""

    id: str
    type: StepType
    params: dict[str, Any] = field(default_factory=dict)
    note: str = ""

    @classmethod
    def create(cls, step_type: StepType, params: dict[str, Any] | None = None, note: str = "") -> Step:
        merged = default_params(step_type)
        if params:
            merged.update(params)
        return cls(id=str(uuid4()), type=step_type, params=merged, note=note)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "params": dict(self.params),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Step:
        step_type = StepType(data["type"])
        params = default_params(step_type)
        params.update(data.get("params") or {})
        return cls(
            id=data["id"],
            type=step_type,
            params=params,
            note=data.get("note", ""),
        )

    def summary(self, image_lookup: dict[str, str] | None = None) -> str:
        image_lookup = image_lookup or {}
        image_id = str(self.params.get("image_id") or "")
        image_name = image_lookup.get(image_id, "")
        if self.type is StepType.WAIT_IMAGE:
            target = image_name or "chưa chọn ảnh"
            return f"Đợi {target} ({self.params.get('timeout_seconds', 10)}s)"
        if self.type is StepType.CLICK_IMAGE:
            target = image_name or "chưa chọn ảnh"
            return f"Click {target}"
        if self.type is StepType.CLICK_COORDINATE:
            return f"Click ({self.params.get('x', 0)}, {self.params.get('y', 0)})"
        if self.type is StepType.TYPE_TEXT:
            text = str(self.params.get("text", ""))
            preview = text if len(text) <= 24 else text[:21] + "..."
            return f'Gõ text "{preview}"'
        if self.type is StepType.PRESS_KEY:
            return f"Gõ phím {self.params.get('keys', '')}"
        if self.type is StepType.MOVE_MOUSE:
            return f"Di chuột tới ({self.params.get('x', 0)}, {self.params.get('y', 0)})"
        if self.type is StepType.DRAG_MOUSE:
            p = self.params
            return f"Kéo ({p.get('x1', 0)}, {p.get('y1', 0)}) → ({p.get('x2', 0)}, {p.get('y2', 0)})"
        if self.type.is_window_step:
            title = str(self.params.get("title") or "")
            target = f'"{title}"' if title else "chưa chọn cửa sổ"
            if self.type is StepType.ACTIVATE_WINDOW:
                return f"Mở cửa sổ {target}"
            if self.type is StepType.MINIMIZE_WINDOW:
                return f"Thu nhỏ {target}"
            p = self.params
            if p.get("mode") == "maximize":
                return f"Phóng to {target}"
            return f"Đặt {target} {p.get('width', 0)}x{p.get('height', 0)} tại ({p.get('left', 0)}, {p.get('top', 0)})"
        return self.type.label
