import pyautogui
import subprocess
import time
import os
import platform

def open_chrome_quad_windows(urls):
    """
    Opens 4 separate Chrome windows and positions each one in a quarter of the screen.
    
    Args:
        urls (list): List of 4 URLs to open in separate Chrome windows
    """
    # Get screen dimensions
    screen_width, screen_height = pyautogui.size()
    
    # Calculate dimensions for each quarter
    quarter_width = screen_width // 2
    quarter_height = screen_height // 2
    
    # Define the positions for each quarter of the screen
    quarters = [
        (0, 0),                           # Top-left
        (quarter_width, 0),               # Top-right
        (0, quarter_height),              # Bottom-left
        (quarter_width, quarter_height)   # Bottom-right
    ]
    
    # Get the appropriate Chrome command for the current OS
    system = platform.system()
    
    for i, url in enumerate(urls[:4]):  # Limit to 4 URLs
        # Open Chrome with a new window for each URL
        if system == "Windows":
            chrome_path = find_chrome_path_windows()
            subprocess.Popen([chrome_path, "--new-window", url])
        
        elif system == "Darwin":  # macOS
            os.system(f'open -n -a "Google Chrome" --args --new-window "{url}"')
        
        else:  # Linux
            chrome_cmd = find_chrome_command_linux()
            subprocess.Popen([chrome_cmd, "--new-window", url])
        
        # Wait for the window to open
        time.sleep(1)
        
        # Position and resize the window
        x, y = quarters[i]
        
        if system == "Windows":
            # Get the active window and resize it
            window = pyautogui.getActiveWindow()
            if window:
                window.moveTo(x, y)
                window.resizeTo(quarter_width, quarter_height)
        
        elif system == "Darwin":  # macOS
            # Use AppleScript to position the window
            applescript = f'''
            tell application "Google Chrome"
                set bounds of front window to {{{x}, {y}, {x + quarter_width}, {y + quarter_height}}}
            end tell
            '''
            os.system(f"osascript -e '{applescript}'")
        
        else:  # Linux
            # Use wmctrl or xdotool (needs to be installed)
            try:
                # Get window ID of the most recently opened window
                window_id = subprocess.check_output(
                    "xdotool getactivewindow", 
                    shell=True
                ).decode().strip()
                
                # Position and resize the window
                os.system(f"xdotool windowmove {window_id} {x} {y}")
                os.system(f"xdotool windowsize {window_id} {quarter_width} {quarter_height}")
            except:
                print(f"Failed to position window {i+1}. Make sure xdotool is installed.")

def find_chrome_path_windows():
    """Find the Chrome executable path on Windows"""
    possible_paths = [
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google\\Chrome\\Application\\chrome.exe')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return "chrome"  # Fallback to command name

def find_chrome_command_linux():
    """Find the Chrome command on Linux"""
    for cmd in ['google-chrome', 'chrome', 'chromium', 'chromium-browser']:
        try:
            subprocess.check_call(['which', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return cmd
        except subprocess.CalledProcessError:
            continue
    
    return "google-chrome"  # Default fallback

# Example usage
if __name__ == "__main__":
    # urls = [
    #     "https://www.google.com",
    #     "https://www.github.com", 
    #     "https://www.youtube.com",
    #     "https://www.google.com"
    # ]
    CHAN_WEB_URL = "https://dev.sandinhstudio.com/chanunity/vihl/index.html?build=14512868535-1.0.7"
    urls = [CHAN_WEB_URL for _ in range(4)]
    
    open_chrome_quad_windows(urls)