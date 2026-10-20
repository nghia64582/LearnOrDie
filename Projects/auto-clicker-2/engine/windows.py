"""Thao tác cửa sổ đang chạy (Windows) qua pygetwindow (đi kèm pyautogui)."""

from __future__ import annotations


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
