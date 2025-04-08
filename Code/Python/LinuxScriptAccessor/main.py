import os
import subprocess
import re
from datetime import datetime

# --- Configuration ---
user = "nghiavt"
host = "dev.sandinhstudio.com"
key_path = "C:/Users/NghiaVT/.ssh/id_rsa"
LOG_FOLDER = "/mnt/hdd2/f1chanlogs"
LOG_PREFIX = "smartfox.log"

cmd = f'ssh -i {key_path} {user}@{host} "cat {log_path}"'
# os.system(cmd)

start_date = datetime(2025, 3, 25)
end_date = datetime(2025, 3, 30)

def run_ssh_command(command):
    ssh_cmd = f"ssh {user}@{host} '{command}'"
    result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Error: {result.stderr}")
        return []
    return result.stdout.strip().splitlines()

def filter_files_by_date(filenames):
    filtered = []
    for name in filenames:
        match = re.search(r'smartfox\.log\.(\d{4}-\d{2}-\d{2})(-\d{2})?', name)
        if match:
            date_str = match.group(1)
            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if start_date <= file_date <= end_date:
                    filtered.append(name)
            except ValueError:
                continue
    return filtered

def analyze_log_lines(lines):
    for line in lines:
        if "ERROR" in line or "Exception" in line:
            print(f"❗ {line}")

def main():
    print("📁 Getting log file list from server...")
    all_files = run_ssh_command(f"ls {LOG_FOLDER}")
    log_files = [f for f in all_files if f.startswith(LOG_PREFIX)]
    print(f"🔍 Found {len(log_files)} log files.")

    filtered = filter_files_by_date(log_files)
    print(f"📅 Filtered files in range: {filtered}")

    for file in filtered:
        print(f"\n📖 Reading {file}...")
        lines = run_ssh_command(f"cat {remote_dir}/{file}")
        analyze_log_lines(lines)


if __name__ == "__main__":
    main()
