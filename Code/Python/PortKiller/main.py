import os
import sys
import socket
import subprocess

def find_process_using_port(port):
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
                pids.add(parts[-1])  # PID is the last column
            else:  # Linux/macOS format
                pids.add(parts[1])  # PID is the second column
        
        return pids

    except subprocess.CalledProcessError:
        return set()

def kill_process(pid):
    """Kill process by PID."""
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
        else:  # Linux/macOS
            os.kill(int(pid), 9)
        print(f"✅ Process {pid} terminated.")
    except Exception as e:
        print(f"❌ Failed to terminate process {pid}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python kill_port.py <port>")
        sys.exit(1)

    port = sys.argv[1]
    
    if not port.isdigit():
        print("❌ Invalid port number. Please enter a numeric port.")
        sys.exit(1)

    print(f"🔍 Searching for processes using port {port}...")
    pids = find_process_using_port(port)

    if not pids:
        print(f"✅ No processes found using port {port}.")
    else:
        for pid in pids:
            kill_process(pid)
