from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from PIL import Image, ImageGrab, ImageTk

from models.image import ImageAsset
from models.image_library import IMAGE_EXTENSIONS, ImageLibrary
from ui.toast import Toast

PREVIEW_MAX_SIZE = (420, 320)

# Chụp màn hình bằng công cụ cắt của Windows (giống Win+Shift+S)
SNIP_URI = "ms-screenclip:"
SNIP_TIMEOUT_SECONDS = 60
SNIP_POLL_MS = 400
# Chờ cửa sổ thu nhỏ xong rồi mới mở công cụ chụp, để app không lọt vào ảnh
SNIP_LAUNCH_DELAY_MS = 350


def _grab_clipboard():
    """Đọc clipboard: trả về ảnh PIL, list đường dẫn file, hoặc None."""
    try:
        return ImageGrab.grabclipboard()
    except Exception:
        return None


def _clipboard_signature(content) -> str | None:
    # Dấu vân tay nội dung clipboard, dùng để nhận biết ảnh MỚI so với ảnh cũ
    if content is None:
        return None
    if isinstance(content, Image.Image):
        digest = hashlib.sha1(content.tobytes()).hexdigest()
        return f"image:{content.mode}:{content.size}:{digest}"
    if isinstance(content, (list, tuple)):
        return "files:" + "|".join(str(item) for item in content)
    return None


def _launch_snipping_tool() -> None:
    """Mở lớp phủ chụp màn hình của Windows. Lỗi thì raise OSError."""
    if sys.platform != "win32":
        raise OSError("Chỉ hỗ trợ trên Windows.")
    try:
        os.startfile(SNIP_URI)  # type: ignore[attr-defined]
    except OSError:
        subprocess.Popen(["explorer", SNIP_URI])


