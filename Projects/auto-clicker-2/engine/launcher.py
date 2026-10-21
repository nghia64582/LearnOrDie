"""Mở file / thư mục / chương trình bằng ứng dụng mặc định của hệ điều hành."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


class LaunchError(RuntimeError):
    pass


def expand_path(raw: str) -> Path:
    """Bỏ dấu ngoặc kép thừa, mở rộng %USERPROFILE% / $HOME và ~."""
    text = str(raw or "").strip().strip('"').strip()
    # %TEN% kiểu Windows (tự xử lý để chạy giống nhau trên mọi hệ điều hành), sau đó $TEN và ~
    text = re.sub(r"%([^%]+)%", lambda m: os.environ.get(m.group(1), m.group(0)), text)
    return Path(os.path.expanduser(os.path.expandvars(text)))


def open_path(raw: str, arguments: str = "") -> Path:
    if not str(raw or "").strip():
        raise LaunchError("Chưa nhập đường dẫn file.")
    path = expand_path(raw)
    if not path.exists():
        raise LaunchError(f"Không tìm thấy file hoặc thư mục: {path}")
    arguments = str(arguments or "").strip()
    try:
        if arguments and path.is_file():
            # Có tham số: chạy trực tiếp chương trình (thường là .exe), thư mục làm việc là thư mục chứa file
            args = shlex.split(arguments, posix=sys.platform != "win32")
            # posix=False giữ nguyên dấu ngoặc kép (để không hỏng đường dẫn có "\"), nên bỏ ngoặc ở hai đầu
            args = [a[1:-1] if len(a) >= 2 and a[0] == a[-1] == '"' else a for a in args]
            subprocess.Popen([str(path), *args], cwd=str(path.parent))
        elif sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as exc:
        raise LaunchError(f"Không mở được {path}: {exc}") from exc
    return path
