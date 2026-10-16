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

    @property
    def label(self) -> str:
        return {
            StepType.WAIT_IMAGE: "Đợi ảnh",
            StepType.CLICK_IMAGE: "Click ảnh",
            StepType.CLICK_COORDINATE: "Click tọa độ",
            StepType.TYPE_TEXT: "Gõ text",
            StepType.PRESS_KEY: "Gõ phím",
        }[self]


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
        return self.type.label
