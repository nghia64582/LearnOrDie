from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ImageAsset:
    """Hình ảnh mẫu dùng cho bước đợi ảnh / click ảnh."""

    id: str
    name: str
    filename: str
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def create(cls, name: str, filename: str) -> ImageAsset:
        now = utc_now_iso()
        return cls(
            id=str(uuid4()),
            name=name,
            filename=filename,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "filename": self.filename,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ImageAsset:
        return cls(
            id=data["id"],
            name=data["name"],
            filename=data["filename"],
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", data.get("created_at", utc_now_iso())),
        )

    def file_path(self, images_dir: Path) -> Path:
        return images_dir / self.filename
