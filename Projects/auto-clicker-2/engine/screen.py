"""Chụp toàn bộ các màn hình (nhiều monitor) và đổi tọa độ ảnh sang tọa độ màn hình thật.

Trên Windows, pyautogui.locateOnScreen chỉ chụp màn hình chính, nên ảnh nằm ở
màn hình phụ không bao giờ tìm thấy. Ở đây ta tự chụp cả "màn hình ảo" (gộp mọi
monitor) bằng ImageGrab.grab(all_screens=True), tìm ảnh trong đó rồi cộng gốc
của màn hình ảo (có thể âm nếu màn hình phụ nằm bên trái/phía trên màn hình chính).
"""

from __future__ import annotations

import sys

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77


def enable_dpi_awareness() -> None:
    # Gọi trước khi tạo cửa sổ Tk. Không có thì Windows co giãn tọa độ khi scale != 100%,
    # làm ảnh chụp và tọa độ click lệch nhau giữa các màn hình.
    if sys.platform != "win32":
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI aware
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def virtual_screen_origin() -> tuple[int, int]:
    """Tọa độ góc trên-trái của màn hình ảo. (0, 0) nếu không phải Windows."""
    if sys.platform != "win32":
        return 0, 0
    try:
        import ctypes

        metrics = ctypes.windll.user32.GetSystemMetrics
        return int(metrics(SM_XVIRTUALSCREEN)), int(metrics(SM_YVIRTUALSCREEN))
    except Exception:
        return 0, 0


def grab_all_screens():
    """Ảnh PIL của toàn bộ màn hình ảo (mọi monitor)."""
    from PIL import ImageGrab

    return ImageGrab.grab(all_screens=True)


def to_screen_box(box):
    """Đổi Box (namedtuple của pyscreeze) tính trong ảnh màn hình ảo sang tọa độ màn hình thật."""
    if box is None:
        return None
    origin_x, origin_y = virtual_screen_origin()
    return box._replace(left=box.left + origin_x, top=box.top + origin_y)
