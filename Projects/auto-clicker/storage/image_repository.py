"""Repository for managing workflow reference images and metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import uuid

from PIL import Image

from storage.workflow_repository import sanitize_filename


@dataclass
class ImageItem:
    """Metadata for a managed image asset."""

    id: str
    name: str
    filename: str
    file_path: Path
    created_at: str
    width: int = 0
    height: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "filename": self.filename,
            "created_at": self.created_at,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_dir: Path) -> ImageItem:
        filename = data.get("filename", "")
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            filename=filename,
            file_path=base_dir / filename,
            created_at=data.get("created_at", ""),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
        )


class ImageRepository:
    """Handles storing, loading, and indexing reference images."""

    def __init__(self, base_dir: Path | str = "data/images") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_dir / "images.json"
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not self.index_file.exists():
            self.index_file.write_text("[]", encoding="utf-8")

    def _read_index(self) -> list[dict[str, Any]]:
        try:
            content = self.index_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_index(self, items: list[dict[str, Any]]) -> None:
        temp_file = self.base_dir / f".tmp_{uuid.uuid4().hex}_images.json"
        try:
            temp_file.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
            temp_file.replace(self.index_file)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

    def list_images(self) -> list[ImageItem]:
        """List all indexed images that physically exist on disk."""
        data = self._read_index()
        results: list[ImageItem] = []
        for d in data:
            item = ImageItem.from_dict(d, self.base_dir)
            if item.file_path.is_file():
                results.append(item)
        return results

    def get_image(self, image_id: str) -> Optional[ImageItem]:
        """Get image metadata by ID."""
        for item in self.list_images():
            if item.id == image_id:
                return item
        return None

    def save_image(
        self,
        img: Image.Image,
        name: str,
        custom_id: Optional[str] = None,
    ) -> ImageItem:
        """Save a PIL Image instance to the repository with metadata."""
        clean_name = name.strip() or "Untitled Image"
        slug = sanitize_filename(clean_name)
        image_id = custom_id.strip() if custom_id and custom_id.strip() else f"img_{slug}_{uuid.uuid4().hex[:6]}"

        # Prevent duplicate ID collision
        existing_items = self.list_images()
        if any(item.id == image_id for item in existing_items):
            image_id = f"{image_id}_{uuid.uuid4().hex[:4]}"

        filename = f"{image_id}.png"
        file_path = self.base_dir / filename

        # Save image file as PNG
        img.save(file_path, format="PNG")
        w, h = img.size

        item = ImageItem(
            id=image_id,
            name=clean_name,
            filename=filename,
            file_path=file_path,
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            width=w,
            height=h,
        )

        # Update index
        data = self._read_index()
        data.append(item.to_dict())
        self._write_index(data)

        return item

    def delete_image(self, image_id: str) -> bool:
        """Delete an image file and remove it from the index."""
        data = self._read_index()
        found = False
        new_data: list[dict[str, Any]] = []

        for d in data:
            if d.get("id") == image_id:
                found = True
                filename = d.get("filename", "")
                fpath = self.base_dir / filename
                if fpath.is_file():
                    try:
                        fpath.unlink()
                    except OSError:
                        pass
            else:
                new_data.append(d)

        if found:
            self._write_index(new_data)
        return found
