import pygetwindow as gw
import win32gui

# Find window by title
win = gw.getWindowsWithTitle("Chắn Sân Đình")[0]  # Replace with your target window name

# Resize and move the window
win.resizeTo(800, 600)
win.moveTo(120, 120)
