"""Thao tác cửa sổ đang chạy (Windows) qua pygetwindow (đi kèm pyautogui)."""

from __future__ import annotations

import os
import subprocess
import sys


class WindowError(RuntimeError):
    pass


def _gw():
    try:
        import pygetwindow
    except (ImportError, NotImplementedError) as exc:
        raise WindowError(
            "Không dùng được pygetwindow (chỉ hỗ trợ Windows). Cài: python -m pip install pygetwindow"
        ) from exc
    return pygetwindow


def list_window_titles() -> list[str]:
    """Tiêu đề các cửa sổ đang hiển thị (bỏ trống, bỏ trùng), sắp theo ABC."""
    titles = {title.strip() for title in _gw().getAllTitles() if title and title.strip()}
    return sorted(titles, key=str.lower)


def find_window(title: str):
    """Tìm cửa sổ theo tiêu đề: ưu tiên trùng khớp hoàn toàn, sau đó là chứa chuỗi (không phân biệt hoa thường)."""
    wanted = title.strip()
    if not wanted:
        raise WindowError("Chưa nhập tiêu đề cửa sổ.")
    candidates = [win for win in _gw().getWindowsWithTitle(wanted) if (win.title or "").strip()]
    exact = [win for win in candidates if win.title.strip().lower() == wanted.lower()]
    if exact:
        return exact[0]
    if candidates:
        return candidates[0]
    raise WindowError(f"Không tìm thấy cửa sổ có tiêu đề \"{wanted}\".")


def activate_window(win) -> None:
    """Hiện lại cửa sổ (kể cả đang thu nhỏ dưới taskbar) và đưa lên trước."""
    if win.isMinimized:
        win.restore()
    try:
        win.activate()
    except Exception:
        # Windows có thể từ chối SetForegroundWindow (lỗi "Error code 0");
        # thu nhỏ rồi khôi phục thường đưa được cửa sổ lên trước
        win.minimize()
        win.restore()


def set_window_geometry(win, mode: str, left: int, top: int, width: int, height: int) -> None:
    if mode == "maximize":
        if win.isMinimized:
            win.restore()
        win.maximize()
        return
    if width <= 0 or height <= 0:
        raise WindowError("Chiều rộng/cao phải lớn hơn 0.")
    # Cửa sổ đang thu nhỏ/phóng to thì phải khôi phục trước mới đổi được vị trí
    if win.isMinimized or win.isMaximized:
        win.restore()
    win.moveTo(int(left), int(top))
    win.resizeTo(int(width), int(height))


def minimize_window(win) -> None:
    win.minimize()


def close_window(win) -> None:
    """Đóng nhẹ nhàng: gửi WM_CLOSE (như bấm nút X), app vẫn có thể hỏi lưu file."""
    win.close()


def window_exists(win) -> bool:
    hwnd = getattr(win, "_hWnd", None)
    if hwnd is not None and sys.platform == "win32":
        try:
            import ctypes

            return bool(ctypes.windll.user32.IsWindow(hwnd))
        except Exception:
            pass
    # Không kiểm tra được bằng handle thì xem cửa sổ còn trong danh sách không
    try:
        current = _gw().getWindowsWithTitle(win.title)
    except WindowError:
        return False
    if hwnd is not None:
        return any(getattr(other, "_hWnd", None) == hwnd for other in current)
    return any(other is win for other in current)


def window_pid(win) -> int:
    """PID của tiến trình sở hữu cửa sổ (GetWindowThreadProcessId)."""
    hwnd = getattr(win, "_hWnd", None)
    if hwnd is None or sys.platform != "win32":
        raise WindowError("Không lấy được tiến trình của cửa sổ (chỉ hỗ trợ Windows).")
    import ctypes
    from ctypes import wintypes

    pid = wintypes.DWORD(0)
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        raise WindowError("Không lấy được tiến trình của cửa sổ.")
    return int(pid.value)


def kill_process(pid: int) -> None:
    """Buộc tắt tiến trình: TerminateProcess, lỗi thì dùng taskkill /F."""
    if pid == os.getpid():
        raise WindowError("Không thể buộc tắt chính auto-clicker.")
    if sys.platform != "win32":
        raise WindowError("Buộc tắt chỉ hỗ trợ Windows.")
    import ctypes

    process_terminate = 0x0001
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(process_terminate, False, int(pid))
    if handle:
        try:
            if kernel32.TerminateProcess(handle, 1):
                return
        finally:
            kernel32.CloseHandle(handle)
    # Không đủ quyền với OpenProcess/TerminateProcess thì thử taskkill
    result = subprocess.run(
        ["taskkill", "/PID", str(int(pid)), "/F", "/T"],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise WindowError(f"Không buộc tắt được tiến trình {pid}: {(result.stderr or result.stdout).strip()}")