class ImagesTab(ttk.Frame):
    def __init__(self, master: tk.Misc, library: ImageLibrary) -> None:
        super().__init__(master, padding=12)
        self.library = library
        self._preview_photo: Optional[ImageTk.PhotoImage] = None
        self._toast: Toast | None = None
        self._snip_baseline: str | None = None
        self._snip_deadline = 0.0
        self._snip_after_id: str | None = None
        self._build()
        self.refresh_list()
        # Ctrl+V dán ảnh từ clipboard khi đang ở tab Hình ảnh
        top = self.winfo_toplevel()
        for sequence in ("<Control-v>", "<Control-V>"):
            top.bind(sequence, self._on_paste_key, add="+")

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

        snip_row = ttk.Frame(left)
        snip_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self._snip_btn = ttk.Button(snip_row, text="Chụp màn hình (Win+Shift+S)", command=self.snip_image)
        self._snip_btn.pack(side="left")
        ttk.Button(snip_row, text="Dán (Ctrl+V)", command=self.paste_image).pack(side="left", padx=6)
        self._snip_status = ttk.Label(left, text="", foreground="#667085", wraplength=320)
        self._snip_status.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

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

    # ---------------- Chụp màn hình / dán clipboard ----------------

    def snip_image(self) -> None:
        if self._snip_after_id is not None:
            self._finish_snip("Đã hủy chụp màn hình.")
            return
        # Ghi nhớ nội dung clipboard hiện tại để không lấy nhầm ảnh cũ
        self._snip_baseline = _clipboard_signature(_grab_clipboard())
        self._snip_btn.configure(text="Hủy chụp")
        self._set_snip_status("Chọn vùng cần chụp… (hủy bằng nút Hủy chụp)")
        self.winfo_toplevel().iconify()
        self._snip_after_id = self.after(SNIP_LAUNCH_DELAY_MS, self._launch_snip)

    def _launch_snip(self) -> None:
        try:
            _launch_snipping_tool()
        except OSError as exc:
            self._finish_snip(
                f"Không mở được công cụ chụp ({exc}). Hãy tự nhấn Win+Shift+S rồi Ctrl+V vào tab này.",
                kind="error",
            )
            return
        self._snip_deadline = time.monotonic() + SNIP_TIMEOUT_SECONDS
        self._snip_after_id = self.after(SNIP_POLL_MS, self._poll_snip)

    def _poll_snip(self) -> None:
        content = _grab_clipboard()
        signature = _clipboard_signature(content)
        if signature is not None and signature != self._snip_baseline:
            self._finish_snip(None)
            self._add_clipboard_content(content)
            return
        if time.monotonic() >= self._snip_deadline:
            self._finish_snip(f"Hết {SNIP_TIMEOUT_SECONDS}s mà chưa có ảnh mới trong clipboard.", kind="error")
            return
        self._snip_after_id = self.after(SNIP_POLL_MS, self._poll_snip)

    def _finish_snip(self, message: str | None, kind: str = "info") -> None:
        if self._snip_after_id is not None:
            try:
                self.after_cancel(self._snip_after_id)
            except tk.TclError:
                pass
            self._snip_after_id = None
        self._snip_btn.configure(text="Chụp màn hình (Win+Shift+S)")
        top = self.winfo_toplevel()
        top.deiconify()
        top.lift()
        top.focus_force()
        if message:
            self._set_snip_status(message, error=kind == "error")
            self._show_toast(message, kind=kind)

    def paste_image(self) -> None:
        content = _grab_clipboard()
        if _clipboard_signature(content) is None:
            message = "Clipboard không có ảnh. Nhấn Win+Shift+S để chụp rồi Ctrl+V."
            self._set_snip_status(message)
            self._show_toast(message)
            return
        self._add_clipboard_content(content)

    def _on_paste_key(self, _event: tk.Event) -> str | None:
        # Chỉ xử lý khi tab Hình ảnh đang hiển thị và không gõ trong ô nhập
        if not self.winfo_ismapped():
            return None
        try:
            focus = self.focus_get()
        except (KeyError, tk.TclError):
            focus = None
        if isinstance(focus, (tk.Entry, tk.Text, ttk.Entry, tk.Spinbox)):
            return None
        self.paste_image()
        return "break"

    def _add_clipboard_content(self, content) -> None:
        added: list[ImageAsset] = []
        errors: list[str] = []
        if isinstance(content, Image.Image):
            # Lưu PNG tạm rồi thêm qua đúng luồng add_from_file (copy + index.json)
            name = f"Chụp {datetime.now():%Y-%m-%d %H:%M:%S}"
            handle, temp_name = tempfile.mkstemp(suffix=".png")
            os.close(handle)
            temp_path = Path(temp_name)
            try:
                content.save(temp_path, "PNG")
                added.append(self.library.add_from_file(temp_path, name=name))
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
            finally:
                temp_path.unlink(missing_ok=True)
        else:
            # Clipboard chứa danh sách file (copy file trong Explorer)
            for item in content:
                path = Path(item)
                if path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                try:
                    added.append(self.library.add_from_file(path))
                except (OSError, ValueError) as exc:
                    errors.append(f"{path.name}: {exc}")
            if not added and not errors:
                errors.append("Các file trong clipboard không phải ảnh.")

        if added:
            self.refresh_list(select_id=added[-1].id)
            message = f"Đã thêm {len(added)} ảnh: " + ", ".join(asset.name for asset in added)
            self._set_snip_status(message)
            self._show_toast(message, kind="success")
        if errors:
            message = "Không thêm được ảnh: " + "; ".join(errors)
            self._set_snip_status(message, error=True)
            self._show_toast(message, kind="error", duration_ms=8000)

    def _set_snip_status(self, text: str, error: bool = False) -> None:
        self._snip_status.configure(text=text, foreground="#b42318" if error else "#667085")

    def _show_toast(self, text: str, kind: str = "info", duration_ms: int = 3000) -> None:
        if self._toast is not None and self._toast.winfo_exists():
            self._toast.dismiss()
        self._toast = Toast(self, text, kind=kind, duration_ms=duration_ms)

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
