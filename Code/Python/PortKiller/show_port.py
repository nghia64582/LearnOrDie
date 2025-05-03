import os
import socket
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
import sys
from collections import defaultdict

class PortManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Port Manager Utility")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10, "bold"))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        self.style.configure("Result.TLabel", font=("Arial", 9))
        
        # Create a notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create Port Killer tab
        self.killer_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.killer_frame, text="Port Killer")
        self.setup_killer_tab()
        
        # Create Port Viewer tab
        self.viewer_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.viewer_frame, text="Port Viewer")
        self.setup_viewer_tab()
        
        # OS info label at bottom
        self.os_info = "Windows" if os.name == 'nt' else "Linux/macOS"
        os_label = ttk.Label(
            root, 
            text=f"Detected OS: {self.os_info}", 
            style="Result.TLabel"
        )
        os_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Auto-refresh ports on startup
        self.refresh_ports_thread()

    def setup_killer_tab(self):
        """Setup the Port Killer tab"""
        # App title
        title_label = ttk.Label(
            self.killer_frame, 
            text="Kill Process by Port", 
            style="Header.TLabel"
        )
        title_label.pack(pady=(0, 20))
        
        # Port input frame
        port_frame = ttk.Frame(self.killer_frame)
        port_frame.pack(fill=tk.X, pady=(0, 15))
        
        port_label = ttk.Label(
            port_frame, 
            text="Enter Port Number:", 
            style="TLabel"
        )
        port_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_entry = ttk.Entry(port_frame, width=15)
        self.port_entry.pack(side=tk.LEFT)
        self.port_entry.focus()
        
        # Action buttons frame
        button_frame = ttk.Frame(self.killer_frame)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.kill_button = ttk.Button(
            button_frame, 
            text="Find and Kill Process", 
            style="TButton",
            command=self.kill_port_thread
        )
        self.kill_button.pack(pady=10)
        
        # Status frame
        status_frame = ttk.Frame(self.killer_frame, relief=tk.GROOVE, borderwidth=2)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        status_label = ttk.Label(
            status_frame, 
            text="Status:", 
            style="TLabel"
        )
        status_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Create a text widget for better output display
        self.result_text = tk.Text(
            status_frame, 
            height=8, 
            width=50, 
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.result_text.pack(padx=10, pady=(0, 10), fill=tk.BOTH, expand=True)
        self.result_text.config(state=tk.DISABLED)
        
        # Scrollbar for result text
        scrollbar = ttk.Scrollbar(self.result_text, command=self.result_text.yview)
        self.result_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_viewer_tab(self):
        """Setup the Port Viewer tab"""
        # Create top frame for controls
        top_frame = ttk.Frame(self.viewer_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title
        title_label = ttk.Label(
            top_frame, 
            text="Active Port Connections", 
            style="Header.TLabel"
        )
        title_label.pack(side=tk.LEFT, pady=(0, 10))
        
        # Refresh button
        self.refresh_button = ttk.Button(
            top_frame, 
            text="Refresh", 
            command=self.refresh_ports_thread
        )
        self.refresh_button.pack(side=tk.RIGHT)
        
        # Filter frame
        filter_frame = ttk.Frame(self.viewer_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        filter_label = ttk.Label(filter_frame, text="Filter by Port/Process:")
        filter_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.filter_entry = ttk.Entry(filter_frame, width=20)
        self.filter_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        filter_button = ttk.Button(
            filter_frame, 
            text="Apply Filter", 
            command=self.apply_filter
        )
        filter_button.pack(side=tk.LEFT)
        
        clear_button = ttk.Button(
            filter_frame, 
            text="Clear Filter", 
            command=self.clear_filter
        )
        clear_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Create treeview for port list with scrollbar
        self.tree_frame = ttk.Frame(self.viewer_frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview Columns
        columns = ("protocol", "local_address", "foreign_address", "state", "pid", "program")
        
        self.port_tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        # Define column headings
        self.port_tree.heading("protocol", text="Protocol")
        self.port_tree.heading("local_address", text="Local Address")
        self.port_tree.heading("foreign_address", text="Foreign Address")
        self.port_tree.heading("state", text="State")
        self.port_tree.heading("pid", text="PID")
        self.port_tree.heading("program", text="Program")
        
        # Define column widths
        self.port_tree.column("protocol", width=70)
        self.port_tree.column("local_address", width=150)
        self.port_tree.column("foreign_address", width=150)
        self.port_tree.column("state", width=100)
        self.port_tree.column("pid", width=70)
        self.port_tree.column("program", width=200)
        
        # Create vertical scrollbar
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.port_tree.yview)
        self.port_tree.configure(yscrollcommand=vsb.set)
        
        # Create horizontal scrollbar
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.port_tree.xview)
        self.port_tree.configure(xscrollcommand=hsb.set)
        
        # Pack scrollbars and treeview
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.port_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = ttk.Label(
            self.viewer_frame, 
            text="Ready", 
            style="Result.TLabel"
        )
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Add right-click menu for port operations
        self.context_menu = tk.Menu(self.port_tree, tearoff=0)
        self.context_menu.add_command(label="Kill Process", command=self.kill_selected_process)
        self.context_menu.add_command(label="Copy Port", command=self.copy_port)
        self.context_menu.add_command(label="Copy PID", command=self.copy_pid)
        
        self.port_tree.bind("<Button-3>", self.show_context_menu)
        
        # Double-click to view process details
        self.port_tree.bind("<Double-1>", self.show_process_details)
        
        # Store the original data for filtering
        self.all_ports_data = []

    def update_status(self, message, is_append=False):
        """Update the status display with a message in the killer tab"""
        self.result_text.config(state=tk.NORMAL)
        if not is_append:
            self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)

    def find_process_using_port(self, port):
        """Find the process ID (PID) using the given port."""
        try:
            # Use netstat (Windows) or lsof (Linux/macOS) to find the PID
            if os.name == 'nt':  # Windows
                cmd = f'netstat -ano | findstr :{port}'
            else:  # Linux/macOS
                cmd = f'lsof -i :{port} | grep LISTEN'

            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True)
            
            # Extract PID from output
            lines = output.strip().split("\n")
            pids = set()
            for line in lines:
                parts = line.split()
                if os.name == 'nt':  # Windows format
                    if len(parts) >= 5:
                        pids.add(parts[-1])  # PID is the last column
                else:  # Linux/macOS format
                    if len(parts) >= 2:
                        pids.add(parts[1])  # PID is the second column
            
            return pids

        except subprocess.CalledProcessError:
            return set()

    def kill_process(self, pid):
        """Kill process by PID."""
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
            else:  # Linux/macOS
                subprocess.run(f'kill -9 {pid}', shell=True, check=True)
            self.update_status(f"✅ Process {pid} terminated.", is_append=True)
            return True
        except Exception as e:
            self.update_status(f"❌ Failed to terminate process {pid}: {e}", is_append=True)
            return False

    def kill_port(self):
        """Main function to find and kill processes using a port"""
        # Get port from entry
        port = self.port_entry.get().strip()
        
        # Validate port
        if not port.isdigit():
            self.update_status("❌ Invalid port number. Please enter a numeric port.")
            return
        
        # Enable the button again
        self.root.after(0, lambda: self.kill_button.config(state=tk.NORMAL))
        
        self.update_status(f"🔍 Searching for processes using port {port}...")
        pids = self.find_process_using_port(port)

        if not pids:
            self.update_status(f"✅ No processes found using port {port}.", is_append=True)
        else:
            success_count = 0
            for pid in pids:
                if self.kill_process(pid):
                    success_count += 1
            
            if success_count == len(pids):
                self.update_status(f"✅ Successfully terminated all processes on port {port}.", is_append=True)
            else:
                self.update_status(f"⚠️ Terminated {success_count} out of {len(pids)} processes on port {port}.", is_append=True)
            
            # Refresh the port list after killing processes
            self.refresh_ports_thread()

    def kill_port_thread(self):
        """Run the port killing process in a separate thread to avoid freezing the UI"""
        self.kill_button.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.kill_port)
        thread.daemon = True
        thread.start()

    def get_ports_data(self):
        """Get information about all currently used ports"""
        ports_data = []
        
        try:
            # Different commands for Windows and Unix-like systems
            if os.name == 'nt':  # Windows
                cmd = 'netstat -ano'
                output = subprocess.check_output(cmd, shell=True, text=True)
                
                # Skip header lines
                lines = output.strip().split('\n')
                data_lines = [line for line in lines if ' TCP ' in line or ' UDP ' in line]
                
                for line in data_lines:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        protocol = parts[0]
                        local_address = parts[1]
                        foreign_address = parts[2]
                        state = parts[3] if len(parts) >= 5 else "N/A"
                        pid = parts[-1]
                        program_name = self.get_process_name(pid)
                        
                        ports_data.append((protocol, local_address, foreign_address, state, pid, program_name))
            else:  # Linux/macOS
                cmd = 'netstat -tulanp'
                output = subprocess.check_output(cmd, shell=True, text=True)
                
                # Skip header lines
                lines = output.strip().split('\n')
                data_lines = [line for line in lines if 'tcp' in line or 'udp' in line]
                
                for line in data_lines:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        protocol = parts[0]
                        local_address = parts[3]
                        foreign_address = parts[4]
                        state = parts[5] if len(parts) >= 6 else "N/A"
                        
                        # Extract PID/Program
                        pid_program = parts[-1]
                        pid = pid_program.split('/')[0] if '/' in pid_program else "N/A"
                        program_name = pid_program.split('/')[1] if '/' in pid_program else "N/A"
                        
                        ports_data.append((protocol, local_address, foreign_address, state, pid, program_name))
        
        except Exception as e:
            self.status_label.config(text=f"Error retrieving port data: {str(e)}")
        
        return ports_data
    
    def get_process_name(self, pid):
        """Get the process name for a given PID (Windows only)"""
        try:
            if os.name == 'nt':  # Windows
                cmd = f'tasklist /FI "PID eq {pid}" /FO CSV /NH'
                output = subprocess.check_output(cmd, shell=True, text=True)
                if output.strip():
                    # Remove quotes from CSV output and split
                    parts = output.strip().replace('"', '').split(',')
                    if len(parts) >= 1:
                        return parts[0]
            else:  # Linux/macOS
                cmd = f'ps -p {pid} -o comm='
                output = subprocess.check_output(cmd, shell=True, text=True)
                return output.strip()
        except:
            pass
        return "Unknown"
    
    def refresh_ports(self):
        """Refresh the list of ports and applications"""
        self.refresh_button.config(state=tk.DISABLED)
        self.status_label.config(text="Refreshing port data...")
        
        # Clear the treeview
        for item in self.port_tree.get_children():
            self.port_tree.delete(item)
        
        # Get port data
        self.all_ports_data = self.get_ports_data()
        
        # Insert data into treeview
        for data in self.all_ports_data:
            self.port_tree.insert("", tk.END, values=data)
        
        self.status_label.config(text=f"Found {len(self.all_ports_data)} active connections")
        self.refresh_button.config(state=tk.NORMAL)
    
    def refresh_ports_thread(self):
        """Run port refresh in a separate thread"""
        thread = threading.Thread(target=self.refresh_ports)
        thread.daemon = True
        thread.start()
    
    def apply_filter(self):
        """Filter port list based on user input"""
        filter_text = self.filter_entry.get().strip().lower()
        
        # Clear the treeview
        for item in self.port_tree.get_children():
            self.port_tree.delete(item)
        
        # Apply filter
        filtered_data = []
        for data in self.all_ports_data:
            for field in data:
                if filter_text in str(field).lower():
                    filtered_data.append(data)
                    break
        
        # Insert filtered data
        for data in filtered_data:
            self.port_tree.insert("", tk.END, values=data)
        
        self.status_label.config(text=f"Showing {len(filtered_data)} of {len(self.all_ports_data)} connections")
    
    def clear_filter(self):
        """Clear the filter and show all data"""
        self.filter_entry.delete(0, tk.END)
        
        # Clear the treeview
        for item in self.port_tree.get_children():
            self.port_tree.delete(item)
        
        # Insert all data
        for data in self.all_ports_data:
            self.port_tree.insert("", tk.END, values=data)
        
        self.status_label.config(text=f"Showing all {len(self.all_ports_data)} connections")
    
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        selected_items = self.port_tree.selection()
        if selected_items:
            self.context_menu.post(event.x_root, event.y_root)
    
    def kill_selected_process(self):
        """Kill the process of the currently selected row"""
        selected_items = self.port_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.port_tree.item(item, "values")
        
        # PID is the 5th column
        if len(values) >= 5:
            pid = values[4]
            program = values[5] if len(values) >= 6 else "Unknown"
            
            if messagebox.askyesno("Confirm", f"Kill process {program} (PID: {pid})?"):
                thread = threading.Thread(target=lambda: self.kill_process_from_viewer(pid))
                thread.daemon = True
                thread.start()
    
    def kill_process_from_viewer(self, pid):
        """Kill process from viewer tab and refresh list"""
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
            else:  # Linux/macOS
                subprocess.run(f'kill -9 {pid}', shell=True, check=True)
            
            self.status_label.config(text=f"Process with PID {pid} terminated successfully")
            
            # Switch to the killer tab to show the result
            self.notebook.select(0)
            self.update_status(f"✅ Process {pid} terminated.")
            
            # Refresh the port list
            self.refresh_ports_thread()
        except Exception as e:
            self.status_label.config(text=f"Failed to terminate process: {str(e)}")
            
            # Switch to the killer tab to show the error
            self.notebook.select(0)
            self.update_status(f"❌ Failed to terminate process {pid}: {e}")
    
    def copy_port(self):
        """Copy the port of the selected process to clipboard"""
        selected_items = self.port_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.port_tree.item(item, "values")
        
        # Extract port from local address (format is typically IP:Port)
        if len(values) >= 2:
            local_address = values[1]
            if ":" in local_address:
                port = local_address.split(":")[-1]
                self.root.clipboard_clear()
                self.root.clipboard_append(port)
                self.status_label.config(text=f"Copied port {port} to clipboard")
    
    def copy_pid(self):
        """Copy the PID of the selected process to clipboard"""
        selected_items = self.port_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.port_tree.item(item, "values")
        
        # PID is the 5th column
        if len(values) >= 5:
            pid = values[4]
            self.root.clipboard_clear()
            self.root.clipboard_append(pid)
            self.status_label.config(text=f"Copied PID {pid} to clipboard")
    
    def show_process_details(self, event):
        """Show detailed information about the selected process on double-click"""
        selected_items = self.port_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.port_tree.item(item, "values")
        
        if len(values) >= 6:
            protocol = values[0]
            local_address = values[1]
            foreign_address = values[2]
            state = values[3]
            pid = values[4]
            program = values[5]
            
            details = f"Protocol: {protocol}\n"
            details += f"Local Address: {local_address}\n"
            details += f"Foreign Address: {foreign_address}\n"
            details += f"State: {state}\n"
            details += f"PID: {pid}\n"
            details += f"Program: {program}\n"
            
            # Switch to killer tab and display in the text area
            self.notebook.select(0)
            self.update_status(f"📊 Process Details:\n{details}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PortManagerApp(root)
    root.mainloop()