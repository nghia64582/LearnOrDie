"""Service layer for image management and clipboard integration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageGrab

from storage.image_repository import ImageItem, ImageRepository


class ImageService:
    """Provides high-level operations for reference image assets."""

    def __init__(self, repository: ImageRepository) -> None:
        self.repository = repository

    def list_images(self) -> list[ImageItem]:
        return self.repository.list_images()

    def get_image(self, image_id: str) -> Optional[ImageItem]:
        return self.repository.get_image(image_id)

    def add_from_file(
        self,
        file_path: str | Path,
        name: Optional[str] = None,
        custom_id: Optional[str] = None,
    ) -> ImageItem:
        """Add image from an existing file on disk."""
        path = Path(file_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: '{path}'")

        with Image.open(path) as img:
            resolved_name = name.strip() if name and name.strip() else path.stem
            return self.repository.save_image(img, resolved_name, custom_id=custom_id)

    def add_from_clipboard(
        self,
        name: str,
        custom_id: Optional[str] = None,
    ) -> ImageItem:
        """Grab image from system clipboard and save it.

        Supports bitmap image on clipboard as well as copied image files.
        Raises ValueError if clipboard does not contain an image.
        """
        clip = ImageGrab.grabclipboard()

        if clip is None:
            raise ValueError("No image found in clipboard. Please copy an image first.")

        # If user copied image file(s) in Windows File Explorer, grabclipboard returns list of filenames
        if isinstance(clip, list):
            for path_str in clip:
                fpath = Path(path_str)
                if fpath.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                    with Image.open(fpath) as img:
                        return self.repository.save_image(img, name, custom_id=custom_id)
            raise ValueError("Clipboard contains files, but none are supported image formats.")

        # If user took a screenshot or copied an image bitmap
        if isinstance(clip, Image.Image):
            return self.repository.save_image(clip, name, custom_id=custom_id)

        raise ValueError(f"Unsupported clipboard data type: {type(clip).__name__}")

    def delete_image(self, image_id: str) -> bool:
        return self.repository.delete_image(image_id)
