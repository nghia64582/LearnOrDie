from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from PIL import Image, ImageTk

from models.image import ImageAsset
from models.image_library import IMAGE_EXTENSIONS, ImageLibrary

PREVIEW_MAX_SIZE = (420, 320)


class ImagesTab(ttk.Frame):
    def __init__(self, master: tk.Misc, library: ImageLibrary) -> None:
        super().__init__(master, padding=12)
        self.library = library
        self._preview_photo: Optional[ImageTk.PhotoImage] = None
        self._build()
        self.refresh_list()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Danh sách hình ảnh", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        columns = ("name", "filename")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Tên")
        self.tree.heading("filename", text="File")
        self.tree.column("name", width=180, stretch=True)
        self.tree.column("filename", width=160, stretch=True)
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._on_select())

        scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(left)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Thêm ảnh", command=self.add_image).pack(side="left")
        ttk.Button(buttons, text="Đổi tên", command=self.rename_image).pack(side="left", padx=6)
        ttk.Button(buttons, text="Xóa", command=self.delete_image).pack(side="left")

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(right, text="Xem trước", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.preview = ttk.Label(
            right,
            text="Chưa chọn ảnh",
            anchor="center",
            relief="groove",
            padding=16,
        )
        self.preview.grid(row=1, column=0, sticky="nsew")

        self.info = ttk.Label(right, text="", justify="left")
        self.info.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def refresh_list(self, select_id: str | None = None) -> None:
        selected = select_id or self._selected_id()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for asset in self.library.all():
            self.tree.insert("", "end", iid=asset.id, values=(asset.name, asset.filename))
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)
            self.tree.focus(selected)
        elif self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
        self._on_select()

    def add_image(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(IMAGE_EXTENSIONS))
        path = filedialog.askopenfilename(
            parent=self,
            title="Chọn hình ảnh",
            filetypes=[("Ảnh", patterns), ("Tất cả file", "*.*")],
        )
        if not path:
            return
        try:
            asset = self.library.add_from_file(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Không thêm được ảnh", str(exc), parent=self)
            return
        self.refresh_list(select_id=asset.id)

    def rename_image(self) -> None:
        asset = self._selected_asset()
        if asset is None:
            messagebox.showinfo("Đổi tên", "Hãy chọn một ảnh trước.", parent=self)
            return
        new_name = simpledialog.askstring(
            "Đổi tên ảnh",
            "Tên mới:",
            initialvalue=asset.name,
            parent=self,
        )
        if new_name is None:
            return
        try:
            self.library.rename(asset.id, new_name)
        except ValueError as exc:
            messagebox.showerror("Không đổi tên được", str(exc), parent=self)
            return
        self.refresh_list(select_id=asset.id)

    def delete_image(self) -> None:
        asset = self._selected_asset()
        if asset is None:
            messagebox.showinfo("Xóa ảnh", "Hãy chọn một ảnh trước.", parent=self)
            return
        confirmed = messagebox.askyesno(
            "Xóa ảnh",
            f"Xóa ảnh \"{asset.name}\"? File trên đĩa cũng sẽ bị xóa.",
            parent=self,
        )
        if not confirmed:
            return
        try:
            self.library.delete(asset.id)
        except (OSError, KeyError) as exc:
            messagebox.showerror("Không xóa được ảnh", str(exc), parent=self)
            return
        self.refresh_list()

    def _selected_id(self) -> str | None:
        selection = self.tree.selection()
        return selection[0] if selection else None

    def _selected_asset(self) -> ImageAsset | None:
        image_id = self._selected_id()
        if not image_id:
            return None
        return self.library.get(image_id)

    def _on_select(self) -> None:
        asset = self._selected_asset()
        if asset is None:
            self._preview_photo = None
            self.preview.configure(image="", text="Chưa chọn ảnh")
            self.info.configure(text="")
            return
        path = asset.file_path(self.library.images_dir)
        self.info.configure(
            text=f"Tên: {asset.name}\nFile: {asset.filename}\nTạo lúc: {asset.created_at}"
        )
        if not path.exists():
            self._preview_photo = None
            self.preview.configure(image="", text="Không tìm thấy file ảnh")
            return
        try:
            with Image.open(path) as image:
                preview = image.copy()
            preview.thumbnail(PREVIEW_MAX_SIZE, Image.Resampling.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(preview)
            self.preview.configure(image=self._preview_photo, text="")
        except OSError:
            self._preview_photo = None
            self.preview.configure(image="", text="Không mở được ảnh")
