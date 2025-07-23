import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import threading
import paramiko
import time
from collections import deque # For efficient appending and popping from both ends

SSH_HOST = "dev.sandinhstudio.com"
SSH_USERNAME = "nghiavt"
SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")
SSH_PASSPHRASE = "nghia123456"

LOG_CONFIG_FILE = "log_configs.txt"
MAX_LOG_LINES_COPY = 50

# --- CẤU HÌNH FONT LOG ---
# Sử dụng một biến duy nhất để dễ dàng chỉnh sửa font và cỡ chữ cho các textfield log
LOG_FONT = ("JetBrains Mono Medium", 10) # Thay đổi font và cỡ chữ ở đây

class LogViewerApp:
    def __init__(self, master):
        self.master = master
        master.title("Ứng Dụng Xem Log Từ Xa")
        master.geometry("1000x700") # Kích thước cửa sổ mặc định

        self.ssh_client = None
        self.tail_process = None
        self.tail_thread = None
        self.log_queue = deque() # Queue for thread-safe log updates
        self.log_lines_buffer = deque(maxlen=MAX_LOG_LINES_COPY) # Buffer for copy function
        self.stop_thread_event = threading.Event() # Event to signal thread to stop

        self.create_widgets()
        self.load_log_configs()

    def create_widgets(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # --- Tab 1: Log Monitoring ---
        self.log_monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_monitor_frame, text="Theo Dõi Log")
        self.create_log_monitor_tab(self.log_monitor_frame)

        # --- Tab 2: Log Filtering ---
        self.log_filter_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_filter_frame, text="Lọc Log")
        self.create_log_filter_tab(self.log_filter_frame)

    def create_log_monitor_tab(self, parent_frame):
        # Dropdown for log file selection
        log_selection_frame = ttk.Frame(parent_frame)
        log_selection_frame.pack(pady=10, fill="x", padx=10)

        ttk.Label(log_selection_frame, text="Chọn File Log:").pack(side="left", padx=5)
        self.log_file_var = tk.StringVar(parent_frame)
        self.log_file_names = [] # To store display names
        self.log_file_paths = {} # Map display name to actual path

        self.log_combobox = ttk.Combobox(log_selection_frame, textvariable=self.log_file_var, state="readonly", width=50)
        self.log_combobox.pack(side="left", padx=5, expand=True, fill="x")
        self.log_combobox.bind("<<ComboboxSelected>>", self.on_log_file_selected)

        # Buttons
        button_frame = ttk.Frame(log_selection_frame)
        button_frame.pack(side="right", padx=5)

        self.view_log_button = ttk.Button(button_frame, text="Xem Log", command=self.start_log_streaming)
        self.view_log_button.pack(side="left", padx=5)

        self.stop_log_button = ttk.Button(button_frame, text="Dừng Xem", command=self.stop_log_streaming, state=tk.DISABLED)
        self.stop_log_button.pack(side="left", padx=5)

        self.clear_log_button = ttk.Button(button_frame, text="Xóa", command=self.clear_log_display)
        self.clear_log_button.pack(side="left", padx=5)

        self.copy_log_button = ttk.Button(button_frame, text="Copy 50 Dòng", command=self.copy_log_to_clipboard)
        self.copy_log_button.pack(side="left", padx=5)

        # Log display Textfield
        # FIX: Áp dụng font đã định nghĩa
        self.log_display = scrolledtext.ScrolledText(parent_frame, wrap=tk.WORD, state="disabled", height=20, font=LOG_FONT)
        self.log_display.pack(expand=True, fill="both", padx=10, pady=5)

    def create_log_filter_tab(self, parent_frame):
        # Input fields for filter
        filter_input_frame = ttk.Frame(parent_frame)
        filter_input_frame.pack(pady=10, fill="x", padx=10)

        ttk.Label(filter_input_frame, text="Đường dẫn File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.filter_filepath_entry = ttk.Entry(filter_input_frame, width=60)
        self.filter_filepath_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # Set a default path for convenience
        if self.log_file_names:
            first_log_name = self.log_file_names[0]
            self.filter_filepath_entry.insert(0, self.log_file_paths[first_log_name])
        else:
            self.filter_filepath_entry.insert(0, "/var/log/syslog") # Default example

        ttk.Label(filter_input_frame, text="Từ khóa:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.filter_keyword_entry = ttk.Entry(filter_input_frame, width=60)
        self.filter_keyword_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.filter_keyword_entry.insert(0, "error") # Default example

        filter_input_frame.grid_columnconfigure(1, weight=1) # Allow entry to expand

        # Buttons
        filter_button_frame = ttk.Frame(parent_frame)
        filter_button_frame.pack(pady=5, fill="x", padx=10)
        filter_button_frame.columnconfigure(0, weight=1)
        filter_button_frame.columnconfigure(1, weight=1)

        self.search_log_button = ttk.Button(filter_button_frame, text="Tìm kiếm Log", command=self.search_log_file)
        self.search_log_button.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.clear_search_button = ttk.Button(filter_button_frame, text="Xóa Kết Quả", command=self.clear_search_display)
        self.clear_search_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Search results Textfield
        # FIX: Áp dụng font đã định nghĩa
        self.search_display = scrolledtext.ScrolledText(parent_frame, wrap=tk.WORD, state="disabled", height=20, font=LOG_FONT)
        self.search_display.pack(expand=True, fill="both", padx=10, pady=5)

    def load_log_configs(self):
        self.log_file_names = []
        self.log_file_paths = {}
        try:
            with open(LOG_CONFIG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(',', 1) # Split only on the first comma
                        if len(parts) == 2:
                            name = parts[0].strip()
                            path = parts[1].strip()
                            self.log_file_names.append(name)
                            self.log_file_paths[name] = path
            self.log_combobox['values'] = self.log_file_names
            if self.log_file_names:
                self.log_file_var.set(self.log_file_names[0]) # Select first item by default
                # Update filter path entry with the first log path
                self.filter_filepath_entry.delete(0, tk.END)
                self.filter_filepath_entry.insert(0, self.log_file_paths[self.log_file_names[0]])
        except FileNotFoundError:
            messagebox.showerror("Lỗi", f"Không tìm thấy file cấu hình log: {LOG_CONFIG_FILE}")
            self.log_file_var.set("Không có file cấu hình")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi đọc file cấu hình log: {e}")
            self.log_file_var.set("Lỗi đọc cấu hình")

    def on_log_file_selected(self, event=None):
        # Update the filter filepath entry when a log file is selected from the dropdown
        selected_name = self.log_file_var.get()
        if selected_name in self.log_file_paths:
            self.filter_filepath_entry.delete(0, tk.END)
            self.filter_filepath_entry.insert(0, self.log_file_paths[selected_name])

    def connect_ssh(self):
        if self.ssh_client is None:
            try:
                self.ssh_client = paramiko.SSHClient()
                # Auto add host keys (DANGEROUS IN PROD, use paramiko.WarningPolicy or manually add known hosts)
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
                
                print(f"Đang kết nối SSH tới {SSH_USERNAME}@{SSH_HOST}...")
                
                # --- ƯU TIÊN KẾT NỐI BẰNG KEY FILE NẾU ĐƯỢC CẤU HÌNH ---
                # Check if SSH_KEY_PATH is defined and the file exists
                if 'SSH_KEY_PATH' in globals() and os.path.exists(SSH_KEY_PATH):
                    try:
                        print(f"  Thử kết nối bằng key file: {SSH_KEY_PATH}")
                        # Load private key, providing passphrase if defined
                        private_key = paramiko.RSAKey.from_private_key_file(
                            SSH_KEY_PATH, 
                            password=globals().get('SSH_PASSPHRASE', None) # Use .get() for safe access
                        )
                        self.ssh_client.connect(SSH_HOST, username=SSH_USERNAME, pkey=private_key, timeout=10)
                        print("Kết nối SSH bằng Key File thành công.")
                        return True
                    except paramiko.PasswordRequiredException:
                        messagebox.showerror("Lỗi SSH", "Key file yêu cầu passphrase nhưng không được cung cấp hoặc sai.")
                        self.ssh_client = None
                        return False
                    except paramiko.AuthenticationException:
                        messagebox.showerror("Lỗi SSH", "Xác thực SSH bằng Key File thất bại. Kiểm tra key và username.")
                        self.ssh_client = None
                        return False
                    except Exception as e:
                        print(f"  Lỗi khi kết nối bằng Key File: {e}. Thử lại bằng mật khẩu...")
                        # Fallback to password if key fails for other reasons
                
                # --- KẾT NỐI BẰNG MẬT KHẨU (NẾU KEY KHÔNG CÓ HOẶC THẤT BẠI) ---
                # FIX: Corrected hostname and removed key_filename/passphrase from password fallback
                print("  Thử kết nối bằng mật khẩu...")
                self.ssh_client.connect(hostname=SSH_HOST, username=SSH_USERNAME, key_filename=os.path.expanduser("~/.ssh/id_rsa"), passphrase=SSH_PASSPHRASE)
                print("Kết nối SSH bằng Mật khẩu thành công.")
                return True

            except paramiko.AuthenticationException:
                messagebox.showerror("Lỗi SSH", "Xác thực SSH thất bại. Kiểm tra tên người dùng/mật khẩu/key.")
            except paramiko.SSHException as e:
                messagebox.showerror("Lỗi SSH", f"Lỗi SSH: {e}")
            except Exception as e:
                messagebox.showerror("Lỗi SSH", f"Lỗi kết nối SSH không xác định: {e}")
            self.ssh_client = None # Reset client on failure
            return False
        return True # Already connected

    def disconnect_ssh(self):
        if self.ssh_client:
            print("Đang đóng kết nối SSH...")
            self.ssh_client.close()
            self.ssh_client = None
            print("Kết nối SSH đã đóng.")

    def start_log_streaming(self):
        self.stop_log_streaming() # Stop any existing streaming first

        selected_name = self.log_file_var.get()
        log_file_path = self.log_file_paths.get(selected_name)

        if not log_file_path:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một file log hợp lệ.")
            return

        if not self.connect_ssh():
            return

        self.clear_log_display()
        self.view_log_button.config(state=tk.DISABLED)
        self.stop_log_button.config(state=tk.NORMAL)
        self.log_display.config(state="normal") # Enable for writing

        try:
            # Use exec_command to get stdin, stdout, stderr streams
            # We need to change directory first, then tail the file
            # Using 'bash -c' to chain commands
            command = f"cd {os.path.dirname(log_file_path)} && tail -n 30 -f {os.path.basename(log_file_path)}"
            print(f"Thực thi lệnh: {command}")
            
            # Get the channel object directly for more control
            self.ssh_channel = self.ssh_client.get_transport().open_session()
            self.ssh_channel.exec_command(command)
            
            # Set buffer size for the channel directly
            self.ssh_channel.set_combine_stderr(True) # Combine stderr into stdout for simpler reading
            self.ssh_channel.setblocking(0) # Set to non-blocking mode for reading

            self.tail_process = self.ssh_channel # Store channel for reading
            # self.tail_error_stream is no longer needed if stderr is combined

            self.stop_thread_event.clear() # Clear the stop signal for the new thread
            self.tail_thread = threading.Thread(target=self._read_log_stream)
            self.tail_thread.daemon = True # Thread exits when main program exits
            self.tail_thread.start()

            # Start checking the queue for new log lines
            self.master.after(100, self._update_log_display_from_queue)

        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi bắt đầu xem log: {e}")
            self.stop_log_streaming()

    def _read_log_stream(self):
        # FIX: More robust reading for continuous streams
        # Read in chunks and process lines
        buffer = ""
        while not self.stop_thread_event.is_set() and self.tail_process and not self.tail_process.closed:
            try:
                if self.tail_process.recv_ready():
                    # Read available data
                    data = self.tail_process.recv(4096).decode('utf-8', errors='ignore')
                    buffer += data
                    # Process lines from the buffer
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        self.log_queue.append(line + '\n') # Add newline back
                elif self.tail_process.exit_status_ready(): # Check if command finished
                    # Read any remaining data
                    remaining_data = self.tail_process.recv(4096).decode('utf-8', errors='ignore')
                    buffer += remaining_data
                    if buffer:
                        for line in buffer.split('\n'):
                            if line: # Avoid adding empty lines from trailing newline
                                self.log_queue.append(line + '\n')
                    print("Lệnh tail đã kết thúc trên server.")
                    break # Exit loop as command is done
                else:
                    # No data ready, wait a bit to prevent busy-looping
                    time.sleep(0.05) # Small delay
            except Exception as e:
                print(f"Lỗi trong luồng đọc log: {e}")
                self.log_queue.append(f"[LỖI LUỒNG]: {e}\n")
                self.stop_thread_event.set() # Signal to stop the thread
                break
        
        # Ensure channel is closed when thread finishes
        if self.tail_process and not self.tail_process.closed:
            self.tail_process.close()
            print("Kênh SSH đã đóng trong luồng đọc.")
        print("Luồng đọc log đã kết thúc.")


    def _update_log_display_from_queue(self):
        while self.log_queue:
            line = self.log_queue.popleft()
            self.log_display.insert(tk.END, line)
            self.log_display.see(tk.END) # Scroll to the end
            self.log_lines_buffer.append(line) # Add to buffer for copy

        # Continue checking the queue if the thread is still running
        # or if there might be remaining data in the buffer after the thread stops
        if self.tail_thread and self.tail_thread.is_alive() or self.log_queue:
            self.master.after(100, self._update_log_display_from_queue)
        else:
            # All data processed and thread has stopped
            self.log_display.config(state="disabled") # Disable writing
            self.view_log_button.config(state=tk.NORMAL)
            self.stop_log_button.config(state=tk.DISABLED)
            print("Streaming log đã dừng.")
            self.disconnect_ssh() # Disconnect SSH after streaming stops

    def stop_log_streaming(self):
        # Signal the reading thread to stop
        self.stop_thread_event.set() 
        
        if self.tail_process and not self.tail_process.closed:
            print("Đang dừng streaming log...")
            # Send Ctrl+C to the remote process to terminate tail -f
            try:
                self.tail_process.send('\x03') # Send Ctrl+C to the channel
                # Give it a moment to terminate
                time.sleep(0.1)
                self.tail_process.close() # Close the channel
            except Exception as e:
                print(f"Lỗi khi gửi Ctrl+C hoặc đóng channel: {e}")
            self.tail_process = None
        
        if self.tail_thread and self.tail_thread.is_alive():
            # Wait for the thread to finish gracefully
            self.tail_thread.join(timeout=2.0) # Give it 2 seconds to stop
            if self.tail_thread.is_alive():
                print("Cảnh báo: Luồng đọc log có thể chưa dừng hoàn toàn.")
        self.tail_thread = None

        self.log_display.config(state="disabled") # Disable writing
        self.view_log_button.config(state=tk.NORMAL)
        self.stop_log_button.config(state=tk.DISABLED)
        self.disconnect_ssh() # Ensure SSH connection is closed

    def clear_log_display(self):
        self.log_display.config(state="normal")
        self.log_display.delete(1.0, tk.END)
        self.log_display.config(state="disabled")
        self.log_lines_buffer.clear() # Clear buffer too

    def copy_log_to_clipboard(self):
        lines_to_copy = list(self.log_lines_buffer) # Get all lines from buffer
        text_to_copy = "".join(lines_to_copy)
        if text_to_copy:
            self.master.clipboard_clear()
            self.master.clipboard_append(text_to_copy)
            self.master.update()

    def search_log_file(self):
        filepath = self.filter_filepath_entry.get().strip()
        keyword = self.filter_keyword_entry.get().strip()

        if not filepath:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đường dẫn file log để tìm kiếm.")
            return
        if not keyword:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập từ khóa để tìm kiếm.")
            return

        if not self.connect_ssh():
            return

        self.clear_search_display()
        self.search_log_button.config(state=tk.DISABLED)
        self.master.update_idletasks() # Update GUI to show disabled state

        self.search_display.config(state="normal") # Enable for writing
        self.search_display.insert(tk.END, "Đang tìm kiếm log... Vui lòng chờ.\n")
        self.search_display.config(state="disabled")
        self.master.update_idletasks()

        # Run search in a separate thread to prevent GUI freeze
        threading.Thread(target=self._execute_search_command, args=(filepath, keyword)).start()

    def _execute_search_command(self, filepath, keyword):
        try:
            # Use 'grep' for searching. -i for case-insensitive, -E for extended regex
            command = f"grep -i -E '{keyword}' {filepath}"
            print(f"Thực thi lệnh tìm kiếm: {command}")
            
            # Use exec_command and read all output
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            
            output = stdout.read().decode('utf-8')
            errors = stderr.read().decode('utf-8')

            self.master.after(0, lambda: self._display_search_results(output, errors))

        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Lỗi Tìm kiếm", f"Lỗi khi thực hiện tìm kiếm: {e}"))
        finally:
            self.master.after(0, lambda: self.search_log_button.config(state=tk.NORMAL))
            self.disconnect_ssh() # Disconnect after search is done

    def _display_search_results(self, output, errors):
        self.search_display.config(state="normal")
        self.search_display.delete(1.0, tk.END) # Clear "Searching..." message

        if errors:
            self.search_display.insert(tk.END, f"--- LỖI TỪ MÁY CHỦ ---\n{errors}\n\n", "error_tag")
            self.search_display.tag_config("error_tag", foreground="red")
        
        if output:
            self.search_display.insert(tk.END, output)
        else:
            self.search_display.insert(tk.END, "Không tìm thấy kết quả nào cho từ khóa này.")
        
        self.search_display.config(state="disabled")
        self.search_display.see(tk.END)

    def clear_search_display(self):
        self.search_display.config(state="normal")
        self.search_display.delete(1.0, tk.END)
        self.search_display.config(state="disabled")

    def on_closing(self):
        print("Đóng ứng dụng...")
        self.stop_log_streaming() # Ensure streaming is stopped
        self.disconnect_ssh() # Ensure SSH connection is closed
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LogViewerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing) # Handle window close event
    root.mainloop()
