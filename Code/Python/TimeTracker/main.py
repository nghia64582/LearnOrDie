import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import psutil
import time
import threading
import os
from datetime import datetime, timedelta
from collections import defaultdict
import json

class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Time Tracker")
        self.root.geometry("800x600")
        
        # Configuration
        self.check_interval = 2  # seconds
        self.save_interval = 30  # seconds
        self.data_dir = "time_tracker_data"
        
        # State variables
        self.is_tracking = False
        self.current_app = None
        self.last_activity_time = time.time()
        self.session_data = defaultdict(float)
        self.afk_threshold = 5  # seconds of inactivity before marking as AFK
        
        # Create data directory
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        self.setup_ui()
        self.check_thread = None
        self.save_thread = None
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Start/Stop button
        self.start_button = ttk.Button(control_frame, text="Start Tracking", command=self.toggle_tracking)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Status: Stopped")
        self.status_label.grid(row=0, column=1, padx=(0, 10))
        
        # Current app label
        self.current_app_label = ttk.Label(control_frame, text="Current App: None")
        self.current_app_label.grid(row=0, column=2)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Current session tab
        self.setup_current_session_tab()
        
        # History tab
        self.setup_history_tab()
        
        # Settings tab
        self.setup_settings_tab()
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def setup_current_session_tab(self):
        # Current session frame
        session_frame = ttk.Frame(self.notebook)
        self.notebook.add(session_frame, text="Current Session")
        
        # Session data display
        ttk.Label(session_frame, text="Current Session Activity:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Treeview for current session
        self.session_tree = ttk.Treeview(session_frame, columns=('Time',), show='tree headings')
        self.session_tree.heading('#0', text='Application')
        self.session_tree.heading('Time', text='Time (seconds)')
        self.session_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Scrollbar for session tree
        session_scrollbar = ttk.Scrollbar(session_frame, orient=tk.VERTICAL, command=self.session_tree.yview)
        session_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.session_tree.configure(yscrollcommand=session_scrollbar.set)
        
        # Clear session button
        ttk.Button(session_frame, text="Clear Session", command=self.clear_session).grid(row=2, column=0, pady=(0, 10))
        
        # Configure grid weights
        session_frame.columnconfigure(0, weight=1)
        session_frame.rowconfigure(1, weight=1)
        
    def setup_history_tab(self):
        # History frame
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="History")
        
        # Date selection
        date_frame = ttk.Frame(history_frame)
        date_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(date_frame, text="Select Date:").grid(row=0, column=0, padx=(0, 5))
        
        # Date entry
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.date_entry = ttk.Entry(date_frame, textvariable=self.date_var, width=12)
        self.date_entry.grid(row=0, column=1, padx=(0, 5))
        
        # Load history button
        ttk.Button(date_frame, text="Load History", command=self.load_history).grid(row=0, column=2, padx=(0, 5))
        
        # Show all days button
        ttk.Button(date_frame, text="Show All Days", command=self.show_all_days).grid(row=0, column=3)
        
        # History display
        self.history_text = scrolledtext.ScrolledText(history_frame, wrap=tk.WORD, width=70, height=25)
        self.history_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(1, weight=1)
        
    def setup_settings_tab(self):
        # Settings frame
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        
        # Check interval setting
        ttk.Label(settings_frame, text="Check Interval (seconds):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.check_interval_var = tk.StringVar(value=str(self.check_interval))
        check_interval_entry = ttk.Entry(settings_frame, textvariable=self.check_interval_var, width=10)
        check_interval_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 5))
        
        # Save interval setting
        ttk.Label(settings_frame, text="Save Interval (seconds):").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.save_interval_var = tk.StringVar(value=str(self.save_interval))
        save_interval_entry = ttk.Entry(settings_frame, textvariable=self.save_interval_var, width=10)
        save_interval_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 5))
        
        # AFK threshold setting
        ttk.Label(settings_frame, text="AFK Threshold (seconds):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.afk_threshold_var = tk.StringVar(value=str(self.afk_threshold))
        afk_threshold_entry = ttk.Entry(settings_frame, textvariable=self.afk_threshold_var, width=10)
        afk_threshold_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 5))
        
        # Apply settings button
        ttk.Button(settings_frame, text="Apply Settings", command=self.apply_settings).grid(row=3, column=0, pady=(10, 0))
        
    def get_active_window_process(self):
        """Get the name of the currently active window"""
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                return self.get_active_window_windows()
            elif system == "Linux":
                return self.get_active_window_linux()
            elif system == "Darwin":  # macOS
                return self.get_active_window_macos()
            else:
                return "Unsupported OS"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_active_window_windows(self):
        """Get active window on Windows"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Get the foreground window
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            
            if hwnd == 0:
                return "No active window"
            
            # Get window title
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                window_title = "No title"
            else:
                buffer = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
                window_title = buffer.value
            
            # Get process ID
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            # Get process name
            try:
                process = psutil.Process(pid.value)
                process_name = process.name()
                
                # Return format: "ProcessName - WindowTitle"
                if window_title and window_title != "No title":
                    return f"{process_name} - {window_title}"
                else:
                    return process_name
            except:
                return window_title if window_title else "Unknown"
                
        except ImportError:
            return "Windows API not available"
        except Exception as e:
            return f"Windows error: {str(e)}"
    
    def get_active_window_linux(self):
        """Get active window on Linux"""
        try:
            import subprocess
            
            # Try xdotool first
            try:
                # Get active window ID
                result = subprocess.run(['xdotool', 'getactivewindow'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    window_id = result.stdout.strip()
                    
                    # Get window name
                    result = subprocess.run(['xdotool', 'getwindowname', window_id], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        window_name = result.stdout.strip()
                        
                        # Get process name
                        result = subprocess.run(['xdotool', 'getwindowpid', window_id], 
                                              capture_output=True, text=True, timeout=2)
                        if result.returncode == 0:
                            pid = int(result.stdout.strip())
                            try:
                                process = psutil.Process(pid)
                                process_name = process.name()
                                return f"{process_name} - {window_name}"
                            except:
                                return window_name
                        else:
                            return window_name
            except FileNotFoundError:
                pass
            
            # Try wmctrl as fallback
            try:
                result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            parts = line.split(None, 3)
                            if len(parts) >= 4:
                                return parts[3]  # Window title
            except FileNotFoundError:
                pass
            
            return "Linux window detection tools not found (install xdotool or wmctrl)"
            
        except Exception as e:
            return f"Linux error: {str(e)}"
    
    def get_active_window_macos(self):
        """Get active window on macOS"""
        try:
            import subprocess
            
            # Use AppleScript to get active window
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set appName to name of frontApp
                try
                    set windowName to name of front window of frontApp
                    return appName & " - " & windowName
                on error
                    return appName
                end try
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "macOS window detection failed"
                
        except Exception as e:
            return f"macOS error: {str(e)}"
    
    def check_activity(self):
        """Check current activity and update tracking data"""
        while self.is_tracking:
            try:
                current_time = time.time()
                
                # Check if user is AFK
                if current_time - self.last_activity_time > self.afk_threshold:
                    app_name = "AFK"
                else:
                    app_name = self.get_active_window_process()
                    self.last_activity_time = current_time
                
                # Update session data
                if app_name != self.current_app:
                    self.current_app = app_name
                    self.root.after(0, self.update_current_app_display)
                
                self.session_data[app_name] += self.check_interval
                self.root.after(0, self.update_session_display)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"Error in check_activity: {e}")
                time.sleep(self.check_interval)
    
    def save_data(self):
        """Save tracking data to file"""
        while self.is_tracking:
            try:
                current_date = datetime.now().strftime("%Y_%m_%d")
                filename = f"action_{current_date}.txt"
                filepath = os.path.join(self.data_dir, filename)
                
                # Load existing data
                existing_data = {}
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r') as f:
                            existing_data = json.load(f)
                    except:
                        existing_data = {}
                
                # Merge with current session data
                for app, time_spent in self.session_data.items():
                    if app in existing_data:
                        existing_data[app] += time_spent
                    else:
                        existing_data[app] = time_spent
                
                # Save merged data
                with open(filepath, 'w') as f:
                    json.dump(existing_data, f, indent=2)
                
                # Clear session data after saving
                self.session_data.clear()
                
                time.sleep(self.save_interval)
                
            except Exception as e:
                print(f"Error in save_data: {e}")
                time.sleep(self.save_interval)
    
    def toggle_tracking(self):
        """Start or stop tracking"""
        if not self.is_tracking:
            self.start_tracking()
        else:
            self.stop_tracking()
    
    def start_tracking(self):
        """Start the tracking process"""
        self.is_tracking = True
        self.last_activity_time = time.time()
        
        # Start threads
        self.check_thread = threading.Thread(target=self.check_activity, daemon=True)
        self.save_thread = threading.Thread(target=self.save_data, daemon=True)
        
        self.check_thread.start()
        self.save_thread.start()
        
        # Update UI
        self.start_button.config(text="Stop Tracking")
        self.status_label.config(text="Status: Tracking")
        
    def stop_tracking(self):
        """Stop the tracking process"""
        self.is_tracking = False
        
        # Final save
        if self.session_data:
            self.save_final_data()
        
        # Update UI
        self.start_button.config(text="Start Tracking")
        self.status_label.config(text="Status: Stopped")
        self.current_app_label.config(text="Current App: None")
        
    def save_final_data(self):
        """Save final session data when stopping"""
        try:
            current_date = datetime.now().strftime("%Y_%m_%d")
            filename = f"action_{current_date}.txt"
            filepath = os.path.join(self.data_dir, filename)
            
            # Load existing data
            existing_data = {}
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = {}
            
            # Merge with current session data
            for app, time_spent in self.session_data.items():
                if app in existing_data:
                    existing_data[app] += time_spent
                else:
                    existing_data[app] = time_spent
            
            # Save merged data
            with open(filepath, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {e}")
    
    def update_current_app_display(self):
        """Update the current app display in UI"""
        self.current_app_label.config(text=f"Current App: {self.current_app}")
    
    def update_session_display(self):
        """Update the session data display"""
        # Clear existing items
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        
        # Add current session data
        for app, time_spent in sorted(self.session_data.items(), key=lambda x: x[1], reverse=True):
            self.session_tree.insert('', 'end', text=app, values=(f"{time_spent:.1f}",))
    
    def clear_session(self):
        """Clear current session data"""
        self.session_data.clear()
        self.update_session_display()
    
    def apply_settings(self):
        """Apply new settings"""
        try:
            self.check_interval = int(self.check_interval_var.get())
            self.save_interval = int(self.save_interval_var.get())
            self.afk_threshold = int(self.afk_threshold_var.get())
            messagebox.showinfo("Settings", "Settings applied successfully!")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for all settings.")
    
    def load_history(self):
        """Load and display history for selected date"""
        try:
            date_str = self.date_var.get()
            date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y_%m_%d")
            filename = f"action_{date_formatted}.txt"
            filepath = os.path.join(self.data_dir, filename)
            
            if not os.path.exists(filepath):
                self.history_text.delete(1.0, tk.END)
                self.history_text.insert(1.0, f"No data found for {date_str}")
                return
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Format and display data
            self.history_text.delete(1.0, tk.END)
            self.history_text.insert(1.0, f"Activity Summary for {date_str}:\n")
            self.history_text.insert(tk.END, "=" * 50 + "\n\n")
            
            total_time = sum(data.values())
            sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
            
            for app, time_spent in sorted_data:
                hours = int(time_spent // 3600)
                minutes = int((time_spent % 3600) // 60)
                seconds = int(time_spent % 60)
                percentage = (time_spent / total_time) * 100 if total_time > 0 else 0
                
                self.history_text.insert(tk.END, f"{app}:\n")
                self.history_text.insert(tk.END, f"  Time: {hours:02d}:{minutes:02d}:{seconds:02d}\n")
                self.history_text.insert(tk.END, f"  Percentage: {percentage:.1f}%\n\n")
            
            total_hours = int(total_time // 3600)
            total_minutes = int((total_time % 3600) // 60)
            self.history_text.insert(tk.END, f"Total tracked time: {total_hours:02d}:{total_minutes:02d}\n")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load history: {e}")
    
    def show_all_days(self):
        """Show summary of all available days"""
        try:
            self.history_text.delete(1.0, tk.END)
            self.history_text.insert(1.0, "All Days Summary:\n")
            self.history_text.insert(tk.END, "=" * 50 + "\n\n")
            
            # Get all data files
            data_files = [f for f in os.listdir(self.data_dir) if f.startswith("action_") and f.endswith(".txt")]
            
            if not data_files:
                self.history_text.insert(tk.END, "No tracking data found.")
                return
            
            for filename in sorted(data_files):
                # Extract date from filename
                date_part = filename.replace("action_", "").replace(".txt", "")
                try:
                    date_obj = datetime.strptime(date_part, "%Y_%m_%d")
                    display_date = date_obj.strftime("%Y-%m-%d")
                except:
                    display_date = date_part
                
                # Load and summarize data
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    total_time = sum(data.values())
                    total_hours = int(total_time // 3600)
                    total_minutes = int((total_time % 3600) // 60)
                    
                    self.history_text.insert(tk.END, f"{display_date}:\n")
                    self.history_text.insert(tk.END, f"  Total time: {total_hours:02d}:{total_minutes:02d}\n")
                    self.history_text.insert(tk.END, f"  Apps tracked: {len(data)}\n")
                    
                    # Show top 3 apps
                    top_apps = sorted(data.items(), key=lambda x: x[1], reverse=True)[:3]
                    for app, app_time in top_apps:
                        app_hours = int(app_time // 3600)
                        app_minutes = int((app_time % 3600) // 60)
                        self.history_text.insert(tk.END, f"    {app}: {app_hours:02d}:{app_minutes:02d}\n")
                    
                    self.history_text.insert(tk.END, "\n")
                    
                except Exception as e:
                    self.history_text.insert(tk.END, f"  Error loading data: {e}\n\n")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show all days: {e}")
    
    def on_closing(self):
        """Handle application closing"""
        if self.is_tracking:
            self.stop_tracking()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TimeTrackerApp(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()