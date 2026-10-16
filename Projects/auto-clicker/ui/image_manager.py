"""Image asset management window and picker dialog."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional

from PIL import Image, ImageTk

from services.image_service import ImageService
from storage.image_repository import ImageItem
from ui.dialogs import confirm_action, prompt_text, show_error, show_info


class ImageManagerWindow(tk.Toplevel):
    """Window for viewing, adding (via file or clipboard), and deleting image assets."""

    def __init__(
        self,
        parent: tk.Widget,
        image_service: ImageService,
        on_image_selected: Optional[Callable[[ImageItem], None]] = None,
        is_picker: bool = False,
    ) -> None:
        super().__init__(parent)
        self.image_service = image_service
        self.on_image_selected = on_image_selected
        self.is_picker = is_picker

        self.title("Image Assets Manager" if not is_picker else "Select Reference Image")
        self.geometry("820x520")
        self.minsize(650, 400)
        self.transient(parent)

        self._selected_item: Optional[ImageItem] = None
        self._current_photo: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        # Top Action Toolbar
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(fill=tk.X, side=tk.TOP)

        btn_add_file = ttk.Button(
            toolbar, text="📁 Add from File...", command=self._on_add_file
        )
        btn_add_file.pack(side=tk.LEFT, padx=(0, 6))

        btn_clipboard = ttk.Button(
            toolbar, text="📋 Paste from Clipboard", command=self._on_paste_clipboard
        )
        btn_clipboard.pack(side=tk.LEFT, padx=(0, 6))

        btn_delete = ttk.Button(
            toolbar, text="🗑️ Delete", command=self._on_delete
        )
        btn_delete.pack(side=tk.LEFT, padx=(0, 6))

        btn_refresh = ttk.Button(toolbar, text="🔄 Refresh", command=self.refresh)
        btn_refresh.pack(side=tk.LEFT, padx=(0, 6))

        if self.is_picker:
            btn_choose = ttk.Button(
                toolbar, text="✔ Select for Node", command=self._on_choose_and_close
            )
            btn_choose.pack(side=tk.RIGHT)

        # Paned Content (Table Left, Preview Right)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Left list frame
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=3)

        cols = ("id", "name", "size", "created_at")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("id", text="Image ID", anchor=tk.W)
        self.tree.heading("name", text="Name", anchor=tk.W)
        self.tree.heading("size", text="Resolution", anchor=tk.W)
        self.tree.heading("created_at", text="Added At", anchor=tk.W)

        self.tree.column("id", width=140)
        self.tree.column("name", width=140)
        self.tree.column("size", width=80)
        self.tree.column("created_at", width=120)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)
        if self.is_picker:
            self.tree.bind("<Double-Button-1>", lambda e: self._on_choose_and_close())

        # Right Preview Frame
        preview_frame = ttk.LabelFrame(paned, text="Image Preview", padding=8)
        paned.add(preview_frame, weight=2)

        self.preview_canvas = tk.Canvas(
            preview_frame,
            bg="#111111",  # Dark high-contrast background
            highlightthickness=3,
            highlightbackground="#000000",  # High contrast solid black border
            relief=tk.SOLID,
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.lbl_info = ttk.Label(
            preview_frame, text="Select an image to preview", font=("Segoe UI", 9)
        )
        self.lbl_info.pack(anchor=tk.W)

    def refresh(self) -> None:
        """Reload image index into the treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        images = self.image_service.list_images()
        for img in images:
            size_str = f"{img.width}x{img.height}" if img.width and img.height else "N/A"
            date_str = img.created_at[:16] if img.created_at else ""
            self.tree.insert(
                "",
                tk.END,
                iid=img.id,
                values=(img.id, img.name, size_str, date_str),
            )

        if images:
            # Select first item
            self.tree.selection_set(images[0].id)
            self._display_preview(images[0])
        else:
            self._clear_preview()

    def _on_row_selected(self, event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        image_id = selection[0]
        item = self.image_service.get_image(image_id)
        if item:
            self._selected_item = item
            self._display_preview(item)

    def _display_preview(self, item: ImageItem) -> None:
        self.preview_canvas.delete("all")
        if not item.file_path.is_file():
            self.lbl_info.configure(text=f"Image file missing: {item.filename}")
            return

        try:
            with Image.open(item.file_path) as orig:
                pw = max(self.preview_canvas.winfo_width(), 200)
                ph = max(self.preview_canvas.winfo_height(), 200)

                # Thumbnail preserving aspect ratio
                thumb = orig.copy()
                thumb.thumbnail((pw - 20, ph - 20), Image.Resampling.LANCZOS)

                self._current_photo = ImageTk.PhotoImage(thumb)
                cw = self.preview_canvas.winfo_width() / 2.0 or 100.0
                ch = self.preview_canvas.winfo_height() / 2.0 or 100.0

                self.preview_canvas.create_image(cw, ch, image=self._current_photo, anchor=tk.CENTER)
                self.lbl_info.configure(
                    text=f"ID: {item.id}\nResolution: {orig.width}x{orig.height}px\nFile: {item.filename}"
                )
        except Exception as err:
            self.lbl_info.configure(text=f"Preview error: {err}")

    def _clear_preview(self) -> None:
        self.preview_canvas.delete("all")
        self._current_photo = None
        self.lbl_info.configure(text="No images available")

    def _on_add_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Reference Image",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"),
                ("All files", "*.*"),
            ],
            parent=self,
        )
        if not file_path:
            return

        default_name = Path(file_path).stem
        name = prompt_text(self, "Image Name", "Enter a name for this image:", default_name)
        if not name or not name.strip():
            return

        try:
            item = self.image_service.add_from_file(file_path, name=name.strip())
            self.refresh()
            self.tree.selection_set(item.id)
            self._display_preview(item)
            show_info(self, "Success", f"Image '{item.name}' added with ID '{item.id}'.")
        except Exception as err:
            show_error(self, "Failed to Add Image", str(err))

    def _on_paste_clipboard(self) -> None:
        name = prompt_text(
            self,
            "Paste from Clipboard",
            "Enter a name for the clipboard image:",
            "Clipboard Snapshot",
        )
        if not name or not name.strip():
            return

        try:
            item = self.image_service.add_from_clipboard(name=name.strip())
            self.refresh()
            self.tree.selection_set(item.id)
            self._display_preview(item)
            show_info(self, "Success", f"Captured clipboard image as '{item.name}' [ID: {item.id}].")
        except Exception as err:
            show_error(self, "Clipboard Error", str(err))

    def _on_delete(self) -> None:
        selection = self.tree.selection()
        if not selection:
            show_info(self, "Selection Required", "Please select an image to delete.")
            return

        image_id = selection[0]
        item = self.image_service.get_image(image_id)
        if not item:
            return

        if not confirm_action(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete image '{item.name}' ({item.id})?",
        ):
            return

        self.image_service.delete_image(image_id)
        self.refresh()

    def _on_choose_and_close(self) -> None:
        selection = self.tree.selection()
        if not selection:
            show_info(self, "Selection Required", "Please select an image.")
            return

        image_id = selection[0]
        item = self.image_service.get_image(image_id)
        if item and self.on_image_selected:
            self.on_image_selected(item)
            self.destroy()
