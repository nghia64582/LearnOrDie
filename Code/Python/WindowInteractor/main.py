import pygetwindow as gw
import psutil

# Common browser process names
BROWSERS = ['chrome.exe', 'msedge.exe', 'firefox.exe', 'brave.exe', 'opera.exe']

def get_process_name(pid):
    try:
        p = psutil.Process(pid)
        return p.name().lower()
    except Exception:
        return None

def list_windows_and_tabs():
    windows = gw.getAllWindows()
    for win in windows:
        if not win.visible:
            continue

        try:
            pid = win._hWnd  # windows handle
            process_name = get_process_name(win._getWindowPID())
        except Exception:
            process_name = None

        title = win.title.strip()

        if not title:
            continue  # Skip windows without titles

        if process_name in BROWSERS:
            print(f"[Browser Window] {process_name}: {title}")
        else:
            print(f"[Other Window] {process_name}: {title}")

if __name__ == "__main__":
    list_windows_and_tabs()
