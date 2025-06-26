import keyboard
import datetime
import os

# Define the specific keys to monitor
# MONITORED_KEYS = [
#     'a', 'b', 'c', 'd', 'e',
#     'space', 'enter', 'esc',
#     'ctrl', 'alt', 'shift',
#     'f1', 'f2', 'f3', 'f4'
# ]
MONITORED_KEYS = [
    'f4', 'f1'
]
# Log file path
LOG_FILE = 'keyboard_log.txt'

def log_key_press(key_name):
    """Log the key press with timestamp to file"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_entry = f"[{timestamp}] Key pressed: {key_name}\n"
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(f"Logged: {key_name} at {timestamp}")
    except Exception as e:
        print(f"Error writing to log file: {e}")

def on_key_event(event):
    """Handle keyboard events"""
    # Only log key press events (not releases)
    try:
        if event.event_type == keyboard.KEY_DOWN:
            key_name = event.name.lower()
            
            # Check if the pressed key is in our monitored list
            if key_name in MONITORED_KEYS:
                log_key_press(key_name)
    except:
        pass

def main():
    """Main function to start keyboard monitoring"""
    print("Keyboard Logger Started")
    print(f"Monitoring keys: {', '.join(MONITORED_KEYS)}")
    print(f"Logging to: {os.path.abspath(LOG_FILE)}")
    print("Press Ctrl+C to stop the logger\n")
    
    # Create log file if it doesn't exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"Keyboard Log Started - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n")
    
    try:
        # Hook all keyboard events
        keyboard.hook(on_key_event)
        
        # Keep the program running
        keyboard.wait()
        
    except KeyboardInterrupt:
        print("\nKeyboard logger stopped by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Unhook all keyboard events
        keyboard.unhook_all()
        print("Cleanup completed")

if __name__ == "__main__":
    # Check if running with appropriate permissions
    try:
        keyboard.is_pressed('shift')
    except Exception as e:
        print("Error: This script requires appropriate permissions to access keyboard events.")
        print("On Windows: Run as Administrator")
        print("On Linux: Run with sudo or add user to input group")
        print("On macOS: Grant accessibility permissions in System Preferences")
        exit(1)
    
    main()