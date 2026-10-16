"""Screen capture, template matching, and desktop input simulation."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import time
from typing import Optional

import numpy as np
from PIL import Image, ImageGrab

# Windows input constants
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# Common virtual key codes
VK_MAP = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "escape": 0x1B,
    "esc": 0x1B,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}


def take_screenshot() -> Optional[Image.Image]:
    """Capture the full primary display screenshot."""
    try:
        return ImageGrab.grab()
    except Exception:
        # Fallback using Windows GDI via ctypes
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)

            hdc_screen = user32.GetDC(0)
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
            gdi32.SelectObject(hdc_mem, hbm)

            gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)  # SRCCOPY

            # Extract bitmap bits
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", wintypes.DWORD),
                    ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD),
                ]

            bih = BITMAPINFOHEADER()
            bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bih.biWidth = w
            bih.biHeight = -h  # top-down
            bih.biPlanes = 1
            bih.biBitCount = 32
            bih.biCompression = 0

            buf = ctypes.create_string_buffer(w * h * 4)
            gdi32.GetDIBits(hdc_screen, hbm, 0, h, buf, ctypes.byref(bih), 0)

            # Cleanup
            gdi32.DeleteObject(hbm)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)

            # Convert buffer to PIL Image (BGRA -> RGB)
            img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
            return img
        except Exception:
            return None


def match_template(
    screen: Image.Image,
    template: Image.Image,
    threshold: float = 0.85,
) -> Optional[tuple[int, int, int, int]]:
    """Locate template image inside screen image.

    Returns (x, y, width, height) of best match if confidence >= threshold, or None.
    """
    sw, sh = screen.size
    tw, th = template.size

    if tw > sw or th > sh or tw <= 0 or th <= 0:
        return None

    # Convert both to grayscale float32 numpy arrays
    screen_arr = np.array(screen.convert("L"), dtype=np.float32)
    tmpl_arr = np.array(template.convert("L"), dtype=np.float32)

    # Standardize template
    t_mean = tmpl_arr.mean()
    t_std = tmpl_arr.std()
    if t_std < 1e-5:
        # Near solid color template, fallback to mean absolute difference
        t_norm = tmpl_arr - t_mean
    else:
        t_norm = (tmpl_arr - t_mean) / t_std

    # Step size for fast search: if screen is large, step 2-3 pixels first
    step = 2 if (sw > 1200 or sh > 800) else 1

    best_score = -1.0
    best_loc = None

    # Search window
    t_len = tw * th
    for y in range(0, sh - th + 1, step):
        for x in range(0, sw - tw + 1, step):
            window = screen_arr[y : y + th, x : x + tw]
            w_std = window.std()
            if w_std < 1e-5:
                continue
            w_norm = (window - window.mean()) / w_std
            # Normalized cross-correlation
            score = float(np.sum(w_norm * t_norm) / t_len)

            if score > best_score:
                best_score = score
                best_loc = (x, y)
                if best_score >= 0.98:  # Almost perfect match, exit early
                    break
        if best_score >= 0.98:
            break

    # If step > 1 and found a candidate near threshold, refine around best_loc
    if step > 1 and best_loc and best_score >= (threshold - 0.1):
        bx, by = best_loc
        rx_min = max(0, bx - step)
        rx_max = min(sw - tw, bx + step)
        ry_min = max(0, by - step)
        ry_max = min(sh - th, by + step)

        for y in range(ry_min, ry_max + 1):
            for x in range(rx_min, rx_max + 1):
                window = screen_arr[y : y + th, x : x + tw]
                w_std = window.std()
                if w_std < 1e-5:
                    continue
                w_norm = (window - window.mean()) / w_std
                score = float(np.sum(w_norm * t_norm) / t_len)
                if score > best_score:
                    best_score = score
                    best_loc = (x, y)

    if best_score >= threshold and best_loc is not None:
        return (best_loc[0], best_loc[1], tw, th)

    return None


def click_at(x: int, y: int) -> None:
    """Move cursor to (x, y) and perform a left mouse click."""
    try:
        user32 = ctypes.windll.user32
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    except Exception:
        pass


def type_text(text: str) -> None:
    """Type a unicode string using Windows SendInput."""
    try:
        user32 = ctypes.windll.user32

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_ulonglong),
            ]

        class INPUT(ctypes.Structure):
            class _I(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]

            _anonymous_ = ("i",)
            _fields_ = [("type", wintypes.DWORD), ("i", _I)]

        for char in text:
            # Key down
            inp_down = INPUT(type=1)
            inp_down.ki = KEYBDINPUT(
                wVk=0, wScan=ord(char), dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0
            )
            # Key up
            inp_up = INPUT(type=1)
            inp_up.ki = KEYBDINPUT(
                wVk=0,
                wScan=ord(char),
                dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )

            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
            time.sleep(0.02)
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
            time.sleep(0.03)
    except Exception:
        pass


def press_key(key_name: str) -> None:
    """Press a special key (e.g. Enter, Tab, Escape, F1..F12)."""
    try:
        user32 = ctypes.windll.user32
        clean_key = key_name.strip().lower()
        vk = VK_MAP.get(clean_key)
        if vk is None:
            # Fallback to typing the text
            type_text(key_name)
            return

        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass
