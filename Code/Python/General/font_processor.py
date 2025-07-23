import tkinter as tk
from tkinter import ttk
import os
import sys
from collections import OrderedDict

# --- START: Code from "Lấy Danh Sách Font Hệ Thống bằng Python" Canvas ---
# Try to import matplotlib.font_manager for a convenient cross-platform approach
try:
    import matplotlib.font_manager as fm
    has_matplotlib_fm = True
except ImportError:
    # print("Cảnh báo: Không tìm thấy thư viện 'matplotlib'. Một số phương pháp tìm font có thể không hoạt động.")
    has_matplotlib_fm = False

def get_system_fonts():
    """
    Attempts to retrieve a list of installed system fonts.
    Combines matplotlib's font_manager (if available) with OS-specific directory scanning.
    Returns a list of unique font file paths.
    """
    font_paths = set()
    # print("Đang tìm kiếm font hệ thống...")

    # 1. Use matplotlib.font_manager if available (often finds many common fonts)
    if has_matplotlib_fm:
        # print("  Sử dụng matplotlib.font_manager...")
        try:
            # fm._rebuild() # This can be slow, use with caution if cache is already built
            for font_file in fm.findSystemFonts():
                font_paths.add(font_file)
        except Exception as e:
            print(f"  Lỗi khi sử dụng matplotlib.font_manager: {e}")

    # 2. OS-specific font directories
    # print("  Quét các thư mục font hệ thống...")

    if sys.platform.startswith('win'):
        # Windows font directories and registry
        # print("    Hệ điều hành: Windows")
        windows_font_dirs = [
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft\\Windows\\Fonts') # User fonts
        ]
        for font_dir in windows_font_dirs:
            if os.path.exists(font_dir):
                for root, _, files in os.walk(font_dir):
                    for file in files:
                        if file.lower().endswith(('.ttf', '.otf', '.ttc')):
                            font_paths.add(os.path.join(root, file))
        
        # Try to read from Windows Registry (more comprehensive)
        try:
            import winreg
            reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                i = 0
                while True:
                    try:
                        value_name, value_data, value_type = winreg.EnumValue(key, i)
                        # Value data contains the font file path
                        if value_type == winreg.REG_SZ:
                            # Paths in registry might be relative to %WINDIR%\Fonts
                            if not os.path.isabs(value_data):
                                value_data = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', value_data)
                            if os.path.exists(value_data):
                                font_paths.add(value_data)
                        i += 1
                    except OSError: # No more values
                        break
            # print("    Đã quét Registry Windows.")
        except ImportError:
            print("    Không tìm thấy 'winreg' (chỉ có trên Windows). Bỏ qua quét Registry.")
        except Exception as e:
            print(f"    Lỗi khi quét Registry Windows: {e}")

    elif sys.platform == 'darwin':
        # macOS font directories
        # print("    Hệ điều hành: macOS")
        macos_font_dirs = [
            '/Library/Fonts',
            '/System/Library/Fonts',
            os.path.expanduser('~/Library/Fonts') # User-specific fonts
        ]
        for font_dir in macos_font_dirs:
            if os.path.exists(font_dir):
                for root, _, files in os.walk(font_dir):
                    for file in files:
                        if file.lower().endswith(('.ttf', '.otf', '.ttc')):
                            font_paths.add(os.path.join(root, file))

    elif sys.platform.startswith('linux'):
        # Linux font directories (common locations)
        # print("    Hệ điều hành: Linux")
        linux_font_dirs = [
            '/usr/share/fonts',
            '/usr/local/share/fonts',
            os.path.expanduser('~/.fonts'), # User-specific fonts (older convention)
            os.path.expanduser('~/.local/share/fonts') # User-specific fonts (newer XDG standard)
        ]
        for font_dir in linux_font_dirs:
            if os.path.exists(font_dir):
                for root, _, files in os.walk(font_dir):
                    for file in files:
                        if file.lower().endswith(('.ttf', '.otf', '.ttc')):
                            font_paths.add(os.path.join(root, file))

    else:
        print(f"    Hệ điều hành không xác định: {sys.platform}. Chỉ sử dụng matplotlib.font_manager (nếu có).")

    # Extract just the font names from the paths for a cleaner list
    font_names = set()
    for path in font_paths:
        try:
            if has_matplotlib_fm:
                 font_names.add(fm.FontProperties(fname=path).get_name())
            else:
                 # Fallback to filename without extension
                 font_names.add(os.path.splitext(os.path.basename(path))[0])
        except Exception:
            # Fallback if font_manager fails for a specific file
            font_names.add(os.path.splitext(os.path.basename(path))[0])

    # Sort the unique names alphabetically
    sorted_font_names = sorted(list(font_names))
    # print(f"\nTìm thấy tổng cộng {len(sorted_font_names)} font duy nhất.")
    return sorted_font_names
# --- END: Code from "Lấy Danh Sách Font Hệ Thống bằng Python" Canvas ---


class FontPreviewApp:
    def __init__(self, master):
        self.master = master
        master.title("Xem Trước Font Hệ Thống")
        master.geometry("600x400")

        self.all_fonts = get_system_fonts()
        self.font_sizes = [8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 64, 72]

        # --- Font Selection ---
        self.font_label = ttk.Label(master, text="Chọn Font:")
        self.font_label.pack(pady=5)

        self.font_var = tk.StringVar(master)
        if self.all_fonts:
            self.font_var.set(self.all_fonts[0]) # Set initial font to the first one found
        else:
            self.font_var.set("Không tìm thấy font")

        self.font_combobox = ttk.Combobox(master, textvariable=self.font_var, values=self.all_fonts, state="readonly")
        self.font_combobox.pack(pady=5)
        self.font_combobox.bind("<<ComboboxSelected>>", self.update_text_display)

        # --- Font Size Selection ---
        self.size_label = ttk.Label(master, text="Chọn Cỡ Chữ:")
        self.size_label.pack(pady=5)

        self.size_var = tk.IntVar(master)
        self.size_var.set(24) # Default font size
        self.size_combobox = ttk.Combobox(master, textvariable=self.size_var, values=self.font_sizes, state="readonly")
        self.size_combobox.pack(pady=5)
        self.size_combobox.bind("<<ComboboxSelected>>", self.update_text_display)

        # --- Demo Text Display ---
        self.demo_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
        self.text_display_label = ttk.Label(master, text=self.demo_text, wraplength=550) # wraplength to wrap text
        self.text_display_label.pack(pady=20, padx=10, fill=tk.BOTH, expand=True)

        # Initial update
        self.update_text_display()

    def update_text_display(self, event=None):
        """Updates the demo text label with the selected font and size."""
        selected_font_name = self.font_var.get()
        selected_font_size = self.size_var.get()

        try:
            # Create a font tuple: (font_family, size, style)
            # We're only changing family and size for simplicity
            font_tuple = (selected_font_name, selected_font_size)
            self.text_display_label.config(font=font_tuple)
            self.text_display_label.config(text=self.demo_text) # Reset text in case of error message
        except tk.TclError as e:
            # Handle cases where a selected font might not be truly usable by Tkinter
            print(f"Lỗi khi áp dụng font '{selected_font_name}' với cỡ {selected_font_size}: {e}")
            self.text_display_label.config(text=f"Không thể hiển thị font này: {selected_font_name}\nLỗi: {e}", font=("Arial", 12))


if __name__ == "__main__":
    root = tk.Tk()
    app = FontPreviewApp(root)
    root.mainloop()
