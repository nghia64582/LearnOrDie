from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.paths import IMAGES_DIR, IMAGES_INDEX, ensure_data_dirs
from models.image import ImageAsset, utc_now_iso

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


class ImageLibrary:
    def __init__(self, images_dir: Path | None = None, index_path: Path | None = None) -> None:
        self.images_dir = images_dir or IMAGES_DIR
        self.index_path = index_path or IMAGES_INDEX
        ensure_data_dirs()
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self._items: list[ImageAsset] = []
        self.reload()

    def reload(self) -> None:
        if not self.index_path.exists():
            self._items = []
            self._save()
            return
        raw = json.loads(self.index_path.read_text(encoding="utf-8"))
        self._items = [ImageAsset.from_dict(item) for item in raw.get("images", [])]

    def all(self) -> list[ImageAsset]:
        return list(self._items)

    def get(self, image_id: str) -> ImageAsset | None:
        return next((item for item in self._items if item.id == image_id), None)

    def add_from_file(self, source: Path, name: str | None = None) -> ImageAsset:
        source = Path(source)
        suffix = source.suffix.lower()
        if suffix not in IMAGE_EXTENSIONS:
            raise ValueError(f"Định dạng ảnh không hỗ trợ: {suffix or '(không có phần mở rộng)'}")
        if not source.is_file():
            raise FileNotFoundError(f"Không tìm thấy file: {source}")

        display_name = name.strip() if name and name.strip() else source.stem
        asset = ImageAsset.create(display_name, "")
        filename = f"{asset.id}{suffix}"
        destination = self.images_dir / filename
        shutil.copy2(source, destination)
        asset.filename = filename
        self._items.append(asset)
        self._save()
        return asset

    def rename(self, image_id: str, name: str) -> ImageAsset:
        asset = self.get(image_id)
        if asset is None:
            raise KeyError(f"Không tìm thấy ảnh: {image_id}")
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Tên ảnh không được để trống")
        asset.name = cleaned
        asset.updated_at = utc_now_iso()
        self._save()
        return asset

    def delete(self, image_id: str) -> None:
        asset = self.get(image_id)
        if asset is None:
            raise KeyError(f"Không tìm thấy ảnh: {image_id}")
        file_path = asset.file_path(self.images_dir)
        self._items = [item for item in self._items if item.id != image_id]
        self._save()
        if file_path.exists():
            file_path.unlink()

    def file_path(self, image_id: str) -> Path:
        asset = self.get(image_id)
        if asset is None:
            raise KeyError(f"Không tìm thấy ảnh: {image_id}")
        return asset.file_path(self.images_dir)

    def _save(self) -> None:
        payload = {"images": [item.to_dict() for item in self._items]}
        self.index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
